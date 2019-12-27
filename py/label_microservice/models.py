"""The models packages defines wrappers around different models."""
import abc

class IssueLabelModel:
  """A base class for all Issue label models.

  This class defines a common interface for all issue label models.
  """

  @abc.abstractmethod
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
