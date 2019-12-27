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

1. Create the secret

   ```
    gsutil cp gs://github-probots_secrets/ml-app-inference-secret-test.yaml ~/secrets/
    <edit ml-app-inference-secret-test.yaml; change the name to drop the "-test" suffix>
    kubectl -n ${NAMESPACE} create -f ~/secrets/ml-app-inference-secret-test.yaml
   ```

1. Set the namespace in `deployment/overlays/dev/kustomization.yaml`

1. Start skaffold

   ```
   skaffold dev -v info --cleanup=false
   ```

1. Follow the developer guide for issue embedding microservice to start the dev version of the issue embedding service

   * That service should only be needed if you want to use repo specific models as opposed to the universal model

1. Port-forward the local port to the remote service

   ```
   kubectl -n ${NAMESPACE} port-forward service/label-bot-worker 8080:80
   ```

   * TODO(jlewi): skaffold supposedly will create local port-forwarding automatically; need to investigate that; looks
     like it might require an additional flag to skaffold and require ports to be declared.


1. Send a prediction request

   ```
   curl -d '{"title":"some title", "text":"sometext"}' -H "Content-Type: application/json" -X POST http://localhost:8080/predict
   ```   
## Unresolved Issues

* skaffold continuous mode (`skaffold dev` ) doesn't appear to detect changes in the python files and retrigger the build and deployment


### Kaniko Image Caching

* Kaniko will cache the output of RUN commands using remote layers ([info](https://github.com/GoogleContainerTools/kaniko#caching))

* This means the command `RUN pip install -r requirements.worker.txt` will result in a cached layer

  * **TODO(jlewi)** When using skaffold and kaniko its not clear whether the cache is being invalidated when requirements.worker.txt is changing.


## Next Steps

* Can we use [Skaffold sync](https://skaffold.dev/docs/references/yaml/) to sync the python code into the container
  so we can skip rebuilds?
  * Can we use Flask reloader to auto-reload the code when it changes?
* Look into using [skaffold profiles](https://skaffold.dev/docs/environment/profiles/)