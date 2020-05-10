package pkg

import (
	"encoding/json"
	"fmt"
	"github.com/aws/aws-sdk-go/private/util"
	"github.com/go-kit/kit/endpoint"
	httptransport "github.com/go-kit/kit/transport/http"
	"github.com/kubeflow/code-intelligence/chatbot/pkg/kfgokit"
	"github.com/pkg/errors"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	log "github.com/sirupsen/logrus"
	"golang.org/x/net/context"
	"io/ioutil"
	"net"
	"net/http"
	"regexp"
	"strings"
	"time"
	//"cloud.google.com/go/dialogflow/apiv2"
	dfext "github.com/kubeflow/code-intelligence/chatbot/pkg/dialogflow"
)

var (
	serviceHeartbeat = prometheus.NewCounter(prometheus.CounterOpts{
		Name: "service_heartbeat",
		Help: "Heartbeat signal every 10 seconds indicating pods are alive.",
	})
)

const (
	DialogFlowWebhookPath = "/dialogflow/webhook"
)

// kubeflowInfoServer provides information about Kubeflow.
// It is used to fulfill information requests from the chatbot.
type kubeflowInfoServer struct {
	listener    net.Listener
	labelMapUri string
	labels      *KubeflowLabels
}

// NewKubeflowInfoServer constructs an info server.
// labelMapUri is the path to the file mapping area labels to owners.
func NewKubeflowInfoServer(labelMapUri string) (*kubeflowInfoServer, error) {
	labels, err := LoadLabels(labelMapUri)

	if err != nil {
		return nil, errors.WithStack(err)
	}
	s := &kubeflowInfoServer{
		labelMapUri: labelMapUri,
		labels:      labels,
	}

	return s, nil
}

// Add heartbeat every 10 seconds
func countHeartbeat() {
	for {
		time.Sleep(10 * time.Second)
		serviceHeartbeat.Inc()
	}
}

type HealthzResponse struct {
	Reply string
}

func makeHealthzEndpoint() endpoint.Endpoint {
	return func(ctx context.Context, request interface{}) (interface{}, error) {
		r := &HealthzResponse{}
		r.Reply = "Request accepted! Still alive!"
		return r, nil
	}
}

func getHealthzHandler() http.Handler {
	return httptransport.NewServer(
		makeHealthzEndpoint(),
		func(_ context.Context, r *http.Request) (interface{}, error) {
			return nil, nil
		},
		kfgokit.EncodeResponse,
	)
}

func makeDialogFlowWebhookEndpoint(svc dfext.DialogFlowWebhookService) endpoint.Endpoint {
	return func(ctx context.Context, request interface{}) (interface{}, error) {
		req := request.(dfext.WebhookRequest)
		r, err := svc.HandleWebhook(ctx, req)
		return r, err
	}
}

// RegisterEndpoints creates the http endpoints for the server.
func (s *kubeflowInfoServer) RegisterEndpoints() {
	webhook := httptransport.NewServer(
		makeDialogFlowWebhookEndpoint(s),
		func(_ context.Context, r *http.Request) (interface{}, error) {
			// TODO(jlewi): We don't really need this code branch
			// Printing out the raw request is just a hack to see what additional
			// information slack is including.
			body, err := ioutil.ReadAll(r.Body)
			if err == nil {
				// For debugging print the complete request. We do this
				// to see what fields Dialogflow is sending.
				log.Infof("Raw request body:\n%v", string(body))
				var request dfext.WebhookRequest
				if err := json.Unmarshal(body, &request); err != nil {
					log.Errorf("Err decoding Dialogflow WebhookRequest: " + err.Error())
					return nil, err
				}
				return request, nil
			} else {
				log.Errorf("Error reading body: %v", err)
				return nil, err
			}
			//
			//var request dfext.WebhookRequest
			//if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
			//	log.Errorf("Err decoding Dialogflow WebhookRequest: " + err.Error())
			//	return nil, err
			//}
			//return request, nil
		},
		kfgokit.EncodeResponse,
	)

	http.Handle(DialogFlowWebhookPath, webhook)
	http.Handle("/", getHealthzHandler())
}

func (s *kubeflowInfoServer) StartHttp(port int) error {
	portS := fmt.Sprintf(":%d", port)
	if port <= 0 {
		log.Info("No port specified; using next available.")
		portS = ":0"
	}

	listener, err := net.Listen("tcp", portS)

	if err != nil {
		panic(err)
	}

	s.listener = listener

	// add an http handler for prometheus metrics
	http.Handle("/metrics", promhttp.Handler())

	go countHeartbeat()

	log.Infof("Listening on address: %+v", listener.Addr())

	err = http.Serve(s.listener, nil)

	return err
}

// matchLabels finds the labels matching the specified parameters
func (s *KubeflowLabels) matchLabels(parameters map[string]string) []string {
	regex := []*regexp.Regexp{}

	for prefix, value := range parameters {
		if strings.TrimSpace(value) == "" {
			continue
		}
		expr := fmt.Sprintf("%v.*/.*%v.*", strings.ToLower(prefix), strings.ToLower(value))
		m, err := regexp.Compile(expr)

		if err != nil {
			log.Errorf("Could not compile the regex: %v ; error %v", expr, err)
			continue
		}
		regex = append(regex, m)
	}

	labels := []string{}
	for label, _ := range s.Labels {
		for _, p := range regex {
			s := strings.ToLower(label)
			if match := p.MatchString(s); match {
				labels = append(labels, label)
			}
		}
	}

	return labels
}

// HandleWebhook is a fulfilment for Dialogflow.
func (s *kubeflowInfoServer) HandleWebhook(ctx context.Context, req dfext.WebhookRequest) (*dfext.WebhookResponse, error) {
	// TODO(jlewi): Should check the intent name.
	//
	// TODO(jlewi): What we really want to do use send a prediction to attach labels to the question and
	// then map it to the area?
	log.Infof("Recieved request:%v", util.PrettyPrint(req))

	res := &dfext.WebhookResponse{
		FulfillmentMessages: []dfext.Message{},
	}

	labels := s.labels.matchLabels(req.QueryResult.Parameters)

	if len(labels) == 0 {
		AppendMessage(res, "I'm sorry I don't understand what area of Kubeflow you are asking about.")
		AppendMessage(res, "You can find a list of areas at "+s.labelMapUri)
		return res, nil
	}

	for _, l := range labels {
		info := s.labels.Labels[l]
		AppendMessage(res,
			fmt.Sprintf("The owners of %v are %v", l, strings.Join(info.Owners, ",")))
	}

	return res, nil
}

func AppendMessage(res *dfext.WebhookResponse, m string) {
	if res == nil {
		log.Errorf("res should not be nil")
		return
	}
	res.FulfillmentMessages = append(
		res.FulfillmentMessages,
		dfext.Message{
			Text: dfext.Text{
				Text: []string{
					m,
				},
			},
		})
}
