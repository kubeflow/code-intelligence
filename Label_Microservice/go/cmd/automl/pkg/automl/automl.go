package automl

import (
	automl "cloud.google.com/go/automl/apiv1"
	"context"
	"fmt"
	"github.com/golang/protobuf/proto"
	"github.com/pkg/errors"
	log "github.com/sirupsen/logrus"
	"google.golang.org/api/iterator"
	automlpb "google.golang.org/genproto/googleapis/cloud/automl/v1"
	"google.golang.org/genproto/protobuf/field_mask"
)

type ModelIterator interface {
	Next() (*automlpb.Model, error)
}

func getLatestDeployedFromIt(it ModelIterator, modelName string) (*automlpb.Model, error) {
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
			continue
		}

		if latest == nil || latest.CreateTime == nil || latest.GetCreateTime().AsTime().Before(model.GetCreateTime().AsTime()) {
			latest = &automlpb.Model{}
			proto.Merge(latest, model)
		}
	}

	return latest, nil
}

// GetLatestDeployed finds the latest deployed model
//
// TODO(jlewi): We should really filter on labels; they don't appear to show up in the UI but they
// are in the API: https://cloud.google.com/automl/docs/reference/rest/v1/projects.locations.models#Model
func GetLatestDeployed(projectID string, location string, modelName string) (*automlpb.Model, error) {
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
	return getLatestDeployedFromIt(it, modelName)
}

// GetModel gets the specified model
func GetModel(name string) (*automlpb.Model, error) {
	ctx := context.Background()
	client, err := automl.NewClient(ctx)
	if err != nil {
		return nil, fmt.Errorf("NewClient: %v", err)
	}
	defer client.Close()

	req := &automlpb.GetModelRequest{
		Name: name,
	}

	return client.GetModel(ctx, req)
}

// labelModel labels the specified model
//
// TODO(jlewi): Should we support removing labels?
func LabelModel(name string, labels map[string]string) error {
	ctx := context.Background()
	client, err := automl.NewClient(ctx)
	if err != nil {
		return fmt.Errorf("NewClient: %v", err)
	}
	defer client.Close()

	req := &automlpb.GetModelRequest{
		Name: name,
	}

	model, err := client.GetModel(ctx, req)

	if err != nil {
		return errors.WithStack(errors.Wrapf(err, "Error getting model %v", name))
	}

	if model.Labels == nil {
		model.Labels = map[string]string{}
	}
	for k, v := range labels {
		model.Labels[k] = v
	}

	uReq := &automlpb.UpdateModelRequest{
		Model: model,
		UpdateMask: &field_mask.FieldMask{
			Paths: []string{"labels"},
		},
	}

	_, err = client.UpdateModel(ctx, uReq)

	return err
}
