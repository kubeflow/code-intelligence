"""This module contains code to get issue data from BigQuery."""

import dateutil 
import json
from pandas.io import gbq
import re

def get_issues(login, project, max_age_days=None):
  """Get issue data from bigquery.
  
  Args:
    login: Which GitHub organization to query for
    project: GCP project to charge BigQuery to
    max_age_days: (Optional) If present only fetch issues which were created
      less then max age_days ago
  """
  query = f"""SELECT          
        JSON_EXTRACT(payload, '$.issue.html_url') as html_url,
        JSON_EXTRACT(payload, '$.issue.title') as title,
        JSON_EXTRACT(payload, '$.issue.body') as body,
        JSON_EXTRACT(payload, "$.issue.labels") as labels,
        JSON_EXTRACT(payload, "$.issue.created_at") as created_at,
        JSON_EXTRACT(payload, "$.issue.updated_at") as updated_at,
        org.login,
        type,
    FROM `githubarchive.month.20*`
    WHERE  (type="IssuesEvent" or type="IssueCommentEvent") and org.login = '{login}'"""
  
  if max_age_days:
    # We need to convert the created_at field to a timestamp.
    # JSON_EXTRACT returns a json string meaning it is quoted and we need 
    # to remove the quotes
    query += f""" and DATETIME_DIFF(CURRENT_DATETIME(), PARSE_DATETIME(
                          "\\"%Y-%m-%dT%TZ\\"", JSON_EXTRACT(payload, 
                                                           "$.issue.created_at")), DAY) 
                   <= {max_age_days} """

  issues_and_pulls=gbq.read_gbq(query, dialect='standard', project_id=project)
  
  # pull request comments also get included so we need to filter those out
  pattern = re.compile(".*issues/[\d]+")
  
  issues_index = issues_and_pulls["html_url"].apply(lambda x: pattern.match(x) is not None)
  issues = issues_and_pulls[issues_index]

  # We need to group the events by issue and then select the most recent event for each 
  # issue as that should have the most up to date labels for each issue.
  # TODO(jlewi): Should we be converting updated_at to a datetime before doing the sort?
  latest_issues = issues.groupby("html_url", as_index=False).apply(lambda x: x.sort_values(["updated_at"]).iloc[-1])
  
  # we need to deserialize the json strings to remove escaping
  for f in ["html_url", "title", "body", "created_at", "updated_at"]:
    latest_issues[f] = latest_issues[f].apply(lambda x : json.loads(x))
  
  # Parse timestamps
  for f in ["created_at", "updated_at"]:
    latest_issues[f] = latest_issues[f].apply(lambda x : dateutil.parser.parse(x))
  
  # Parse labels
  def get_labels(x):
    d = json.loads(x)
    return [i["name"] for i in d]

  latest_issues["parsed_labels"] = latest_issues["labels"].apply(get_labels)
  
  return latest_issues