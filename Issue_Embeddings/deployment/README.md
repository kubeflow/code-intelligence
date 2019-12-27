# Deploying This Microservice: GitHub Issue Featurizer

This directory contains manifests for the backend of the microservice that returns embeddings given an issue label and body.  This backend is associated with associated with gh-issue-labeler.com/text.

This is currently running on a GKE cluster.


## issue-label-bot-dev

There is a dedicated instance running in

* **GCP project**: issue-label-bot-dev
* **cluster**: github-api-cluster
* **namespace**: issuefeat

Deploying it

1. Create the deployment

   ```
   kustomize build deployment/overlays/dev | kubectl apply -f -
   ```

   * TODO(jlewi): We should probably define suitable prod and possibly staging environments as well

1. You can also follow the [developer_guide.md](../developer_guide.md) to deploy it using skaffold

1. TODO(jlewi): Add instructions for how to build and update the images; one way to do this would be to use
   `skaffold build` followed by `kustomize edit`

   * We may need/want to use skaffold profiles to define GCR buckets corresponding to dev, staging, and prod