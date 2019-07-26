"""Identify issues that need triage."""
from code_intelligence import graphql
from code_intelligence import util
import fire
import github3
import json
import logging
import os
import numpy as np
import pprint
import retrying
import json

TOKEN_NAME = "GITHUB_TOKEN"

# TODO(jlewi): If we make this an app maybe we should read this from a .github
#file
ALLOWED_KINDS = ["improvement/enhancement", "community/question", "kind/bug"]
ALLOWED_PRIORITY = ["priority/p0", "priority/p1", "priority/p2",
                    "priority/p3"]

REQUIRES_PROJECT = ["priority/p0", "priority/p1"]

TRIAGE_PROJECT = "Needs Triage"

# TODO(jlewi): Project card is currently hard coded
# The notebook triage.ipynb contains a snippet to get the project card id
PROJECT_CARD_ID = "MDEzOlByb2plY3RDb2x1bW41OTM0MzEz"

class TriageInfo(object):
  """Class describing whether an issue needs triage"""
  def __init__(self):
    self.issue = None
    # Booleans indicating why triage might fail
    self.missing_kind = True
    self.missing_priority = True
    self.missing_project = True
    self.missing_area = True

    self.triage_project_card = None

  @classmethod
  def from_issue(cls, issue):
    """Construct TriageInfo from the supplied issue"""
    info = TriageInfo()
    info.issue = issue
    labels = graphql.unpack_and_split_nodes(issue, ["labels", "edges"])

    project_cards = graphql.unpack_and_split_nodes(issue,
                                                   ["projectCards", "edges"])


    for l in labels:
      name = l["name"]

      if name in ALLOWED_KINDS:
        info.missing_kind = False

      if name in ALLOWED_PRIORITY:
        info.missing_priority = False

        if not name in REQUIRES_PROJECT:
          info.missing_project = False
        else:
          if project_cards:
            info.missing_project = False

      if name.startswith("area") or name.startswith("community"):
        info.missing_area= False

    for c in project_cards:
      if c.get("project").get("name") == TRIAGE_PROJECT:
        info.triage_project_card = c
        break

    return info

  def __eq__(self, other):
    if self.missing_kind != other.missing_kind:
      return False

    if self.missing_priority != other.missing_priority:
      return False

    if self.missing_project != other.missing_project:
      return False

    if self.missing_area != other.missing_area:
      return False

    if self.in_triage_project != other.in_triage_project:
      return False

    if self.in_triage_project:
      if self.triage_project_card["id"] != other.triage_project_card["id"]:
        return False
    return True

  @property
  def needs_triage(self):
    """Return true if the issue needs triage"""
    needs = False

    # closed issues don't need triage
    if self.issue["state"].lower() == "closed":
      return False

    if self.missing_kind:
      needs = True

    if self.missing_priority:
      needs = True

    if self.missing_project:
      needs = True

    if self.missing_area:
      needs = True

    return needs

  def __repr__(self):
    pieces = ["needs_triage={0}".format(self.needs_triage)]

    if self.needs_triage:
      for f in ["missing_kind", "missing_area", "missing_priority",
                "missing_project"]:
        v = getattr(self, f)
        pieces.append("{0}={1}".format(f, v))

    return ";".join(pieces)

  def message(self):
    """Return a human readable message."""
    if not self.needs_triage:
      return "Issue doesn't need attention."

    lines = []
    if self.needs_triage:
      lines.append("Issue needs triage:")

    if self.missing_kind:
      lines.append("\t Issue needs one of the labels {0}".format(ALLOWED_KINDS))

    if self.missing_priority:
      lines.append("\t Issue needs one of the priorities {0}".format(ALLOWED_PRIORITY))

    if self.missing_area:
      lines.append("\t Issue needs an area label")

    if self.missing_project:
      lines.append("\t Issues with priority in {0} need to be assigned to a project".format(REQUIRES_PROJECT))

    return "\n".join(lines)

  @property
  def in_triage_project(self):
    return self.triage_project_card is not None

