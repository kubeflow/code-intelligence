CONTEXT=label-bot-dev
PRCTL_IMAGE=/home/jlewi/git_kubeflow-testing/go/prctl_latest_image.json

# Deploy the latest tekton tasks in dev
apply-dev:
	cd Label_Microservice && make apply-dev

set-prctl-image:
	kpt cfg set ./tekton prctl-image $(shell yq r $(PRCTL_IMAGE) builds[0].tag)
