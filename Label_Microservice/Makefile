# TODO(jlewi): Need to sort out root vs project level Makefiles
CONTEXT=label-bot-dev

hydrate-prod:
	rm -f ../acm-repos/issue-label-bot/namespaces/label-bot-prod/*
	kustomize build -o ../acm-repos/issue-label-bot/namespaces/label-bot-prod deployment/overlays/prod
	kustomize build -o ../acm-repos/issue-label-bot/namespaces/label-bot-prod auto-update/prod

# TODO this is duplicated in the root Makefile
apply-dev:
	kustomize build ./auto-update/dev | kubectl --context=$(CONTEXT) apply -f - 

update-image:    
	skaffold build --kube-context=${CONTEXT} -v info --file-output=latest_image.json
	cd deployment/overlays/prod && kustomize edit set image gcr.io/issue-label-bot-dev/bot-worker=$(shell yq r latest_image.json builds[0].tag )

build-diff-image:
	skaffold build --kube-context=${CONTEXT} -b gcr.io/issue-label-bot-dev/labelbot-diff -v info --file-output=labelbot-diff.image.json

set-diff-image:
	cd auto-update/base && kustomize edit set image gcr.io/issue-label-bot-dev/labelbot-diff=$(shell yq r labelbot-diff.image.json builds[0].tag )

update-diff-image: build-diff-image set-diff-image
	
	
