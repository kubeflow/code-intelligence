# Deploying This Microservice: GitHub Issue Featurizer

This directory contains manifests for the backend of the microservice that returns embeddings given an issue label and body.  This backend is associated with associated with gh-issue-labeler.com/text.

This is currently running on a GKE cluster.


## issue-label-bot-dev

There is a dedicated instance running in

* **GCP project**: issue-label-bot-dev
* **cluster**: issue-label-bot
* **namespace**: label-bot-prod


See [kubeflow/code-intelligence#70](https://github.com/kubeflow/code-intelligence/issues/70) for a log of how it was setup.

Deploying it

1. Use skaffold to build a new image.

   ```
   skaffold build
   ```

1. Edit the image

   ```
   cd deployment/overlays/prod
   kustomize edit set image gcr.io/issue-label-bot-dev/issue-embedding=gcr.io/issue-label-bot-dev/issue-embedding:${TAG}@${SHA}
   ```

1. Create the deployment

   ```
   cd Label_Microservice/deployment/overlays/prod
   kustomize build | kubectl apply -f -
   ```