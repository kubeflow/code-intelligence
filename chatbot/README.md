# Chatbot

This is a Dialogflow fulfillment server.

## Deployment

It is currently running in

* **project**: issue-label-bot-dev
* **cluster**: code-intelligence

It is deployed through ACM. To deploy it

```
skaffold render --output=../kubeflow_clusters/code-intelligence/acm-repo/dialogflow-webhook.yaml
```

Then commit and push the updated manifests to ACM

## Notes.

To expose the webhook we need to bypass IAP. To do this we create a second K8s service to create a second GCP Backend Service
but with IAP enabled.

This requires the following modifications

* `kubeflow_clusters/code-intelligence/dialogflow-ingress.yaml` this file defines the Kubernetes service and backendconfig
* `kubeflow_clusters/code-intelligence/extensions_v1beta1_ingress_envoy-ingress.yaml` - We modify our existing
   gateway to add a second path which won't have IAP enabled.


 We need to manually modify the GCP health check associated with this backend

 * Set the path to "/healthz/ready"
 * Set the target port to the node port mapped to the istio status-port

### Authorization using manual JWTs

We need to modify the security policy applied at the ingress gateway so that it won't reject requests without a valid
JWT.

To deploy the fullfilment server we need to modify the Kubeflow ingress  policy to allow traffic from the dialgoflow webserver.
This traffic can't be routed through IAP. We will still use a JWT to restrict traffic but it will be a JWT we create.

So we need to add a second JWT origin rule to match this traffic to the policy.


#### Creating a JWT

To generate JWTs we use the [jose-util](https://github.com/square/go-jose/tree/master/jose-util).

First we need to generate a public-private key pair to sign JWTs.


```
git clone git@github.com:square/go-jose.git git_go-jose
cd git_go-jose/jose-uitl
go build.
```

Generate a key pair


```
./jose-util generate-key --alg=ES256 --use sig --kid=chatbot
```

This will generate a json file.

Convert this to a JWK file. A JWK file is just a json file which has a list of keys; the keys being the contents of the
the json file outputted by jose-util. 


Upload the public bit to a public GCS bucket. The following is our current public key.


```
https://storage.cloud.google.com/issue-label-bot-dev_public/chatbot/keys/jwk-sig-chatbot-pub.json
```


JWT's are bearer tokens so be sure to keep it secret. These JWTs also currently don't expire. 

We modify the ISTIO policy to accept this JWT for paths prefixed by /chatbot; see `kubeflow_clusters/code-intelligence/acm-repo/authentication.istio.io_v1alpha1_policy_ingress-jwt.yaml`

To verify that is working try sending a request without a JWT

```
curl https://code-intelligence.endpoints.issue-label-bot-dev.cloud.goog/chatbot/
```

* This should fail with error "Origin Authentication Failure"

Now generate a JWT using the binary 

We can do this using the binary `cmd/jwt`

```
cd cmd/jwt
go build .
./jwt
```

Send a request using this JWT in the header

```
curl https://code-intelligence.endpoints.issue-label-bot-dev.cloud.goog/chatbot/ -H "Authorization: Bearer ${CHATBOTJWT}"

```

* This request should succeed.

To test the webhook path

```
curl https://code-intelligence.endpoints.issue-label-bot-dev.cloud.goog/chatbot/dev/dialogflow/webhook -H "Authorization: Bearer ${CHATBOTJWT}" -d '{}' -H "Content-Type: application/json" 
```

## Referencess

* [ISTIO 1.1 Policy Resource](https://archive.istio.io/v1.1/docs/reference/config/istio.authentication.v1alpha1/#Policy)
* [ISTIO 1.5 JWT policy example](https://istio.io/docs/tasks/security/authorization/authz-jwt/)
  * This example includes some static JWTs that can be used for testing.