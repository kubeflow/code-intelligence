# Logging and Monitoring


## Stackdriver logs

* Label bot workers use structured json logs
* You can search the logs in stackdrive some examples below
* There is also a BigQuery sink for the stackdriver logs to facilitate analysis and querying


Use a label like the following to see messages for
a specific issue

```
jsonPayload.repo_owner = "kubeflow"
jsonPayload.repo_name = "code-intelligence"
jsonPayload.issue_num = "132"
resource.labels.namespace_name = "label-bot-prod"
```