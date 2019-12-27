import logging
import pytest

from code_intelligence import util

def test_parse_issue_spec():
  """A unittest for parsing issues. """

  test_cases = [
    {
      "issue": "kubeflow/tfjob#153",
      "expected": ("kubeflow", "tfjob", 153)
    },
    {
      "issue": "kubeflow/tfjob/tfjob",
      "expected": (None, None, None)
    }
  ]

  for c in test_cases:
    owner, repo, number = util.parse_issue_spec(c["issue"])
    assert owner == c["expected"][0]
    assert repo == c["expected"][1]
    assert number == c["expected"][2]

if __name__ == "__main__":
  logging.basicConfig(
      level=logging.INFO,
      format=('%(levelname)s|%(asctime)s'
              '|%(pathname)s|%(lineno)d| %(message)s'),
      datefmt='%Y-%m-%dT%H:%M:%S',
  )
  logging.getLogger().setLevel(logging.INFO)

  pytest.main()
