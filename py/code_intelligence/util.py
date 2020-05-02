import datetime
import logging
import json
import pytz
import re

import json_log_formatter


ISSUE_RE = re.compile("([^/]*)/([^#]*)#([0-9]*)")
ISSUE_URL_RE = re.compile("https://github.com/([^/]*)/([^#]*)/issues/([0-9]*)")

# TODO(jlewi): Might be better to just write it
# as a json list
def write_items_to_json(output_file, results):
  with open(output_file, "w") as hf:
    for i in results:
      json.dump(i, hf)
      hf.write("\n")
  logging.info("Wrote %s items to %s", len(results), output_file)

def parse_issue_spec(issue):
  """Parse an issue in the form {owner}/{repo}#{number}

  Args:
    isue: An issue in the form {owner}/{repo}#{number}

  Returns:
    owner, repo, number
  """
  m = ISSUE_RE.match(issue)
  if not m:
    return None, None, None
  return m.group(1), m.group(2), int(m.group(3))

# TODO(jlewi): Unittest
def parse_issue_url(issue):
  """Parse an issue in the form https://github.com/{owner}/{repo}/issues/{number}
  Args:
    issue: An issue in the form {owner}/{repo}#{number}
  Returns:
    owner, repo, number
  """
  m = ISSUE_URL_RE.match(issue)
  if not m:
    return None, None, None
  return m.group(1), m.group(2), int(m.group(3))

# TODO(jlewi): Unittest
def build_issue_url(org, repo, number):
  """Return a url in the form https://github.com/{owner}/{repo}/issues/{number}

  Args:
    org: The organization that owns the issue
    repo: The repo that owns the issue
    number: The issue number

  Returns:
    owner, repo, number
  """
  return f"https://github.com/{org}/{repo}/issues/{number}"

pacific = pytz.timezone("US/Pacific")

def now():
  """Return the current time with timezone information."""
  # see https://julien.danjou.info/python-and-timezones/
  # Need to attach a time zone
  return datetime.datetime.now(tz=pacific)

class CustomisedJSONFormatter(json_log_formatter.JSONFormatter):
  """A custom formatter to produce logs in json format."""
  def json_record(self, message, extra, record):
    extra['message'] = message

    extra["filename"] = record.pathname
    extra["line"] = record.lineno
    extra["level"] = record.levelname
    if "time" not in extra:
      extra["time"] = now().isoformat()
    extra["thread"] = record.thread
    extra["thread_name"] = record.threadName
    return extra
