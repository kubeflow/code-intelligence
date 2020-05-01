"""The models packages defines wrappers around different models."""
import abc
import typing

class IssueLabelModel:
  """A base class for all Issue label models.

  This class defines a common interface for all issue label models.
  """

  @abc.abstractmethod
  def predict_issue_labels(self, org:str, repo:str, title:str,
                           text:typing.List[str], context=None):
    """Return a dictionary of label probabilities.

    Args:
      org: The organization the issue belongs in
      repo: The repository.
      title: Issue title
      text: List of contents of the comments on the issue

      context: (Optional) Dictionary of additional context information

    Return
    ------
    dict: Dictionary of label to probability of that label for the
      the issue str -> float
    """
