package dialogflow

import "context"

// Define go structs to deserialize Dialgoflow webhooks into.
// Code is copied from
// https://cloud.google.com/dialogflow/docs/fulfillment-webhook#go

type Intent struct {
	DisplayName string `json:"displayName"`
}

type QueryResult struct {
	Intent Intent `json:"intent"`
	QueryText string `json:"queryText"`
	Parameters map[string]string `json:"parameters"`
}

type Text struct {
	Text []string `json:"text"`
}

type Message struct {
	Text Text `json:"text"`
}

// WebhookRequest is used to unmarshal a WebhookRequest JSON object. Note that
// not all members need to be defined--just those that you need to process.
// As an alternative, you could use the types provided by
// the Dialogflow protocol buffers:
// https://godoc.org/google.golang.org/genproto/googleapis/cloud/dialogflow/v2#WebhookRequest
type WebhookRequest struct {
	Session     string      `json:"session"`
	ResponseID  string      `json:"responseId"`
	QueryResult QueryResult `json:"queryResult"`
	OriginalDetectIntentRequest OriginalDetectIntentRequest `json:"originalDetectIntentRequest"`
}

type OriginalDetectIntentRequest struct {
	Source string `json:"source"`
	Version string `json:"version"`
	Payload interface{}
}


// WebhookResponse is used to marshal a WebhookResponse JSON object. Note that
// not all members need to be defined--just those that you need to process.
// As an alternative, you could use the types provided by
// the Dialogflow protocol buffers:
// https://godoc.org/google.golang.org/genproto/googleapis/cloud/dialogflow/v2#WebhookResponse
type WebhookResponse struct {
	FulfillmentMessages []Message `json:"fulfillmentMessages"`
}

// DialogFlowWebhookService defines an interface for handling Dialgflow webhook fulfillments.
// https://cloud.google.com/dialogflow/docs/fulfillment-webhook#go
type DialogFlowWebhookService interface {
	HandleWebhook(ctx context.Context, req WebhookRequest) (*WebhookResponse, error)
}