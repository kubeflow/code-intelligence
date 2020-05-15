package pkg

import (
	"encoding/json"
	"fmt"
	"github.com/go-kit/kit/endpoint"
	httptransport "github.com/go-kit/kit/transport/http"
	"github.com/kubeflow/code-intelligence/chatbot/pkg/kfgokit"
	"github.com/pkg/errors"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	log "github.com/sirupsen/logrus"
	"golang.org/x/net/context"
	"net"
	"net/http"
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
	listener net.Listener
	labelMapUri string
	labels *KubeflowLabels
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
		labels: labels,
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
			var request dfext.WebhookRequest
			if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
				log.Errorf("Err decoding Dialogflow WebhookRequest: " + err.Error())
				return nil, err
			}
			return request, nil
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

func (s *kubeflowInfoServer) HandleWebhook(ctx context.Context, req dfext.WebhookRequest)(*dfext.WebhookResponse, error) {
	log.Errorf("TODO need to implement actual webhook")
	res := &dfext.WebhookResponse{
		FulfillmentMessages:[]dfext.Message {
			{
				Text: dfext.Text{
					Text: []string {
						"Need to add actual webhook message",
					} ,
				},
			},
		},
		}
	return res, nil
}