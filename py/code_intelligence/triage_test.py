from code_intelligence import triage
import json
import logging
import pytest

def build_info(missing_kind, missing_priority, missing_area, missing_project,
               project_card):
  info = triage.TriageInfo()
  info.missing_kind = missing_kind
  info.missing_area = missing_area
  info.missing_priority = missing_priority
  info.missing_project = missing_project
  info.triage_project_card = project_card
  return info

def test_triage_info():
  expected = [
    build_info(False, False, False, False, {"id": "12ab"}),
    build_info(True, True, True, True, None),
    build_info(True, True, True, True, None),
  ]

  actual = []

  with open("test_data/issues_for_triage.json") as hf:
    lines = hf.readlines()

    for i, l in enumerate(lines):
      issue = json.loads(l)

      a = triage.TriageInfo.from_issue(issue)
      actual.append(a)
  assert len(expected) == len(actual)

  for i in range(len(expected)):
    e = expected[i]
    a = actual[i]
    assert e == a

    if i == 0:
      assert not e.needs_triage
    else:
      assert e.needs_triage


if __name__ == "__main__":
  logging.basicConfig(
      level=logging.INFO,
      format=('%(levelname)s|%(asctime)s'
              '|%(pathname)s|%(lineno)d| %(message)s'),
      datefmt='%Y-%m-%dT%H:%M:%S',
  )
  logging.getLogger().setLevel(logging.INFO)

  pytest.main()