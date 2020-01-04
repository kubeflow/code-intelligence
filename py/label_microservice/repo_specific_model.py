"""Define a repo specific model."""

import hashlib
import logging
import numpy as np
import os
import requests
import yaml

from code_intelligence import gcs_util
from label_microservice import mlp
from label_microservice import models
from label_microservice import repo_config

# The default endpoint for the microservice to compute embeddings
DEFAULT_EMBEDDING_API_ENDPOINT = "http://issue-embedding-server"

class RepoSpecificLabelModel(models.IssueLabelModel):
  """A repo specific model using a multi-layer perceptron."""

  def __init__(self):
    self.config = None
    self._mlp_predictor = None
    self._embedding_api_endpoint = DEFAULT_EMBEDDING_API_ENDPOINT

    # A list of labels. The order of the labels corresponds to the order
    # of the probabilities returned by the model
    self._label_names = None
    # Dictionary mapping label names to the probability thresholds.
    self._label_thresholds = None

  @classmethod
  def from_repo(cls, repo_owner, repo_name, embedding_api_endpoint=None):
    """Construct a model given the repo owner and name.

    Load config from the YAML of the specific repo_owner/repo_name.

    Args:
      repo_owner: str
      repo_name: str
      embedding_api_endpoint: The endpoint for the microservice to compute
        embeddings
    """

    model = RepoSpecificLabelModel()

    model._embedding_api_endpoint = embedding_api_endpoint

    model.config = repo_config.RepoConfig(repo_owner=repo_owner,
                                          repo_name=repo_name)

    # download model
    gcs_util.download_file_from_gcs(model.config.model_bucket_name,
                                    model.config.model_gcs_path,
                                    model.config.model_local_path)

    # download label columns
    gcs_util.download_file_from_gcs(model.config.model_bucket_name,
                                    model.config.labels_gcs_path,
                                    model.config.labels_local_path)

    model._mlp_predictor = mlp.MLPWrapper(
      clf=None, model_file=model.config.model_local_path, load_from_model=True)

    # Get label info.
    # Expect a YAML file with a dictionary
    # {'labels': list, 'probability_thresholds': {label_index: threshold}}
    with open(model.config.labels_local_path, 'r') as f:
      label_columns = yaml.safe_load(f)

    model._label_names = label_columns["labels"]
    model._label_thresholds = {}

    for index, threshold in label_columns["probability_thresholds"].items():
      model._label_thresholds[model._label_names[index]] = threshold

    logging.info(f"Loaded model gs://{model.config.model_bucket_name}/"
                 f"{model.config.model_gcs_path}")
    logging.info(f"Loaded model config gs://{model.config.model_bucket_name}/"
                 f"{model.config.labels_gcs_path}")
    logging.info(f"Model label thresholds {model._label_thresholds}",
                 extra={"thresholds": model._label_thresholds})
    if not embedding_api_endpoint:
      embedding_api_endpoint = DEFAULT_EMBEDDING_API_ENDPOINT

    model._embedding_api_endpoint = embedding_api_endpoint
    logging.info(f"Issue embedding service set to {model._embedding_api_endpoint}")
    return model

  def predict_issue_labels(self, title:str , text:str, context=None):
    """Return a dictionary of label probabilities.

    Args:
      title: The title for the issue
      text: The text for the issue
      context: (Optional) dictionary of information like the issue. Used
        for logging
    Return
    ------
    dict: Dictionary of label to probability of that label for the
      the issue str -> float
    """
    issue_embedding = self._get_issue_embedding(title, text)

    if not context:
      context = {}

    # if not retrieve the embedding, ignore to predict it
    if issue_embedding is None:
      logging.error("No embeddings returned for issue", extra=context)
      return {}

    # Predict probabilities expects a list of lists; i.e a 2-d matrix where
    # each column is a different input vector. The output is an array
    # with shape (n_samples, n_clasess) (for more info see
    # https://scikit-learn.org/stable/modules/generated/sklearn.neural_network.MLPClassifier.html#sklearn.neural_network.MLPClassifier.predict_proba)
    # We take the first row of this matrix because we only have 1 sample.
    # Note: result[0] is essentially equivalent to result[0, :]
    label_probabilities = self._mlp_predictor.predict_probabilities(
      [issue_embedding])[0]

    # check thresholds to get labels that need to be predicted
    # TODO(kubeflow/code-intelligence/issues/83): We should store the labels
    # in the MLPClassifier to decrease the risk that they get out of sync
    # with the probabilities.
    predictions = dict(zip(self._label_names, label_probabilities))

    # TODO(https://github.com/kubeflow/code-intelligence/issues/79):
    # We should use some sort of context to pass along information
    # about the issue so we can log what issue these predictions pertain
    # to.
    extra = {}
    extra.update(context)
    extra["predictions"] = predictions
    logging.info(f"Unfiltered predictions: {predictions}", extra=extra)

    labels_to_remove = []
    for label, probability in predictions.items():
      # if the threshold of any label is None, just ignore it
      # because the label does not meet both of precision & recall thresholds
      if not self._label_thresholds[label]:
        labels_to_remove.append(label)
        continue

      if probability < self._label_thresholds[label]:
        labels_to_remove.append(label)

    for l in labels_to_remove:
      del predictions[l]
    logging.info(f"Labels below precision and recall {labels_to_remove}",
                 extra=context)
    return predictions

  def _get_issue_embedding(self, title, text):
    """Get the embedding of the issue by calling GitHub Issue
    Embeddings API endpoint.

    Args:
      title: The title for the issue
      text: The text for the issue

    Return
    ------
    numpy.ndarray
        shape: (1600,)
    """
    data = {'title': title, 'body': text}

    # sending post request and saving response as response object
    url = self._embedding_api_endpoint + "/text"
    r = requests.post(url=url, json=data)
    if r.status_code != 200:
      logging.warning(f'Status code is {r.status_code} not 200: '
                            'can not retrieve the embedding')
      return None

    # For debugging print out hash of the content embeddings. This is to
    # see if they are changing
    m = hashlib.md5()
    m.update(r.content)
    logging.info(f"hash of embeddings {m.hexdigest()}")
    embeddings = np.frombuffer(r.content, dtype='<f4')[:1600]
    return embeddings
