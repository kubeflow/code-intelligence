package server

import (
	"encoding/json"
	"fmt"
	"github.com/kubeflow/code-intelligence/Label_Microservice/go/cmd/automl/pkg/automl"
	"github.com/kubeflow/code-intelligence/Label_Microservice/go/cmd/automl/pkg/kpt"
	log "github.com/sirupsen/logrus"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"net/http"
)

const (
	kind       = "NeedsSync"
	apiVersion = "v1alpha1"
)

type Server struct {
	Project    string
	Location   string
	Name       string
	KptFile    string
	SetterName string
}

type NeedsSyncResponse struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty" protobuf:"bytes,1,opt,name=metadata"`
	NeedsSync         bool              `json:"needsSync"`
	Parameters        map[string]string `json:"parameters"`
	Errors            []responseError   `json:"errors,omitempty"`
}

type responseError struct {
	Message string `json:"message"`
}

func (s *Server) Healthz(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("ok"))
	w.WriteHeader(http.StatusOK)
}

func appendError(r *NeedsSyncResponse, msg string) {
	r.Errors = append(r.Errors, responseError{Message: msg})
}

func (s *Server) NeedsSync(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json; charset=UTF-8")

	response := &NeedsSyncResponse{
		TypeMeta: metav1.TypeMeta{
			Kind:       kind,
			APIVersion: apiVersion,
		},
		NeedsSync:  false,
		Parameters: map[string]string{},
		Errors:     []responseError{},
	}

	getErr := func() error {
		latest, err := automl.GetLatestDeployed(s.Project, s.Location, s.Name)

		if err != nil {
			appendError(response, fmt.Sprintf("Error getting latest model; %v", err))
			return err
		}

		if latest == nil {
			log.Infof("No deployed models found: project: %v, location: %v, Display Name: %v", s.Project, s.Location, s.Name)
		} else {
			response.Parameters["name"] = latest.GetName()
		}

		setterPath := []string{"openAPI", "definitions", "io.k8s.cli.setters." + s.SetterName, "x-k8s-cli", "setter", s.SetterName}
		current, err := kpt.GetKptSetter(s.KptFile, setterPath)

		if err != nil {
			appendError(response, fmt.Sprintf("Error getting current model; %v", err))
			return err
		}

		response.NeedsSync = current != latest.GetName()

		return nil
	}()

	if getErr != nil {
		log.Errorf("Error determining if sync needed; %v", getErr)
	}

	buf, err := json.Marshal(response)
	if err != nil {
		log.Errorf("Error marshling response; %v", err)
		w.WriteHeader(http.StatusInternalServerError)
		return
	}

	if len(response.Errors) > 0 {
		w.WriteHeader(http.StatusInternalServerError)
	}
	if _, err := w.Write(buf); err != nil {
		log.Errorf("Error writing response; %v", err)
	}
}
