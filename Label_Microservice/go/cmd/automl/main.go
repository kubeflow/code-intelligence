// When using EUC as application-default you may need to run
// gcloud auth application-default set-quota-project ${PROJECT}
// to set the billing project

package main

import (
	automl "cloud.google.com/go/automl/apiv1"
	"context"
	"flag"
	"fmt"
	"github.com/golang/protobuf/proto"
	"github.com/onrik/logrus/filename"
	log "github.com/sirupsen/logrus"
	"google.golang.org/api/iterator"
	automlpb "google.golang.org/genproto/googleapis/cloud/automl/v1"
	"gopkg.in/yaml.v2"
	"io/ioutil"
)

// From https://stackoverflow.com/questions/28969455/how-to-properly-instantiate-os-filemode
const (
	OS_READ        = 04
	OS_WRITE       = 02
	OS_EX          = 01
	OS_USER_SHIFT  = 6
	OS_GROUP_SHIFT = 3
	OS_OTH_SHIFT   = 0

	OS_USER_R   = OS_READ << OS_USER_SHIFT
	OS_USER_W   = OS_WRITE << OS_USER_SHIFT
	OS_USER_X   = OS_EX << OS_USER_SHIFT
	OS_USER_RW  = OS_USER_R | OS_USER_W
	OS_USER_RWX = OS_USER_RW | OS_USER_X

	OS_GROUP_R   = OS_READ << OS_GROUP_SHIFT
	OS_GROUP_W   = OS_WRITE << OS_GROUP_SHIFT
	OS_GROUP_X   = OS_EX << OS_GROUP_SHIFT
	OS_GROUP_RW  = OS_GROUP_R | OS_GROUP_W
	OS_GROUP_RWX = OS_GROUP_RW | OS_GROUP_X

	OS_OTH_R   = OS_READ << OS_OTH_SHIFT
	OS_OTH_W   = OS_WRITE << OS_OTH_SHIFT
	OS_OTH_X   = OS_EX << OS_OTH_SHIFT
	OS_OTH_RW  = OS_OTH_R | OS_OTH_W
	OS_OTH_RWX = OS_OTH_RW | OS_OTH_X

	OS_ALL_R   = OS_USER_R | OS_GROUP_R | OS_OTH_R
	OS_ALL_W   = OS_USER_W | OS_GROUP_W | OS_OTH_W
	OS_ALL_X   = OS_USER_X | OS_GROUP_X | OS_OTH_X
	OS_ALL_RW  = OS_ALL_R | OS_ALL_W
	OS_ALL_RWX = OS_ALL_RW | OS_GROUP_X
)

// getLatestDeployed finds the latest deployed model
//
// TODO(jlewi): We should really filter on labels; they don't appear to show up in the UI but they
// are in the API: https://cloud.google.com/automl/docs/reference/rest/v1/projects.locations.models#Model
func getLatestDeployed(projectID string, location string, modelName string) (*automlpb.Model, error) {
	// projectID := "my-project-id"
	// location := "us-central1"

	ctx := context.Background()
	client, err := automl.NewClient(ctx)
	if err != nil {
		return nil, fmt.Errorf("NewClient: %v", err)
	}
	defer client.Close()

	req := &automlpb.ListModelsRequest{
		Parent: fmt.Sprintf("projects/%s/locations/%s", projectID, location),
	}

	it := client.ListModels(ctx, req)

	var latest *automlpb.Model
	// Iterate over all results
	for {
		model, err := it.Next()
		if err == iterator.Done {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("ListModels.Next: %v", err)
		}

		if model.GetDisplayName() != modelName {
			continue
		}
		// Skip undeployed models
		if model.GetDeploymentState() != automlpb.Model_DEPLOYED {
			log.Infof("Skipping model %v; it is in state %v", model.GetName(), model.GetDeploymentState())
		}

		if latest == nil || latest.CreateTime == nil || latest.GetCreateTime().AsTime().Before(model.GetCreateTime().AsTime()) {
			latest = &automlpb.Model{}
			proto.Merge(latest, model)
		}
	}

	return latest, nil
}

func init() {
	// Add filename as one of the fields of the structured log message.
	filenameHook := filename.NewHook()
	filenameHook.Field = "filename"
	log.AddHook(filenameHook)
}

func main() {
	var project = flag.String("context", "issue-label-bot-dev", "Project to get AutoML models for")
	var location = flag.String("location", "us-central1", "Location to search for models")
	var name = flag.String("name", "kubeflow_issues_with_repo", "The display name of the model; only models with this name will be considered")
	var output = flag.String("output", "", "(Optional) If supplied the model info is written to this file in YAML format")

	flag.Parse()

	latest, err := getLatestDeployed(*project, *location, *name)

	if err != nil {
		log.Fatalf("Failed to list models; error %v", err)
	}

	if latest == nil {
		log.Errorf("No deployed models found: project: %v, location: %v, Display Name: %v", project, location, name)
		return
	}

	log.Infof("Latest model: %v", latest.GetName())

	if *output != "" {
		log.Infof("Writing model information to: %v", *output)

		b, err := yaml.Marshal(latest)

		if err != nil {
			log.Errorf("Error marshaling YAML: %v", err)
			return
		}

		ioutil.WriteFile(*output, b, OS_ALL_R)
	}
	log.Infof("Getting models succeeded.")
}
