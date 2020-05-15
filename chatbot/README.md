# Chatbot

This is a Dialogflow fulfillment server.

## Deployment

It is currently running in

* **Full cluster name**: gke_issue-label-bot-dev_us-east1-d_issue-label-bot
* **project**: issue-label-bot-dev
* **cluster**: issue-label-bot

## Notes.

To expose the webhook we need to bypass IAP. To do this we create a second K8s service to create a second GCP Backend Service
but with IAP enabled.

```
kubectl --context=issue-label-bot-dev  -n istio-system create -f istio-ingressgateway.yaml
```

We need to modify the security policy applied at the ingress gateway so that it won't reject requests without a valid
JWT.

To deploy the fullfilment server we need to modify the Kubeflow ingress  policy to allow traffic from the dialgoflow webserver.
This traffic can't be routed through IAP. We will still use a JWT to restrict traffic but it will be a JWT we create.

So we need to add a second JWT origin rule to match this traffic to the policy.

We can do this as

```
kubectl --context=issue-label-bot-dev -n istio-system patch policy  ingress-jwt -p "$(cat ingress-jwt.patch.yaml)" --type=merge
```

To verify that is working we can port-forward to the service.

```
kubectl --context=issue-label-bot-dev  -n istio-system port-forward service/chatbot-istio-ingressgateway 9080:80
```

Send a request with a JWT this should fail with "Origin Authentication Failure" since there is no JWT.

```
curl localhost:9080/chatbot/dev/  -d '{}' -H "Content-Type: application/json" 
```



To authorize Dialogflow webhook we will use a JWT.  We use the jose-util to generate a public private key pair

```
git clone git@github.com:square/go-jose.git git_go-jose
cd git_go-jose/jose-uitl
go build.
```

Generate a key pair


```
./jose-util generate-key --alg=ES256 --use sig --kid=chatbot
```

Upload the public bit to a public GCS bucket

```
https://storage.cloud.google.com/issue-label-bot-dev_public/chatbot/keys/jwk-sig-chatbot-pub.json
```

## Referencess

* [ISTIO 1.1 Policy Resource](https://archive.istio.io/v1.1/docs/reference/config/istio.authentication.v1alpha1/#Policy)
* [ISTIO 1.5 JWT policy example](https://istio.io/docs/tasks/security/authorization/authz-jwt/)
  * This example includes some static JWTs that can be used for testing.