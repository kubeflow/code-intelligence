import logging
import json
import re

ISSUE_RE = re.compile("([^/]*)/([^#]*)#([0-9]*)")

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
