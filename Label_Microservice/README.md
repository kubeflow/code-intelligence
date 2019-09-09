# Repo-Specific Label Microservice

This folder contains the service that receives an issue as input and returns repo-specific label predictions.


## Summary

There are two services now.

- The flask app produces three types of labels for all repositories or forwards traffic to Cloud Pub/Sub.

- The repo-specific label microservice (in this folder) handles events in Cloud Pub/Sub and generates repo-specific labels according to repositories.


## Production

1. The flask app
    - **repository**: [machine-learning-apps/Issue-Label-Bot](https://github.com/machine-learning-apps/Issue-Label-Bot)
    - **GCP project**: github-probots
    - **cluster**: kf-ci-ml
    - **namespace**: mlapp

1. Repo-specific label microservice
    - **repository**: [kubeflow/code-intelligence](https://github.com/kubeflow/code-intelligence/tree/master/Label_Microservice)
    - **GCP project**: issue-label-bot-dev
    - **cluster**: workers
    - **namespace**: default


## Testing

1. The flask app
    - **repository**: [machine-learning-apps/Issue-Label-Bot](https://github.com/machine-learning-apps/Issue-Label-Bot)
    - **GCP project**: issue-label-bot-dev
    - **cluster**: github-mlapp-test
    - **namespace**: mlapp

1. Repo-specific label microservice
    - **repository**: [kubeflow/code-intelligence](https://github.com/kubeflow/code-intelligence/tree/master/Label_Microservice)
    - **GCP project**: issue-label-bot-dev
    - **cluster**: github-mlapp-test
    - **namespace**: default
