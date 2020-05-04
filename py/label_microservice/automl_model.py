"""Use a model trained on automl.
"""
import hashlib
import logging
import numpy as np
import os
import requests
import retrying
import typing
import yaml

from code_intelligence import github_util
from google.cloud import automl
from label_microservice import models

# TODO(jlewi): Do we want to hardcode this?
CONFIDENCE_THRESHOLD = .5

class AutoMLModel(models.IssueLabelModel):
  """Use a model training with GCP AutoML."""

  def __init__(self, model_name = None, prediction_client=None):
    self.config = None
    # The model name
    # e.g. a value like value like
    # "projects/976279526634/locations/us-central1/models/TCN654213816573231104'"
    self.model_name = model_name

    if not prediction_client:
      prediction_client = automl.PredictionServiceClient()

    self._prediction_client = prediction_client

  def predict_issue_labels(self, org:str, repo:str, title:str,
                           text:typing.List[str], context=None):
    """Return a dictionary of label probabilities.

    Args:
      org: The organization the issue belongs in
      repo: The repository.
      title: Issue title
      text: List of contents of the comments on the issue

      context: (Optional) dictionary of information like the issue. Used
        for logging
    Return
    ------
    dict: Dictionary of label to probability of that label for the
      the issue str -> float
    """
    if not context:
      context = {}

    content = github_util.build_issue_doc(org, repo, title, text)
    text_snippet = automl.types.TextSnippet(content=content)
    payload = automl.types.ExamplePayload(text_snippet=text_snippet)

    # TODO(jlewi): Retry longer? Distinguish permanent vs. retryable errors
    #@retrying.retry(stop_max_delay=60*1000)
    def _predict():
      response = self._prediction_client.predict(self.model_name, payload)
      return response

    response = _predict()

    predictions = {}

    for annotation_payload in response.payload:
      # TODO(jlewi): Can we do this in a more principled way?
      # AutoML doesn't allow "/" in the label names so during training
      # we convert them from "/" to "-". So here we need to convert them
      # back to "/"
      # Only replace the first occurence of the "-". In principle I think
      # we might have sub areas as well and we should fix this.
      label = annotation_payload.display_name.replace("-", "/", 1)
      predictions[label] = annotation_payload.classification.score

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
      if probability < CONFIDENCE_THRESHOLD:
        labels_to_remove.append(label)

    for l in labels_to_remove:
      del predictions[l]
    logging.info(f"Labels below AutoML threshold {labels_to_remove}",
                 extra=context)
    return predictions
