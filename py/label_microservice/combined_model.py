"""A combined model combines multiple models."""

import itertools
import logging

from label_microservice import models

class CombinedLabelModels(models.IssueLabelModel):
  """Generate predictions with multiple models and then combine the results"""

  def __init__(self, models=None):
    # A list of models to generate predictions
    self._models = models

  def predict_issue_labels(self, title:str , text:str, context=None):
    """Return a dictionary of label probabilities.

    Args:
      title: The title for the issue
      text: The text for the issue

    Return
    ------
    dict: Dictionary of label to probability of that label for the
      the issue str -> float
    """
    if not self._models:
      raise ValueError("Can't generate predictions; no models loaded")

    predictions = {}
    for i, m in enumerate(self._models):
      logging.info(f"Generating predictions with model {i}")

      latest = m.predict_issue_labels(title, text, context=context)

      predictions = self._combine_predictions(predictions, latest)

    return predictions

  @staticmethod
  def _combine_predictions(left, right):
    """Combine two sets of predictions by taking the max probability."""
    results = {}
    results.update(left)

    for label, probability in right.items():
      if not label in results:
        results[label] = probability
        continue

      results[label] = max(left[label], right[label])

    return results
