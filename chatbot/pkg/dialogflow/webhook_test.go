package dialogflow

import (
	"encoding/json"
	"io/ioutil"
	"os"
	"path"
	"testing"
)

func Test_ParseRequest(t *testing.T) {
	wd , err := os.Getwd()

	if err != nil {
		t.Fatalf("Could not get working directory; %v", err)
	}

	testFile := path.Join(wd, "test_data", "request.json")

	b, err := ioutil.ReadFile(testFile)

	if err != nil {
		t.Fatalf("Could not read request from %v; error: %v", testFile, err)
	}

	request := &WebhookRequest{}
	if err := json.Unmarshal(b, request); err != nil {
		t.Fatalf("Could not unmarshal the request; error %v", err)
	}

	if request.OriginalDetectIntentRequest.Source != "slack" {
		t.Fatalf("For source Got %v; want slack",  request.OriginalDetectIntentRequest.Source)
	}
}