package client

import (
	"encoding/json"
	"github.com/kubeflow/code-intelligence/Label_Microservice/go/cmd/automl/pkg/server"
	"net/http"
	"reflect"
)

// Ref: http://hassansin.github.io/Unit-Testing-http-client-in-Go

import (
	"bytes"
	"io/ioutil"
	"testing"
)

// RoundTripFunc .
type RoundTripFunc func(req *http.Request) *http.Response

// RoundTrip .
func (f RoundTripFunc) RoundTrip(req *http.Request) (*http.Response, error) {
	return f(req), nil
}

//NewTestClient returns *http.Client with Transport replaced to avoid making real calls
func NewTestClient(fn RoundTripFunc) *http.Client {
	return &http.Client{
		Transport: RoundTripFunc(fn),
	}
}

func Test_Get(t *testing.T) {

	type testCase struct {
		expected     *server.NeedsSyncResponse
		responseCode int
	}

	cases := []testCase{
		{
			expected: &server.NeedsSyncResponse{
				NeedsSync: true,
				Parameters: map[string]string{
					"param1": "value1",
				},
			},
			responseCode: http.StatusOK,
		},
	}

	for _, i := range cases {
		client := NewTestClient(func(req *http.Request) *http.Response {
			b, err := json.Marshal(i.expected)
			if err != nil {
				t.Fatalf("Could not marshal response; error %v", err)
			}
			return &http.Response{
				StatusCode: i.responseCode,
				// Send response to be tested
				Body: ioutil.NopCloser(bytes.NewBuffer(b)),
				// Must be set to non-nil value or it panics
				Header: make(http.Header),
			}
		})

		c := NeedsSyncClient{
			URL:    "http://someUrl",
			Client: client,
		}

		resp, err := c.Get()

		if err != nil {
			t.Errorf("Could not get result; %v", err)
			continue
		}

		if !reflect.DeepEqual(resp, i.expected) {
			t.Errorf("Got %+v; Want %+v", resp, i.expected)
		}
	}

}
