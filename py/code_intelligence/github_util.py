import fire
import os
import logging
from code_intelligence import github_app
import typing
import yaml

def get_issue_handle(installation_id, username, repository, number):
  "get an issue object."
  ghapp = github_app.GitHubApp.create_from_env()
  install = ghapp.get_installation(installation_id)
  return install.issue(username, repository, number)

def get_yaml(owner, repo, ghapp=None):
  """
  Looks for the yaml file in a /.github directory.

  yaml file must be named issue_label_bot.yaml
  """

  if not ghapp:
    # TODO(jlewi): Should we deprecate this code path and always pass
    # in the github app?
    ghapp = github_app.GitHubApp.create_from_env()

  try:
    # get the app installation handle
    inst_id = ghapp.get_installation_id(owner=owner, repo=repo)
    inst = ghapp.get_installation(installation_id=inst_id)
    # get the repo handle, which allows you got get the file contents
    repo = inst.repository(owner=owner, repository=repo)
    results = repo.file_contents('.github/issue_label_bot.yaml').decoded
  # TODO(jlewi): We should probably catching more narrow exceptions and
  # not swallowing all exceptions. The exceptions we should swallow are
  # the ones related to the configuration file not existing.
  except Exception as e:
    logging.info(f"Exception occured getting .github/issue_label_bot.yaml: {e}")
    return None

  return yaml.safe_load(results)

def build_issue_doc(org:str, repo:str, title:str, text:typing.List[str]):
  """Build a document string out of various github features.

  Args:
   org: The organization the issue belongs in
   repo: The repository.
   title: Issue title
   text: List of contents of the comments on the issue

  Returns:
   content: The document to classify
  """
  pieces = [title]
  pieces.append(f"{org.lower()}_{repo.lower()}")
  pieces.extend(text)
  content = "\n".join(pieces)
  return content

# TODO(https://github.com/kubeflow/code-intelligence/issues/126): This function should replace
# get_issue_text
def get_issue(url, gh_client):
  """Fetch the issue data using GraphQL.

  Args:
    url: Url of the GitHub isue to fetch
    gh_client: GitHub GraphQl client.

  Returns
    ------
    dict
        {'title':str,
         'comments':List[str]
         'labels': List[str]
         'removed_labels': List[str]}

    comments is a list of comments. The first one will be the body of the issue.

    labels: Labels currently on the issue
    removed_labels: Labels that have been removed
  """

  # The "!" means the variable can't be null. We allow the cursors
  # to be null so that on the first call we fetch the first couple items.
  issue_query = """query getIssue($url: URI!, $labelCursor: String, $timelineCursor: String, $commentsCursor: String) {
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
      comments(first: 100, after: $commentsCursor) {
        totalCount
        edges {
          node {
            author {
              login
            }
            body
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
      timelineItems(first: 100, itemTypes: [UNLABELED_EVENT], after: $timelineCursor) {
        totalCount
        edges {
          node {
            __typename
             ... on UnlabeledEvent {
                  createdAt
                  label {
                    name
                  }
                }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
      labels(first: 100, after: $labelCursor) {
        totalCount
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            name
          }
        }
      }
    }
  }
}"""

  variables = {
    "url": url,
    "labelCursor": None,
    "commentsCursor": None,
    "timelineCurosr": None,
  }

  has_more = True

  result = {
    "title": None,
    "comments": [],
    "comment_authors": [],
    "labels": set(),
    "removed_labels": set(),
  }
  while has_more:
    issue_results = gh_client.run_query(issue_query, variables)

    if "errors" in issue_results:
      logging.error(f"There was a problem running the github query; {issue_results['errors']}")
      raise ValueError(f"There was a problem running the github query: {issue_results['errors']}")

    issue = issue_results["data"]["resource"]

    # Only set the title once on the first call
    if not result["title"]:
      result["title"] = issue["title"]

    if not result["comments"]:
      result["comments"].append(issue["body"])
      result["comment_authors"].append(issue["author"]["login"])

    for e in issue["comments"]["edges"]:
      node = e["node"]
      result["comments"].append(node["body"])
      result["comment_authors"].append(node["author"]["login"])

    for e in issue["labels"]["edges"]:
      node = e["node"]
      result["labels"].add(node["name"])

    for e in issue["timelineItems"]["edges"]:
      node = e["node"]
      result["removed_labels"].add(node["label"]["name"])

    has_more = False

    for f in ["comments", "labels", "timelineItems"]:
      has_more = has_more or issue[f].get("pageInfo").get("hasNextPage")

    variables["labelCursor"] = issue["labels"]["pageInfo"]["endCursor"]
    variables["commentsCursor"] = issue["comments"]["pageInfo"]["endCursor"]
    variables["timelineCursor"] = issue["timelineItems"]["pageInfo"]["endCursor"]

  # For removed_labels we only want labels that were permanently removed
  result["removed_labels"] = result["removed_labels"] - result["labels"]

  result["labels"] = list(result["labels"])
  result["removed_labels"] = list(result["removed_labels"])
  return result
