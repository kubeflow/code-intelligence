# Developer guide

## Skaffold

Skaffold is configured to build the artifacts on your cluster using kaniko

`skaffold.yaml` is currently configured to run on

* **project**: issue-label-bot-dev 
* **cluster**: issue-label-bot-dev-kf 
* **zone**: us-east1-d


Setup a namespace for your development

1. Create the namespace

   ```
   kubectl create namespace ${NAMESPACE}
   ```

1. Modify skaffold.yaml; change cluster.namespace to ${NAMESPACE}


   * Use a namespace without ISTIO side car injection turned on
   * Due to [GoogleContainerTools/skaffold#3442](https://github.com/GoogleContainerTools/skaffold/issues/3442) Skaffold won't work with Kaniko in namespaces with ISTIO side car injection turned on

1. Copy the GCP secret to use to push images

   ```
   NAMESPACE=<new kubeflow namespace>
   SOURCE=kubeflow
   NAME=user-gcp-sa
   SECRET=$(kubectl -n ${SOURCE} get secrets ${NAME} -o jsonpath="{.data.${NAME}\.json}" | base64 -d)
   kubectl create -n ${NAMESPACE} secret generic ${NAME} --from-literal="${NAME}.json=${SECRET}"
   ```

1. Set the namespace in `deployment/overlays/dev/kustomization.yaml`



## Next Steps

* Look into using [skaffold profiles](https://skaffold.dev/docs/environment/profiles/)