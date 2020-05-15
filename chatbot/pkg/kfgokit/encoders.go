package kfgokit

import (
	"encoding/json"
	"github.com/go-kit/kit/endpoint"
	"golang.org/x/net/context"
	"net/http"
)

// EncodeResponse endodes responses.
// This is a generic json encoder. It takes arbitrary go structurs and encodes them as json.
func EncodeResponse(ctx context.Context, w http.ResponseWriter, response interface{}) error {
	// If the response
	if f, ok := response.(endpoint.Failer); ok && f.Failed() != nil {
		ErrorEncoder(ctx, f.Failed(), w)
		return nil
	}
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	return json.NewEncoder(w).Encode(response)
}
