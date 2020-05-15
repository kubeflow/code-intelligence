package kfgokit

import (
"bytes"
"encoding/json"
"golang.org/x/net/context"
"io/ioutil"
"net/http"
)

func err2code(err error) int {
	// TODO(jlewi): We should map different errors to different http status codes.
	return http.StatusInternalServerError
}

// ErrorEncoder is a custom error used to encode errors into the http response.
// If the error is of type httpError then is used to obtain the statuscode.
// TODO(jlewi): Should we follow the model
func ErrorEncoder(_ context.Context, err error, w http.ResponseWriter) {
	h, ok := err.(*httpError)

	if ok {
		w.WriteHeader(h.Code)
	} else {
		w.WriteHeader(err2code(err))
	}
	json.NewEncoder(w).Encode(err)
}

// httpError allows us to attach add an http status code to an error
//
// Inspired by on https://cloud.google.com/apis/design/errors
//
// TODO(jlewi): We should support adding an internal message that would be logged on the server but not returned
// to the user. We should attach to that log message a unique id that can also be returned to the user to make
// it easy to look errors shown to the user and our logs.
type httpError struct {
	Message string
	Code    int
}

func (e *httpError) Error() string {
	return e.Message
}

type errorWrapper struct {
	Error string `json:"error"`
}

// encodeHTTPGenericRequest is a transport/http.EncodeRequestFunc that
// JSON-encodes any request to the request body. Primarily useful in a client.
func encodeHTTPGenericRequest(_ context.Context, r *http.Request, request interface{}) error {
	var buf bytes.Buffer
	if err := json.NewEncoder(&buf).Encode(request); err != nil {
		return err
	}
	r.Body = ioutil.NopCloser(&buf)
	return nil
}
