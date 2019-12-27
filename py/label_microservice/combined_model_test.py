"""Unittest for repo_specific_model. """
import logging
from unittest import mock
import pytest

from label_microservice import combined_model
from label_microservice import test_util

def test_combine_predictions():
  """A unittest for combine predictions.
  """
  left = {
    "a": .1,
    "b": .9,
    "c": .5,
  }

  right = {
    "a": .9,
    "b": .1,
    "d": .6
  }

  actual = combined_model.CombinedLabelModels._combine_predictions(left, right)

  expected = {
    "a": .9,
    "b": .9,
    "c": .5,
    "d": .6,
  }
  test_util.assert_dict_equal(expected, actual)

if __name__ == "__main__":
  logging.basicConfig(
      level=logging.INFO,
      format=('%(levelname)s|%(asctime)s'
              '|%(pathname)s|%(lineno)d| %(message)s'),
      datefmt='%Y-%m-%dT%H:%M:%S',
  )
  logging.getLogger().setLevel(logging.INFO)

  pytest.main()
