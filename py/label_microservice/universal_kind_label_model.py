
import tensorflow as tf
from tensorflow.keras import models as keras_models
from tensorflow.keras import utils as keras_utils

import dill as dpickle

from urllib.request import urlopen
from label_microservice import models

class UniversalKindLabelModel(models.IssueLabelModel):
  """UniversalKindLabelModel is a universal model that is trained across all repos.

  The model predicts the kind for an issue.
  """
  def __init__(self,  class_names=['bug', 'feature', 'question']):
    """Instantiate the model.

    Args:
      class_names: The specific label names to use for the three classes.
    """
    super(UniversalKindLabelModel, self).__init__()

    # TODO(jlewi): We should probably parameterize the models rather than
    # hardcoding it.
    title_pp_url = "https://storage.googleapis.com/codenet/issue_labels/issue_label_model_files/title_pp.dpkl"
    body_pp_url = 'https://storage.googleapis.com/codenet/issue_labels/issue_label_model_files/body_pp.dpkl'
    model_url = 'https://storage.googleapis.com/codenet/issue_labels/issue_label_model_files/Issue_Label_v1_best_model.hdf5'
    model_filename = 'downloaded_model.hdf5'

    with urlopen(title_pp_url) as f:
        self.title_pp = dpickle.load(f)

    with urlopen(body_pp_url) as f:
        self.body_pp = dpickle.load(f)

    model_path = keras_utils.get_file(fname=model_filename, origin=model_url)

    # TODO(jlewi): Is this right? Do we want to get the default graph or
    # create a new graph? What happens when we are loading multiple graphs
    # at once into memory.
    self._graph = tf.get_default_graph()
    self.model = keras_models.load_model(model_path)

    self.class_names = class_names

  def predict_issue_labels(self,  title:str, body:str):
    """
    Get probabilities for the each class.

    Parameters
    ----------
    title: str
        the issue title
    body: str
       the issue body

    Returns
    ------
    Dict[str:float]

    Example
    -------
    >>> issue_labeler = IssueLabeler(body_pp, title_pp, model)
    >>> issue_labeler.get_probabilities('hello world', 'hello world')
    {'bug': 0.08372017741203308,
     'feature': 0.6401631832122803,
     'question': 0.2761166989803314}
    """
    #transform raw text into array of ints
    vec_body = self.body_pp.transform([body])
    vec_title = self.title_pp.transform([title])

    # make predictions with the model
    with self._graph.as_default():
      probs = self.model.predict(x=[vec_body, vec_title]).tolist()[0]

    return {k:v for k,v in zip(self.class_names, probs)}
