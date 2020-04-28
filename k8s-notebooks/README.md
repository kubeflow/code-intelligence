# Notebook Manifests

TODO(jlewi): kpt setters aren't properly configured yet
  * volumes need to be properly set

This directory contains a kustomize package for spinning up
a notebook on Kubeflow to run the example.

Create a secret with the GITHUB_TOKEN

```
kubectl -n kubeflow-jlewi create secret generic github-token --from-literal=github_token=${GITHUB_TOKEN}
```

