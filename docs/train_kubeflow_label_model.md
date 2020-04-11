# Training a Label Bot Model For Kubeflow

These are instructions/pointers for how to train and deploy a Kubeflow specific
model trained on all Kubeflow repositories.

A lot of relevant information is in various issues:

* [kubeflow/code-intelligence#110](https://github.com/kubeflow/code-intelligence/issues/110) Train an org wide model
* [kubeflow/code-intelligence#70](https://github.com/kubeflow/code-intelligence/issues/70) Ensemble model combining repo specific models
  and global model
  

These notes are in complete as training and deploying an org wide model is still a work in progress; see [kubeflow/code-intelligence#110](https://github.com/kubeflow/code-intelligence/issues/110)

## Build Training set and compute embeddings

* Use the notebook [../Issue_Embeddings/notebooks/Get-GitHub-Issues.ipynb](../Issue_Embeddings/notebooks/Get-GitHub-Issues.ipynb) to

  * Fetch all issues for kubeflow from BigQuery
  * Compute embeddings for all Kubeflow issues
  * Save the data to an HDF5 file on GCS