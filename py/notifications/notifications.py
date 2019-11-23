from code_intelligence import graphql
import fire
import github3
import json
import logging
import os
import numpy as np
import pprint
import retrying
import json

TOKEN_NAME = "INPUT_PERSONAL_ACCESS_TOKEN"
PULL_REQUEST_TYPE = "PullRequest"

# TODO(jlewi): Rewrite this code to use:
#  i) graphql.unpack_and_split_nodes
#  ii) graphql.shard_writer
def process_notification(n):
  # Mark as read anything that isn't an explicit mention.
  # For PRs there doesn't seem like a simple way to detect if the notice
  # is because the state changed
  #
  # We exclude mentions on PR because that gets overwhelmed by "/assign"
  # statements. We should potentially be more discerning and not mark the
  # notification as read for PRs which aren't assigned to the user.
  if n.reason == "mention":
    if n.subject.get("type") != "PullRequest":
      return

  title = n.subject.get("title")
  logging.info("Marking as read: type: %s reason: %s title: %s",
               n.subject.get("type"), n.reason, title)
  n.mark()


def process_issue_results(data):
  """Process the data returned by the issues GraphQL request.

  Args:
    data: The data returned

  Returns:
    issues: A list of dicts; each dict is the data for some of
    the results
  """
  edges = data.get("data").get("repository").get("issues").get("edges")

  issues = []
  for e in edges:
    issues.append(e["node"])

  return issues

class NotificationManager(object):
  def mark_read(self, user):
    token = os.getenv(TOKEN_NAME)
    if not token:
      raise ValueError(("Environment variable {0} needs to be set to a GitHub "
                        "token.").format(token))
    client = github3.GitHub(username=user, token=token)
    notifications = client.notifications()

    # https://developer.github.com/v3/activity/notifications/
    #
    # How do we identify closed pull requests?
    for n in notifications:
      process_notification(n)

  def write_notifications(self, user, output):
    """Write all notifications to a file.

    Args:
      user: Name of the user to get notifications for
      output: The file to write notifications to.

    Fetches all notifications, including ones marked read,
    and writes them to the supplied file.
    """
    token = os.getenv(TOKEN_NAME)
    if not token:
      raise ValueError(("Environment variable {0} needs to be set to a GitHub "
                        "token.").format(token))
    client = github3.GitHub(username=user, token=token)
    notifications = client.notifications(all=True)

    # https://developer.github.com/v3/activity/notifications/
    #
    # How do we identify closed pull requests?
    i = 0
    with open(output, mode="w") as hf:
      for n in notifications:
        i += 1
        hf.write(n.as_json())
        hf.write("\n")

    logging.info("Wrote %s notifications to %s", i, output)

  def fetch_issues(self, org, repo, output):
    """Fetch issues for a repository

    Args:
      org: The org that owns the repository
      repo: The directory for the repository
      output: The directory to write the results

    Writes the issues along with the first comments to a file in output
    directory.
    """
    client = graphql.GraphQLClient()

    num_issues_per_page = 100
    query_template = """{{
repository(owner: "{org}", name: "{repo}") {{
  issues(first:{num_issues_per_page} {issues_cursor}) {{
    totalCount
    pageInfo {{
      endCursor
      hasNextPage
    }}
    edges{{
      node {{
        author {{
          __typename
                ... on User {{
                  login
                }}

                ... on Bot{{
                  login
                }}
        }}
        title
        body
        comments(first:20, ){{
          totalCount
          edges {{
            node {{
              author {{
          __typename
                ... on User {{
                  login
                }}

                ... on Bot{{
                  login
                }}
        			}}
              body
              createdAt
            }}
          }}
        }}
      }}
    }}
  }}
}}
}}
"""


    shard = 0
    num_pages = None
    if not os.path.exists(output):
      os.makedirs(output)

    total_issues = None
    has_next_issues_page = True
    # TODO(jlewi): We should persist the cursors to disk so we can resume
    # after errors
    issues_cursor = None
    while has_next_issues_page:
      issues_cursor_text = ""
      if issues_cursor:
        issues_cursor_text = "after:\"{0}\"".format(issues_cursor)
      query = query_template.format(org=org, repo=repo,
                                    num_issues_per_page=num_issues_per_page,
                                    issues_cursor=issues_cursor_text)
      results = client.run_query(query)

      if results.get("errors"):
        logging.error("There was a problem issuing the query; errors:\n%s",
                      "\n".join(results.get("errors")))
        return

      if not total_issues:
        total_issues = results["data"]["repository"]["issues"]["totalCount"]
        num_pages = int(np.ceil(total_issues/float(num_issues_per_page)))
        logging.info("%s/%s has a total of %s issues", org, repo, total_issues)

      shard_file = os.path.join(
        output, "issues-{0}-{1}-{2:03d}-of-{3:03d}.json".format(org, repo, shard,
        num_pages))

      issues = process_issue_results(results)
      with open(shard_file, "w") as hf:
        for i in issues:
          json.dump(i, hf)
          hf.write("\n")
        logging.info("Wrote shard %s to %s", shard, shard_file)
      shard += 1

      page_info = results["data"]["repository"]["issues"]["pageInfo"]
      issues_cursor = page_info["endCursor"]
      has_next_issues_page = page_info["hasNextPage"]

  def _create_client(self, user):
    token = os.getenv(TOKEN_NAME)
    if not token:
      raise ValueError(("Environment variable {0} needs to be set to a GitHub "
                        "token.").format(token))
    client = github3.GitHub(username=user, token=token)

    return client

if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO,
                    format=('%(levelname)s|%(asctime)s'
                            '|%(message)s|%(pathname)s|%(lineno)d|'),
                    datefmt='%Y-%m-%dT%H:%M:%S',
                    )

  fire.Fire(NotificationManager)
