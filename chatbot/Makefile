# Trigger a build and push.
.PHONY: push
push:
	skaffold render --output=../kubeflow_clusters/code-intelligence/acm-repo/dialogflow-webhook.yaml -v info
	git add ..
	git commit -m "Latest code"
	# TODO(jlewi): How can we avoid hardcoding the remote name
	git push jlewi

