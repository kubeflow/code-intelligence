package automl

import (
	"google.golang.org/api/iterator"
	"google.golang.org/genproto/googleapis/cloud/automl/v1"
	"google.golang.org/protobuf/types/known/timestamppb"
	"testing"
	"time"
)

type ModelList struct {
	models []*automl.Model
	pos    int
}

func (it *ModelList) Next() (*automl.Model, error) {
	if it.pos >= len(it.models) {
		return nil, iterator.Done
	}

	it.pos = it.pos + 1
	return it.models[it.pos-1], nil
}

func buildModel(name string, displayName string, createTime time.Time, state automl.Model_DeploymentState) *automl.Model {
	m := &automl.Model{}

	m.Name = name
	m.DisplayName = displayName
	m.CreateTime = timestamppb.New(createTime)
	m.DeploymentState = state
	return m
}

func TestGetLatestDeployed(t *testing.T) {
	type testCase struct {
		models   []*automl.Model
		expected string
	}

	now := time.Now()
	testCases := []testCase{
		{
			models: []*automl.Model{
				buildModel("oldest", "some_model", now.Add(-10*time.Hour), automl.Model_DEPLOYED),
				buildModel("newest", "some_model", now.Add(10*time.Hour), automl.Model_DEPLOYED),
				buildModel("2nd-oldest", "some_model", now.Add(5*time.Hour), automl.Model_DEPLOYED),
			},
			expected: "newest",
		},
	}

	for _, c := range testCases {
		it := &ModelList{
			models: c.models,
			pos:    0,
		}

		latest, err := getLatestDeployedFromIt(it, "some_model")
		if err != nil {
			t.Errorf("Could not get latest model %v", err)
			continue
		}

		if latest.Name != c.expected {
			t.Errorf("Got %v; Want %v", latest.Name, c.expected)
		}
	}
}