class IssueTriage(object):
  def __init__(self):
    self._client = None

  @property
  def client(self):
    if not self._client:
      self._client = graphql.GraphQLClient()

    return self._client

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


  def _iter_issues(self, org, repo, output=None):
    """Iterate over issues in batches for a repository

    Args:
      org: The org that owns the repository
      repo: The directory for the repository
      output: The directory to write the results; if not specified results
        are not downloaded

    Writes the issues along with the first comments to a file in output
    directory.
    """
    client = graphql.GraphQLClient()

    num_issues_per_page = 100

    # TODO(jlewi):Use query variables
    # TODO(jlewi):
    query_template = """{{
repository(owner: "{org}", name: "{repo}") {{
  issues(first:{num_issues_per_page}, states: OPEN, {issues_cursor}) {{
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
        id
        title
        body
        url
        state
        labels(first:30, ){{
          totalCount
          edges {{
            node {{
              name
            }}
          }}
        }}
        projectCards(first:30, ){{
          totalCount
          edges {{
            node {{
              id
              project {{
                name
                number
              }}
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
    if output and not os.path.exists(output):
      os.makedirs(output)

    total_issues = None
    has_next_issues_page = True
    # TODO(jlewi): We should persist the cursors to disk so we can resume
    # after errors
    issues_cursor = None
    shard_writer = None
    while has_next_issues_page:
      issues_cursor_text = ""
      if issues_cursor:
        issues_cursor_text = "after:\"{0}\"".format(issues_cursor)
      query = query_template.format(org=org, repo=repo,
                                    num_issues_per_page=num_issues_per_page,
                                    issues_cursor=issues_cursor_text)
      results = client.run_query(query)

      if results.get("errors"):
        message = json.dumps(results.get("errors"))
        logging.error("There was a problem issuing the query; errors:\n%s",
                      "\n", message)
        return

      if not total_issues:
        total_issues = results["data"]["repository"]["issues"]["totalCount"]
        num_pages = int(np.ceil(total_issues/float(num_issues_per_page)))
        logging.info("%s/%s has a total of %s issues", org, repo, total_issues)

      if output and not shard_writer:
        logging.info("initializing the shard writer")
        shard_writer = graphql.ShardWriter(num_pages, output,
                                           prefix="issues-{0}-{1}".format(org, repo))

      issues = graphql.unpack_and_split_nodes(
        results, ["data", "repository", "issues", "edges"])

      yield issues

      if shard_writer:
        shard_writer.write_shard(issues)

      page_info = results["data"]["repository"]["issues"]["pageInfo"]
      issues_cursor = page_info["endCursor"]
      has_next_issues_page = page_info["hasNextPage"]

  def _issue_needs_triage(self, issue):
    """Check if the supplied issue needs triage.

    Args:
      issue: json dictionary describing the issue

    Returns:
      triage_info: Instance of TriageInfo explaining whether the issue needs
        triage
    """

  def triage(self, repo, output=None):
    """Triage issues in the specified repository.

    Args:
      repo: Repository in the form {org}/{repo}
      output: (Optional) directory to write issues
    """
    org, repo_name = repo.split("/")

    for shard_index, shard in enumerate(self._iter_issues(org, repo_name, output=output)):
      logging.info("Processing shard %s", shard_index)
      for i in shard:
        self._process_issue(i)

  def triage_issue(self, url, project=None, add_comment=False):
    """Triage a single issue.

    Args:
      url: The url of the issue e.g.
        https://github.com/kubeflow/community/issues/280

      project: (Optional) If supplied the URL of the project to add issues
        needing triage to.

      add_comment: Set to true to comment on the issue with why
        the issue needs triage
    """

    query = """query getIssue($url: URI!) {
  resource(url: $url) {
    __typename
    ... on Issue {
      author {
        __typename
        ... on User {
          login
        }
        ... on Bot {
          login
        }
      }
      id
      title
      body
      url
      state
      labels(first: 30) {
        totalCount
        edges {
          node {
            name
          }
        }
      }
      projectCards(first:30, ){
        totalCount
        edges {
          node {
            id
            project {
              name
              number
            }
          }
        }
      }
    }
  }
}"""

    variables = {
      "url": url
    }
    results = self.client.run_query(query, variables=variables)

    if results.get("errors"):
      message = json.dumps(results.get("errors"))
      logging.error("There was a problem issuing the query; errors:\n%s",
                        "\n".join(message))
      return

    issue = results["data"]["resource"]
    self._process_issue(issue)

  def _process_issue(self, issue, add_comment=False):
    """Process a single issue.

    Args:
      issue: Issue to process.
    """
    info = TriageInfo.from_issue(issue)
    logging.info("Issue %s:\nstate:%s\n", info.issue["url"], info.message())

    if not info.needs_triage:
      self._remove_triage_project(info)
      return

    # TODO(jlewi): We should check if there is already a triage message
    if add_comment:
      mutation = """
  mutation AddIssueComment($input: AddCommentInput!){
    addComment(input:$input){
      subject {
        id
      }
    }
  }
  """
      mutation_variables = {
        "input": {
          "subjectId": issue["id"],
          "body": info.message(),
        }
      }

      results = client.run_query(mutation, variables=mutation_variables)

      if results.get("errors"):
        message = json.dumps(results.get("errors"))
        logging.error("There was a problem commenting on the issue; errors:\n%s",
                          "\n".join(message))
        return

    # add project
    self._add_triage_project(info)

  def _remove_triage_project(self, issue_info):
    """Remove the issue from the triage project.

    Args:
      issue_info: TriageInfo
    """
    if not issue_info.in_triage_project:
      return

    add_card = """
mutation DeleteFromTriageProject($input: DeleteProjectCardInput!){
  deleteProjectCard(input:$input) {
     clientMutationId
  }
}
"""
    variables = {
      "input": {
        "cardId": issue_info.triage_project_card["id"],
      }
    }

    logging.info("Issue %s remove from triage project", issue_info.issue["url"])
    results = self.client.run_query(add_card, variables=variables)

    if results.get("errors"):
      message = json.dumps(results.get("errors"))
      logging.error("There was a problem removing the issue from the triage project; "
                    "errors:\n%s\n", join(message))
      return

  def _add_triage_project(self, issue_info):
    """Add the issue to the triage project if needed

    Args:
      issue_info: IssueInfo
    """

    if issue_info.in_triage_project:
      logging.info("Issue %s already in triage project",
                   issue_info.issue["url"])
      return

    add_card = """
mutation AddProjectIssueCard($input: AddProjectCardInput!){
  addProjectCard(input:$input) {
     clientMutationId
  }
}
"""
    add_variables = {
      "input": {
        "contentId": issue_info.issue["id"],
        "projectColumnId": PROJECT_CARD_ID,
      }
    }

    results = self.client.run_query(add_card, variables=add_variables)

    if results.get("errors"):
      # Check if the error was because the issue was already added
      ALREADY_ADDED = "Project already has the associated issue"
      if not (len(results["errors"]) == 1 and
              results["errors"][0]["message"] == ALREADY_ADDED):
        message = json.dumps(results.get("errors"))
        logging.error("There was a problem adding the issue to the project; "
                      "errors:\n%s\n", join(message))
        return

if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO,
                      format=('%(levelname)s|%(asctime)s'
                            '|%(message)s|%(pathname)s|%(lineno)d|'),
                    datefmt='%Y-%m-%dT%H:%M:%S',
                    )

  fire.Fire(IssueTriage)
