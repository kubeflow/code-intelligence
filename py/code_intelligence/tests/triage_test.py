from code_intelligence import triage
from dateutil import parser as dateutil_parser
import json
import logging
import pytest

def build_info(kind_time, priority_time, area_time, project_time,
               project_card, state, requires_project):
  info = triage.TriageInfo()
  if kind_time:
    info.kind_time = dateutil_parser.parse(kind_time)
  if priority_time:
    info.priority_time = dateutil_parser.parse(priority_time)
  if area_time:
    info.area_time = dateutil_parser.parse(area_time)
  if project_time:
    info.project_time = dateutil_parser.parse(project_time)
  info.triage_project_card = project_card
  info.issue = {
    "state": state,
  }
  info.requires_project = requires_project
  return info

def test_triage_info():

  expected = [
    build_info("2019-07-16T15:01:43+00:00", "2019-07-15T15:01:43+00:00",
               "2019-08-16T15:01:43Z", "2019-07-15T15:05:31+00:00", None,
               "OPEN", True),
    build_info(None, None, None, None, None, "OPEN", False),
  ]

  expected_triaged_at = [
    dateutil_parser.parse("2019-08-16T15:01:43Z"),
    None
  ]

  actual = []

  with open("test_data/issues_for_triage.json") as hf:
    issues = json.load(hf)

  for issue in issues:
    a = triage.TriageInfo.from_issue(issue)
    a.needs_triage
    actual.append(a)
  assert len(expected) == len(actual)

  for i in range(len(expected)):
    e = expected[i]
    a = actual[i]
    assert e == a

    e_triaged_at = expected_triaged_at[i]

    if not e_triaged_at:
      assert a.needs_triage
    else:
      assert a.triaged_at == e.triaged_at


if __name__ == "__main__":
  logging.basicConfig(
      level=logging.INFO,
      format=('%(levelname)s|%(asctime)s'
              '|%(pathname)s|%(lineno)d| %(message)s'),
      datefmt='%Y-%m-%dT%H:%M:%S',
  )
  logging.getLogger().setLevel(logging.INFO)

  # Do not submit
  test_triage_info()
  # pytest.main()