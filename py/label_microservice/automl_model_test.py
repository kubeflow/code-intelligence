"""Unittest for repo_specific_model. """
import logging
from unittest import mock
import pytest

from google.cloud.automl import types as automl_types
from label_microservice import automl_model
from label_microservice import test_util

def test_predict_labels():
  """A unittest for predict labels.

  This function mocks out AutoML.
  """
  mock_client = mock.MagicMock()
  payload = []

  predict_response = automl_types.PredictResponse()

  annotation = automl_types.AnnotationPayload()
  annotation.display_name = "area-jupyter"
  annotation.classification.score = 1
  predict_response.payload.append(annotation)

  annotation = automl_types.AnnotationPayload()
  annotation.display_name = "area-operator"
  annotation.classification.score = .4
  predict_response.payload.append(annotation)

  mock_client.predict.return_value = predict_response

  model = automl_model.AutoMLModel(model_name="some/model", prediction_client=mock_client)

  results = model.predict_issue_labels("kubeflow", "docs", "some title",
                                       ["some text"])

  expected = {
    # Use an integer and not float to avoid numeric issues in evalueation
    "area/jupyter": 1,
  }
  test_util.assert_dict_equal(expected, results)

if __name__ == "__main__":
  logging.basicConfig(
      level=logging.INFO,
      format=('%(levelname)s|%(asctime)s'
              '|%(pathname)s|%(lineno)d| %(message)s'),
      datefmt='%Y-%m-%dT%H:%M:%S',
  )
  logging.getLogger().setLevel(logging.INFO)

  pytest.main()


