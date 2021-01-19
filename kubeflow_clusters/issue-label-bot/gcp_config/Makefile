PROJECT_ARG=--project issue-label-bot-dev


.PHONY: list apply

list:
	gcloud deployment-manager deployments list $(PROJECT_ARG)

get:
	gcloud deployment-manager deployments describe issue-label-bot $(PROJECT_ARG)

preview:
	gcloud deployment-manager deployments update issue-label-bot $(PROJECT_ARG) \
		--config cluster-kubeflow.yaml \
		--preview

apply:
	gcloud deployment-manager deployments update issue-label-bot $(PROJECT_ARG)

cancel:
	gcloud deployment-manager deployments cancel-preview issue-label-bot $(PROJECT_ARG)
