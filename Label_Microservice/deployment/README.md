# Deploying Workers for Label Microservice

This directory contains manifests for workers of the repo-specific label microservice.

This is currently running on a GKE cluster.


## Production

There is a dedicated instance running in

* **GCP project**: issue-label-bot-dev
* **cluster**: issue-label-bot

See [kubeflow/code-intelligence#70](https://github.com/kubeflow/code-intelligence/issues/70) for a log of how it was setup.

Deploying it

1. Use skaffold to build a new image.

   ```
   skaffold build
   ```

1. Update the image

   ```
   cd ..
   make update-diff-image
   ```

1. Hydrate the GitOps manifests

   ```
   cd ..
   make hydrate-prod
   ```

1. Commit and push the manifests

## Staging/Dev

There is a staging/dev instance running in a different namespace