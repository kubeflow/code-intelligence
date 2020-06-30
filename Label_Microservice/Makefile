
CONTEXT=issue-label-bot

hydrate-prod:
	rm -f ../acm-repos/issue-label-bot/namespaces/label-bot-prod/*
	kustomize build -o ../acm-repos/issue-label-bot/namespaces/label-bot-prod deployment/overlays/prod

update-image:    
	skaffold build --kube-context=${CONTEXT} -v info --file-output=latest_image.json
	cd deployment/overlays/prod && kustomize edit set image gcr.io/issue-label-bot-dev/bot-worker=$(shell yq r latest_image.json builds[0].tag )
