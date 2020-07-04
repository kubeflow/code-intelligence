# Continuously Retraining and Updating the model

:warning: These docs are work in progress. See [kubeflow/code-intelligence#155](https://github.com/kubeflow/code-intelligence/issues/155)


## How PRs are created

SSH deploy keys are used to push commits to a branch of kubeflow/code-intelligence. [Tekton](https://github.com/tektoncd/pipeline/blob/master/docs/auth.md) handles most of the setup required for enabling ssh access. 

## Git Authentication

Refer to the [Tekton docs](https://github.com/tektoncd/pipeline/blob/master/docs/auth.md) for information
on authenticating to git using ssh.

We use [deploy-keys](https://developer.github.com/v3/guides/managing-deploy-keys/#deploy-keys) to grant ssh access to the bot

* The private key is stored in the secret manager key [label-bot-ssh-private](https://console.cloud.google.com/security/secret-manager/secret/label-bot-ssh-private?project=issue-label-bot-dev)
* The public key is in gcs [gs://issue-label-bot-dev_secrets/label_bot.pub]
* The key is currently associated with the email jeremy@lewi.us so that the CLA check will pass.
* Key fingerprint

  ```
  Fingerprint: 2e:61:7c:19:28:28:4f:1a:2d:d0:33:ea:df:e2:41:08
  ```

The kustomize package [ssh-secret](./ssh-secret) can be used to create the K8s secrets from local files containing the 
keys. The keys should be stored outside of git because the shouldn't be checked into source control.