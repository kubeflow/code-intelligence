
CONTEXT=issue-label-bot

hydrate-prod:
	rm -rf .build/prod
	mkdir -p .build/prod
	kustomize build -o .build/prod deployment/overlays/prod

apply-prod: hydrate-prod
	kubectl --context=$(CONTEXT) apply -f .build/prod