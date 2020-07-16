package client

import (
	"encoding/json"
	"github.com/kubeflow/code-intelligence/Label_Microservice/go/cmd/automl/pkg/server"
	"github.com/pkg/errors"
	"io/ioutil"
	"net/http"
)

type NeedsSyncClient struct {
	URL    string
	Client *http.Client
}

func (c *NeedsSyncClient) Get() (*server.NeedsSyncResponse, error) {
	resp, err := c.Client.Get(c.URL)

	if err != nil {
		return nil, errors.WithStack(errors.Wrapf(err, "Could not get %v", c.URL))
	}
	r := &server.NeedsSyncResponse{}

	if err != nil {
		return nil, errors.WithStack(errors.Wrapf(err, "There was a problem getting the GitHub installation id"))
	}

	if resp.StatusCode != http.StatusOK {
		// TODO(jlewi): Should we try to read the body and include that in the error message?
		return nil, errors.WithStack(errors.Errorf("Get %v returned statusCode %v; Response:\n%+v", c.URL, resp.StatusCode, resp))
	}

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, errors.WithStack(errors.Wrapf(err, "There was a problem reading the response body."))
	}

	err = json.Unmarshal(body, r)

	if err != nil {
		return nil, errors.WithStack(errors.Wrapf(err, "Could not unmarshal json:\n %v", string(body)))
	}

	return r, nil
}
