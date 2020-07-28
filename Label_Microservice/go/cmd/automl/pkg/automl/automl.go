package automl

import (
	"bufio"
	automl "cloud.google.com/go/automl/apiv1"
	"context"
	"encoding/csv"
	"fmt"
	"github.com/golang/protobuf/proto"
	"github.com/pkg/errors"
	log "github.com/sirupsen/logrus"
	"google.golang.org/api/iterator"
	automlpb "google.golang.org/genproto/googleapis/cloud/automl/v1"
	"google.golang.org/genproto/protobuf/field_mask"
	"os"
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

func getLatestTrainedFromIt(it ModelIterator, modelName string) (*automlpb.Model, error) {
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

// GetLatestTrained finds the latest trained model
//
// TODO(jlewi): We should really filter on labels; they don't appear to show up in the UI but they
// are in the API: https://cloud.google.com/automl/docs/reference/rest/v1/projects.locations.models#Model
func GetLatestTrained(projectID string, location string, modelName string) (*automlpb.Model, error) {
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
	return getLatestTrainedFromIt(it, modelName)
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

// GetModelEvaluation gets the evaluation for the specified model
func GetModelEvaluation(name string, outputFile string) (*automlpb.ModelEvaluation, error) {
	ctx := context.Background()
	client, err := automl.NewClient(ctx)
	if err != nil {
		return nil, fmt.Errorf("NewClient: %v", err)
	}
	defer client.Close()

	req := &automlpb.ListModelEvaluationsRequest{
		Parent: name,
	}

	var w *csv.Writer
	if outputFile == "" {
		w = csv.NewWriter(os.Stdout)
	} else {
		f, err := os.Create(outputFile)
		if err != nil {
			return nil, err
		}

		defer f.Close()
		w = csv.NewWriter(bufio.NewWriter(f))
	}

	defer w.Flush()
	it := client.ListModelEvaluations(ctx, req)
	
	w.Write([]string{"Label", "Precision", "Recall", "Threshold" })

	// Iterate over all results
	for {
		e, err := it.Next()
		if err == iterator.Done {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("ListModelEvaluationsRequest.Next: %v", err)
		}

		toString:= func(f float32) string {
			return fmt.Sprintf("%v", f)
		}
		m := e.GetClassificationEvaluationMetrics()
		for i, entry := range m.GetConfidenceMetricsEntry() {
			// Find the first entry that is <=.5
			if i == len(m.GetConfidenceMetricsEntry()) || m.GetConfidenceMetricsEntry()[i+1].GetConfidenceThreshold() > .5 {
				w.Write([]string{e.GetDisplayName(),  toString(entry.GetPrecision()), toString(entry.GetRecall()), toString(entry.GetConfidenceThreshold())})
				break
			}

		}

		//log.Infof("Evaluation: %+v, %+v", e, m.GetAuRoc())
	}

	//
	//if err != nil {
	//	return nil, err
	//}

	return nil, nil
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
