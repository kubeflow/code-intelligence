# Deploying Workers for Label Microservice

This directory contains manifests for workers of the repo-specific label microservice.

This is currently running on a GKE cluster.


## Production

There is a dedicated instance running in

* **GCP project**: issue-label-bot-dev
* **cluster**: workers

Deploying it

1. Create the deployment

   ```
   kubectl apply -f deployments.yaml  
   ```

1. Create the secret

   ```
   gsutil cp gs://github-probots_secrets/ml-app-inference-secret.yaml /tmp
   kubectl apply -f /tmp/ml-app-inference-secret.yaml
   ```


## Testing

There is a staging cluster running in

* **GCP project**: issue-label-bot-dev
* **cluster**: github-mlapp-test

Deploying it

1. Create the deployment

   ```
   kubectl apply -f deployments-test.yaml  
   ```

1. Create the secret

   ```
   gsutil cp gs://github-probots_secrets/ml-app-inference-secret-test.yaml /tmp
   kubectl apply -f /tmp/ml-app-inference-secret-test.yaml
   ```

