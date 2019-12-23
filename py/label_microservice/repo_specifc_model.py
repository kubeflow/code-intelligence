"""Define a repo specific model."""

import logging
import numpy as np
import requests
import yaml

from code_intelligence import gcs_util
from passlib.apps import custom_app_context as pwd_context
from label_microservice import mlp
from label_microservice import models
from label_microservice import repo_config

# The default endpoint for the microservice to compute embeddings
#
# TODO(chunhsiang): change the embedding microservice to be an internal DNS of k8s service.
#   see: https://v1-12.docs.kubernetes.io/docs/concepts/services-networking/dns-pod-service/#services
DEFAULT_EMBEDDING_API_ENDPOINT = "https://embeddings.gh-issue-labeler.com/text"

class RepoSpecificLabelModel(models.IssueLabelModel):
  """A repo specific model using a multi-layer perceptron."""

  def __init__(self):
    self.config = None
    self._mlp_predictor = None
    self._embedding_api_endpoint = None
    self._embedding_api_key = None

    self._label_columns = None
    self._label_names = None
    self._label_thresholds = None

  @classmethod
  def from_repo(cls, repo_owner, repo_name,
                embedding_api_endpoint=DEFAULT_EMBEDDING_API_ENDPOINT):
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
    model._embedding_api_key = os.environ['GH_ISSUE_API_KEY']

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
      model._label_columns = yaml.safe_load(f)

    model._label_names = model._label_columns['labels']
    model._label_thresholds = model._label_columns['probability_thresholds']

    return model

  def predict_issue_labels(self, title:str , text:str ):
    """Return a dictionary of label probabilities.

    Args:
      title: The title for the issue
      text: The text for the issue

    Return
    ------
    dict: Dictionary of label to probability of that label for the
      the issue str -> float
    """
    issue_embedding = self._get_issue_embedding(title, text)

    # if not retrieve the embedding, ignore to predict it
    if issue_embedding is None:
      return [], None

    # change embedding from 1d to 2d for prediction and extract the result
    label_probabilities = self._mlp_predictor.predict_probabilities(
      [issue_embedding])[0]

    # check thresholds to get labels that need to be predicted
    predictions = {}
    for i in range(len(label_probabilities)):
      # if the threshold of any label is None, just ignore it
      # because the label does not meet both of precision & recall thresholds
      if self._label_thresholds[i] and label_probabilities[i] >= self._label_thresholds[i]:
        predictions[self._label_names[i]] = label_probabilities[i]
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
    r = requests.post(url=self._embedding_api_endpoint,
                          headers={'Token': pwd_context.hash(
                            self._embedding_api_key)},
                          json=data)
    if r.status_code != 200:
      logging.warning(f'Status code is {r.status_code} not 200: '
                            'can not retrieve the embedding')
      return None

    embeddings = np.frombuffer(r.content, dtype='<f4')[:1600]
    return embeddings
