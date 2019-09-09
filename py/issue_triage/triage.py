"""Identify issues that need triage."""
from code_intelligence import graphql
from code_intelligence import util
import datetime
from dateutil import parser as dateutil_parser
import fire
import json
import logging
import os
import numpy as np
import pprint
import retrying
import json

TOKEN_NAME = "GITHUB_TOKEN"

# TODO(jlewi): If we make this an app maybe we should read this from a .github
# file
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

    self.triage_project_card = None

    # The times of various events
    self.kind_time = None
    self.priority_time = None
    self.project_time = None
    self.area_time = None
    self.closed_at = None

    self.requires_project = False

  @classmethod
  def from_issue(cls, issue):
    """Construct TriageInfo from the supplied issue"""
    info = TriageInfo()
    info.issue = issue
    labels = graphql.unpack_and_split_nodes(issue, ["labels", "edges"])

    project_cards = graphql.unpack_and_split_nodes(issue,
                                                   ["projectCards", "edges"])

    events = graphql.unpack_and_split_nodes(issue,
                                            ["timelineItems", "edges"])

    for l in labels:
      name = l["name"]

      if name in ALLOWED_PRIORITY:
        info.requires_project = name in REQUIRES_PROJECT

    for c in project_cards:
      if c.get("project").get("name") == TRIAGE_PROJECT:
        info.triage_project_card = c
        break

    # TODO(jlewi): Could we potentially miss some events since we aren't
    # paginating through all events for an issue? This should no longer
    # be an issue because _process_issue will call _get_issue and paginate
    # through all results.
    for e in events:

      if not "createdAt" in e:
        continue

      t = dateutil_parser.parse(e.get("createdAt"))

      if e.get("__typename") == "LabeledEvent":
        name = e.get("label").get("name")

        if name.startswith("kind"):
          if info.kind_time:
            continue
          info.kind_time = t

        if name.startswith("area"):
          if info.area_time:
            continue
          info.area_time = t

        if name in ALLOWED_PRIORITY:
          if info.priority_time:
            continue
          info.priority_time = t

      if e.get("__typename") == "AddedToProjectEvent":
        if info.project_time:
          continue
        info.project_time = t

    if issue.get("closedAt"):
      info.closed_at = dateutil_parser.parse(issue.get("closedAt"))

    return info

  def __eq__(self, other):
    for f in ["kind_time", "priority_time", "project_time", "area_time",
              "closed_at", "in_triage_project", "requires_project"]:
      if getattr(self, f) != getattr(other, f):
        return False

    if self.in_triage_project:
      if self.triage_project_card["id"] != other.triage_project_card["id"]:
        return False
    return True

  @property
  def needs_triage(self):
    """Return true if the issue needs triage"""
    # closed issues don't need triage
    if self.issue["state"].lower() == "closed":
      return False

    # If any events are missing then we need triage
    for f in ["kind_time", "priority_time", "area_time"]:
      if not getattr(self, f):
        return True

    if self.requires_project and not self.project_time:
      return True

    return False

  def __repr__(self):
    pieces = ["needs_triage={0}".format(self.needs_triage)]

    for f in ["kind_time", "priority_time", "project_time", "area_time",
              "closed_at", "in_triage_project"]:
      v = getattr(self, f)
      if not v:
        continue

      if isinstance(v, datetime.datetime):
        v = v.isoformat()
      pieces.append("{0}={1}".format(f, v))

    return ";".join(pieces)

  def message(self):
    """Return a human readable message."""
    if not self.needs_triage:
      return "Issue doesn't need attention."

    lines = []
    if self.needs_triage:
      lines.append("Issue needs triage:")

    if not self.kind_time:
      lines.append("\t Issue needs a kind label")

    if not self.priority_time:
      lines.append("\t Issue needs one of the priorities {0}".format(ALLOWED_PRIORITY))

    if not self.area_time:
      lines.append("\t Issue needs an area label")

    if self.requires_project and not self.project_time:
      lines.append("\t Issues with priority in {0} need to be assigned to a project".format(REQUIRES_PROJECT))

    return "\n".join(lines)

  @property
  def triaged_at(self):
    """Returns a datetime representing the time it was triage or None."""
    if self.needs_triage:
      return None

    # Determine whether issue was triaged by being closed or not
    events = [self.kind_time,
              self.priority_time,
              self.area_time]

    if self.requires_project:
      events.append(self.project_time)

    has_all_events = True
    for e in events:
      if not e:
        has_all_events = False

    if has_all_events:
      events = sorted(events)
      return events[-1]
    else:
      return self.closed_at

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

  def _iter_issues(self, org, repo, issue_filter=None, output=None):
    """Iterate over issues in batches for a repository

    Args:
      org: The org that owns the repository
      repo: The directory for the repository
      output: The directory to write the results; if not specified results
        are not downloaded
      issue_filter: Used to filter issues to consider based on when they were
        last updated

    Writes the issues along with the first comments to a file in output
    directory.
    """
    client = graphql.GraphQLClient()

    num_issues_per_page = 100

    if not issue_filter:
      today = datetime.datetime.now()
      today = datetime.datetime(year=today.year, month=today.month, day=today.day)

      start_time = today - datetime.timedelta(days=60)

    # Labels and projects are available via timeline events.
    # However, in timeline events project info (e.g. actual project name)
    # is only in developer preview.
    # The advantage of using labels and projectCards (as opposed to timeline
    # events) is that its much easier to bound the number of items we need
    # to fetch in order to return all labels and projects
    # for timeline items its much more likely the labels and projects we care
    # about will require pagination.
    #
    # TODO(jlewi): We should add a method to fetch all issue timeline items
    # via pagination in the case the number of items exceeds the page size.
    #
    # TODO(jlewi): We need to consider closed issues if we want to compute
    # stats.
    #
    # TODO(jlewi): We should support fetching only OPEN issues; if we are
    # deciding which issues need triage or have been triaged we really only
    # need to look at open isues. Closed Issues will automatically move to
    # the appropriate card in the Kanban board.
    query = """query getIssues($org: String!, $repo: String!, $pageSize: Int, $issueCursor: String, $filter: IssueFilters) {
  repository(owner: $org, name: $repo) {
    issues(first: $pageSize, filterBy: $filter, after: $issueCursor) {
      totalCount
      pageInfo {
        endCursor
        hasNextPage
      }
      edges {
        node {
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
          createdAt
          closedAt
          labels(first: 30) {
            totalCount
            edges {
              node {
                name
              }
            }
          }
          projectCards(first: 30) {
            totalCount
            pageInfo {
              endCursor
              hasNextPage
            }
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
          timelineItems(first: 30) {
            totalCount
            pageInfo {
              endCursor
              hasNextPage
            }
            edges {
              node {
                __typename
                ... on AddedToProjectEvent {
                  createdAt

                }
                ... on LabeledEvent {
                  createdAt
                  label {
                    name
                  }
                }
                ... on ClosedEvent {
                  createdAt
                }
              }
            }
          }
        }
      }
    }
  }
}
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

    if not issue_filter:
      start_time = datetime.datetime.now() - datetime.timedelta(weeks=24)
      issue_filter = {
        "since": start_time.isoformat(),
      }

    while has_next_issues_page:

      variables = {
        "org": org,
        "repo": repo,
        "pageSize": num_issues_per_page,
        "issueCursor": issues_cursor,
        "filter": issue_filter,
      }
      results = client.run_query(query, variables=variables)

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


  def download_issues(self, repo, output, issue_filter=None):
    """Download the issues to the specified directory

    Args:
      repo: Repository in the form {org}/{repo}
    """

    org, repo_name = repo.split("/")

    for shard_index, shard in enumerate(self._iter_issues(org, repo_name,
                                                          output=output,
                                                          issue_filter=None)):
      logging.info("Wrote shard %s", shard_index)

  def _build_dataframes(self, issues_dir):
    """Build dataframes containing triage info.

    Args:
      issues_dir: The directory containing issues

    Returns:
      data:
    """

  def update_kanban_board(self):
    """Checks if any issues in the needs triage board can be removed.
    """
    query = """query getIssues($issueCursor: String) {
  search(type: ISSUE, query: "is:open is:issue org:kubeflow project:kubeflow/26", first: 100, after: $issueCursor) {
    issueCount
    pageInfo {
      endCursor
      hasNextPage
    }
    edges {
      node {
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
          createdAt
          closedAt
          labels(first: 30) {
            totalCount
            edges {
              node {
                name
              }
            }
          }
          projectCards(first: 30) {
            totalCount
            pageInfo {
              endCursor
              hasNextPage
            }
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
          timelineItems(first: 30) {
            totalCount
            pageInfo {
              endCursor
              hasNextPage
            }
            edges {
              node {
                __typename
                ... on AddedToProjectEvent {
                  createdAt
                }
                ... on LabeledEvent {
                  createdAt
                  label {
                    name
                  }
                }
                ... on ClosedEvent {
                  createdAt
                }
              }
            }
          }
        }
      }
    }
  }
}
"""
    issues_cursor = None
    has_next_issues_page = True
    while has_next_issues_page:

      variables = {
        "issueCursor": issues_cursor,
      }
      results = self.client.run_query(query, variables=variables)

      if results.get("errors"):
        message = json.dumps(results.get("errors"))
        logging.error("There was a problem issuing the query; errors:\n%s",
                      "\n", message)
        return

      issues = graphql.unpack_and_split_nodes(
        results, ["data", "search", "edges"])

      for i in issues:
        self._process_issue(i)

      page_info = results["data"]["search"]["pageInfo"]
      issues_cursor = page_info["endCursor"]
      has_next_issues_page = page_info["hasNextPage"]


  def triage(self, repo, output=None, **kwargs):
    """Triage issues in the specified repository.

    Args:
      repo: Repository in the form {org}/{repo}
      output: (Optional) directory to write issues
    """
    org, repo_name = repo.split("/")

    for shard_index, shard in enumerate(self._iter_issues(org, repo_name,
                                                          output=output,
                                                          **kwargs)):
      logging.info("Processing shard %s", shard_index)
      for i in shard:
        self._process_issue(i)

  def _get_issue(self, url):
    """Gets the complete issue.

    This function does pagination to fetch all timeline items.
    """

    # TODO(jlewi): We should impelement pagination for labels as well
    query = """query getIssue($url: URI!, $timelineCursor: String) {
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
      timelineItems(first: 30, after: $timelineCursor) {
            totalCount
            pageInfo {
              endCursor
              hasNextPage
            }
            edges {
              node {
                __typename
                ... on AddedToProjectEvent {
                  createdAt

                }
                ... on LabeledEvent {
                  createdAt
                  label {
                    name
                  }
                }
                ... on ClosedEvent {
                  createdAt
                }
              }
           }
      }
    }
  }
}"""

    variables = {
      "url": url,
      "timelineCursor": None,
    }
    results = self.client.run_query(query, variables=variables)

    if results.get("errors"):
      message = json.dumps(results.get("errors"))
      logging.error("There was a problem issuing the query; errors:\n%s",
                        "\n".join(message))
      return

    issue = results["data"]["resource"]

    has_next_page = issue["timelineItems"]["pageInfo"]["hasNextPage"]

    while has_next_page:
      variables["timelineCursor"] = issue["timelineItems"]["pageInfo"]["endCursor"]
      results = self.client.run_query(query, variables=variables)

      edges  = (issue["timelineItems"]["edges"] +
                results["data"]["resource"]["timelineItems"]["edges"])
      issue["timelineItems"]["edges"] = edges
      issue["timelineItems"]["pageInfo"] = (
        results["data"]["resource"]["timelineItems"]["pageInfo"])
      has_next_page = (results["data"]["resource"]["timelineItems"]["pageInfo"]
                       ["hasNextPage"])

    return issue

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
    issue = self._get_issue(url)
    return self._process_issue(issue)

  def _process_issue(self, issue, add_comment=False):
    """Process a single issue.

    Args:
      issue: Issue to process.
    """

    if issue["timelineItems"]["pageInfo"]["hasNextPage"]:
      # Since not all timelineItems were fetched; we need to refetch
      # the issue and this time paginate to get all items.
      logging.info("Issue: %s; fetching all timeline items", issue["url"])
      issue = self._get_issue(issue["url"])

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
    return info

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
