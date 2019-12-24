"""A combined model combines multiple models."""

from label_microservice import models

class CombinedLabelModels(models.IssueLabelModel):
  """Generate predictions with multiple models and then combine the results"""

  def __init__(self, models=None):
    # A list of models to generate predictions
    self._models = models


  def predict_issue_labels(self, title:str , text:str):
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

    for i, m in enumerate(self._models):

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

