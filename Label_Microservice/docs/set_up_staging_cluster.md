# Set Up a Staging Cluster for Issue Label Bot

2019-09-04

Authors: Chun-Hsiang Wang ([chunhsiang@google.com](mailto:chunhsiang@google.com))


# TL;DR

We have an [existing issue label bot](https://github.com/machine-learning-apps/Issue-Label-Bot) in production, which contains a flask app to handle GitHub payloads. Then, we create a [new microservice](https://github.com/kubeflow/code-intelligence/tree/master/Label_Microservice) to receive some traffic from the flask app and predict repository specific labels for those events. We have a [rollout design](https://docs.google.com/document/d/1HoY7rNGlDj_W5U74Ax8DC4umqz5wrW4ef4SB64N3vN4/edit#heading=h.c5xb2gcly2x8) for our new bot. Before the rollout of our new bot, we would like to set up a staging cluster including all microservices, like the flask app and workers for repo-specific label prediction, to confirm whether the whole procedures work well while processing real GitHub payloads.

This doc describes the scripts to create a staging cluster and configure all services in it. If we have new code changes, we can re-apply all settings and test the services. Furthermore, if we create more microservices for this project in the future, we can follow the steps in this doc to check the services are ready to be in production.


# Create a staging cluster


## Step 1. Create a cluster

Create a staging cluster using GCP console or run the following commands.

Set the default project.


```
gcloud config set project [PROJECT_ID]
```


Create a cluster.


```
gcloud container clusters create [CLUSTER_NAME] [--zone [COMPUTE_ZONE]]
```


Now, I have created a staging cluster called ``github-mlapp-test`` in the project ``issue-label-bot-dev``. You can directly access the cluster by the command.


```
gcloud container clusters get-credentials github-mlapp-test --zone us-east1-d
```


Result (**do not copy; this is example output**)


```
Fetching cluster endpoint and auth data.
kubeconfig entry generated for github-mlapp-test.
```


Create a namespace for the flask app.


```
kubectl create namespace mlapp
```


Result (**do not copy; this is example output**)


```
namespace/mlapp created
```



## Step 2. Create a testing GitHub app

For testing, you need to use another GitHub app to run as the bot in production. You need to register a testing GitHub app by following steps 1-4 of [this document](https://developer.github.com/apps/quickstart-guides/setting-up-your-development-environment/). Remember to store your ``APP_ID``, ``PRIVATE_KEY`` and ``WEBHOOK_SECRET``. And you will need to update the ``Webhook URL`` to be the flask app url later.

As documented in kubeflow/code-intelligence#84 we have created the 
**kf-label-bot-dev** GitHub App to be used for development with Kubeflow.
The PEM key for this bot is stored at

To create the secret in your dev cluster you can use the script 
`create_secrets.py`.

```
cd Label_Microservice/scripts
python3 create_secrets.py create-dev
```

You 

You should encode the ``APP_ID``, ``PRIVATE_KEY`` and ``WEBHOOK_SECRET`` with base64 encoder and modify the values in the file ``/tmp/ml-app-inference-secret-test.yaml`` if you would like to use your GitHub app to test the services. 

Then you need to apply the secret to the cluster.


```
kubectl apply -f /tmp/ml-app-inference-secret-test.yaml
```


Result (**do not copy; this is example output**)


```
secret/ml-app-inference-secret-test created
```


Because we use another namespace ``mlapp`` instead of ``default`` for the flask app, you need to apply the secret to the namespace ``mlapp``.


```
kubectl apply -f /tmp/ml-app-inference-secret-test.yaml -n mlapp
```


Result (**do not copy; this is example output**)


```
secret/ml-app-inference-secret-test created
```



## Step 3. Build the image for the flask app

In the repository [machine-learning-apps/Issue-Label-Bot](https://github.com/machine-learning-apps/Issue-Label-Bot), you can run a command in the root of the repository to build an image for testing and push it to Google Container Registry in the GCP project ``issue-label-bot-dev``.


```
sh script/bootstrap_test
```


It will build an image called `gcr.io/issue-label-bot-dev/github-mlapp-test:[TIMESTAMP]` and store it in GCR. We use the timestamp tag to separate the different versions of codes.

Modify the image used in the deployment of the flask app by adding the timestamp tag to the value of ``spec.template.spec.containers[0].image`` in the file [deployment/deployments-test.yaml](https://github.com/machine-learning-apps/Issue-Label-Bot/blob/master/deployment/deployments-test.yaml#L20).  You can check the built image name by seeing all docker images.


```
docker images
```


Result (**do not copy; this is example output**)


```
REPOSITORY                                     TAG                   IMAGE ID            CREATED            SIZE
hamelsmu/mlapp-test                            2019-08-28_17-49-37   61b186f93a05        18 hours ago       2.7GB
gcr.io/issue-label-bot-dev/github-mlapp-test   2019-08-28_17-49-37   61b186f93a05        18 hours ago       2.7GB
```


For example, the value you need to set is ``gcr.io/issue-label-bot-dev/github-mlapp-test:2019-08-28_17-49-37``.

After modifying the value of the image, create the deployment for testing flask app.


```
kubectl apply -f deployment/deployments-test.yaml
```


Result (**do not copy; this is example output**)


```
deployment.apps/ml-github-app-test created
```


Check the deployment.


```
kubectl get deployment -n mlapp
```


Result (**do not copy; this is example output**)


```
NAME                 DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
ml-github-app-test   1         1         1            1           32s
```


Create the service.


```
kubectl apply -f deployment/service-test.yaml
```


Result (**do not copy; this is example output**)


```
service/ml-github-app-test created
```


Check the service.


```
kubectl get services -n mlapp
```


Result (**do not copy; this is example output**)


```
NAME                 TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)          AGE
ml-github-app-test   NodePort    10.0.35.87   <none>        3000:30472/TCP   7d2h
```


Create the ingress.


```
kubectl apply -f deployment/ingress-test.yaml
```


Result (**do not copy; this is example output**)


```
ingress.extensions/ml-gh-app-test created
```


Check the ingress.


```
kubectl get ingress -n mlapp
```


Result (**do not copy; this is example output**)


```
NAME             HOSTS   ADDRESS   PORTS   AGE
ml-gh-app-test   *                 80      4s
```


You should wait for the address of the name ``ml-gh-app-test`` if it is pending. After several seconds, it should be generated and the output will change.

Result (**do not copy; this is example output**)


```
NAME             HOSTS   ADDRESS         PORTS   AGE
ml-gh-app-test   *       35.227.209.81   80      63s
```


You need to update the ``Webhook URL`` to be the address for your testing GitHub app on GitHub. For this example, ``Webhook URL`` of the testing GitHub app should be ``http://35.227.209.81/event_handler``.


## Step 4. Build the image for the repo-specific labeler

For repo-specific issue labeler, we use a GCP service account to handle permissions to access GCP resources such as GCS and Pub/Sub. You need to attach a key file of a service account to the kubernetes cluster by creating one using the command or downloading from GCP console.


```
gcloud iam service-accounts keys create ~/key.json \
  --iam-account [SA-NAME]@[PROJECT-ID].iam.gserviceaccount.com
```


Then, create a secret using the key file.


```
kubectl create secret generic user-gcp-sa --from-file=user-gcp-sa.json=[KEY_FILE_NAME]
```


Result (**do not copy; this is example output**)


```
secret/user-gcp-sa created
```


In the repository [kubeflow/code-intelligence](https://github.com/kubeflow/code-intelligence), we have a microservice to do repository specific issue prediction. You need to build the testing image for workers by running the command in the root of the repository.


```
sh Label_Microservice/scripts/bootstrap_test
```


It will build an image named ``gcr.io/issue-label-bot-dev/bot-worker-test:[TIMESTAMP]`` and push it to GCR. Same as the image for the flask app, we use the timestamp tag to separate the different versions of codes.

See the timestamp tag of the image and modify the value of ``spec.template.spec.containers[0].image`` in the file [Label_Microservice/deployment/deployments-test.yaml](https://github.com/kubeflow/code-intelligence/blob/master/Label_Microservice/deployment/deployments-test.yaml#L18).


```
docker images
```


Result (**do not copy; this is example output**)


```
REPOSITORY                                    TAG                   IMAGE ID            CREATED             SIZE
bot-worker-test                               2019-08-28_16-02-17   86caed80d5ab        20 hours ago        8.14GB
gcr.io/issue-label-bot-dev/bot-worker-test    2019-08-28_16-02-17   86caed80d5ab        20 hours ago        8.14GB
```


Change the value to be ``gcr.io/issue-label-bot-dev/bot-worker-test:2019-08-28_16-02-17``.

After modifying the value of the image, create the deployment for the microservice.


```
kubectl apply -f Label_Microservice/deployment/deployments-test.yaml
```


Result (**do not copy; this is example output**)


```
deployment.extensions/worker-test created
```


Check the deployment.


```
kubectl get deployment
```


Result (**do not copy; this is example output**)


```
NAME                 DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
worker-test          3         3         3            3           70s
```



## Step 5. Create issues to test the services

If you use your own testing GitHub app, you should install the app to your testing repositories and create issues to check the services work well.

For my testing GitHub app, I installed the app to my repositories (under my GitHub account ``abcdefgs0324``). Currently, there are two types of tests in two repositories.



*   Create issues in [the repository](https://github.com/abcdefgs0324/Issue-Label-Bot) that the events will be processed by the existing flask app and see whether the labels will be added normally.
*   To test whether the flask app forwards events to the repository specific microservice, we need to create issues in [the repository](https://github.com/abcdefgs0324/issue-label-bot-test), which we defined that all new issues in it need to always be forwarded to the microservice in the flask app according to [the yaml file](https://github.com/machine-learning-apps/Issue-Label-Bot/blob/master/flask_app/forwarded_repo.yaml).


# Test the services while code changes


## Option 1. Code changes in the flask app

Get the credentials of the staging cluster named ``github-mlapp-test`` in the project ``issue-label-bot-dev`` by the command.


```
gcloud container clusters get-credentials github-mlapp-test --zone us-east1-d
```


Result (**do not copy; this is example output**)


```
Fetching cluster endpoint and auth data.
kubeconfig entry generated for github-mlapp-test.
```


If you need to set new variables to be passed as secrets or update variables such as changing a testing GitHub app, you need to download the testing yaml config file from GCS and update the values.


```
gsutil cp gs://github-probots_secrets/ml-app-inference-secret-test.yaml /tmp
```


After updating the file, you need to apply the secret to the cluster.


```
kubectl apply -f /tmp/ml-app-inference-secret-test.yaml -n mlapp
```


Result (**do not copy; this is example output**)


```
secret/ml-app-inference-secret-test configured
```


While there are code changes in the flask app (ie, [the repository](https://github.com/machine-learning-apps/Issue-Label-Bot)), you should build a new image for the flask app by running the command in the root of the repository (almost following [step 3](#step-3-build-the-image-for-the-flask-app)).


```
sh script/bootstrap_test
```


Modify the image used in the deployment of the flask app by adding the timestamp tag to the value of ``spec.template.spec.containers[0].image`` in the file [deployment/deployments-test.yaml](https://github.com/machine-learning-apps/Issue-Label-Bot/blob/master/deployment/deployments-test.yaml#L20).  You can check the built image name by seeing all docker images.


```
docker images
```


Result (**do not copy; this is example output**)


```
REPOSITORY                                     TAG                   IMAGE ID            CREATED            SIZE
hamelsmu/mlapp-test                            2019-08-28_17-49-37   61b186f93a05        18 hours ago       2.7GB
gcr.io/issue-label-bot-dev/github-mlapp-test   2019-08-28_17-49-37   61b186f93a05        18 hours ago       2.7GB
```


For example, the value you need to set is ``gcr.io/issue-label-bot-dev/github-mlapp-test:2019-08-28_17-49-37``. Also, remember to add more environment variables if you need them.

After updating the yaml file, re-apply the deployment for testing flask app.


```
kubectl apply -f deployment/deployments-test.yaml
```


Result (**do not copy; this is example output**)


```
deployment.apps/ml-github-app-test configured
```



## Option 2. Code changes in the repo-specific microservice

Get the credentials of the staging cluster named ``github-mlapp-test`` in the project ``issue-label-bot-dev`` by the command.


```
gcloud container clusters get-credentials github-mlapp-test --zone us-east1-d
```


Result (**do not copy; this is example output**)


```
Fetching cluster endpoint and auth data.
kubeconfig entry generated for github-mlapp-test.
```


If you need to set new variables to be passed as secrets or update variables such as changing a testing GitHub app, you need to download the testing yaml config file from GCS and update the values.


```
gsutil cp gs://github-probots_secrets/ml-app-inference-secret-test.yaml /tmp
```


After updating the file, you need to apply the secret to the cluster.


```
kubectl apply -f /tmp/ml-app-inference-secret-test.yaml
```


Result (**do not copy; this is example output**)


```
secret/ml-app-inference-secret-test configured
```


While there are code changes in the repo-specific microservice (ie, [the repository](https://github.com/kubeflow/code-intelligence)), you should build a new image for it by running the command in the root of the repository (almost following [step 4](#step-4-build-the-image-for-the-repo-specific-labeler)).


```
sh Label_Microservice/scripts/bootstrap_test
```


Modify the image used in the deployment of the microservice by adding the timestamp tag to the value of ``spec.template.spec.containers[0].image`` in the file [Label_Microservice/deployment/deployments-test.yaml](https://github.com/kubeflow/code-intelligence/blob/master/Label_Microservice/deployment/deployments-test.yaml#L18).


```
docker images
```


Result (**do not copy; this is example output**)


```
REPOSITORY                                    TAG                   IMAGE ID            CREATED             SIZE
bot-worker-test                               2019-08-28_16-02-17   86caed80d5ab        20 hours ago        8.14GB
gcr.io/issue-label-bot-dev/bot-worker-test    2019-08-28_16-02-17   86caed80d5ab        20 hours ago        8.14GB
```


Change the value to be ``gcr.io/issue-label-bot-dev/bot-worker-test:2019-08-28_16-02-17``. Also, remember to add more environment variables if you need them.

After updating the yaml file, re-apply the deployment for the microservice.


```
kubectl apply -f Label_Microservice/deployment/deployments-test.yaml
```


Result (**do not copy; this is example output**)


```
deployment.extensions/worker-test configured
```



## Option 3. New microservice

If you have new microservice and want to integrate it to the services. You need to build docker images and create the secrets, deployments and/or services that you need. You can also create a new namespace like the flask app to separate all settings from others. Then, get the credentials of the staging cluster and apply them by the steps similar to [step 3](#step-3-build-the-image-for-the-flask-app) and [step 4](#step-4-build-the-image-for-the-repo-specific-labeler).
