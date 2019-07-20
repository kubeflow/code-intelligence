import json
import logging
import notifications
import pytest

def test_process_issue_results():
  with open("test_data/issue-results-test-data.json") as hf:
    results = json.load(hf)

  issues = notifications.process_issue_results(results)
  assert len(issues) == 100
  assert "title" in issues[0]


if __name__ == "__main__":
  logging.basicConfig(
      level=logging.INFO,
      format=('%(levelname)s|%(asctime)s'
              '|%(pathname)s|%(lineno)d| %(message)s'),
      datefmt='%Y-%m-%dT%H:%M:%S',
  )
  logging.getLogger().setLevel(logging.INFO)
  pytest.main()