CONTEXT=label-bot-dev
PRCTL_IMAGE=/home/jlewi/git_kubeflow-testing/go/prctl_latest_image.json

# Deploy the latest tekton tasks in dev
apply-dev:
	kustomize build tekton/installs/dev | kubectl --context=$(CONTEXT) apply -f -
	kustomize build Label_Microservice/auto-update/dev | kubectl --context=$(CONTEXT) apply -f -

set-prctl-image:
	kpt cfg set ./tekton prctl-image $(shell yq r $(PRCTL_IMAGE) builds[0].tag)
