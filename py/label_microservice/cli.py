"""A cli for interacting with the models.

The CLI can be used to publish issues to perform inference on to pubsub
to be picked up by the backends.
"""
import logging
import json
import fire
from code_intelligence import graphql
from code_intelligence import github_util
from code_intelligence import util
from google.cloud import pubsub
import subprocess

DEFAULT_TOPIC = "projects/issue-label-bot-dev/topics/TEST_event_queue"
class Cli:
  @staticmethod
  def get_issue(url):
    """Get the data for a specific issue.

    Args:
      url: URL of the issue
    """
    gh_client = graphql.GraphQLClient()
    result = github_util.get_issue(url, gh_client)
    print(json.dumps(result, indent=4, sort_keys=True))

  @staticmethod
  def label_issue(issue, pubsub_topic=DEFAULT_TOPIC):
    """Label a specific issue.

    Args:
      issue: The issue in the form {owner}/{repo}#{issue}
      pubsub_topic: (Optional) the pubsub topic to publish to. This should
        be in the form projects/{project}/topics/{topic_name}
    """
    publisher = pubsub.PublisherClient()
    repo_owner, repo_name, issue_num = util.parse_issue_spec(issue)

    if not repo_owner:
      raise ValueError(f"issue={issue} didn't match regex "
                       f"{util.ISSUE_RE.pattern}")

    # all attributes being published to pubsub must be sent as text strings
    publisher.publish(pubsub_topic,
                      b'New issue.',
                      # TODO(jlewi): Does the backend depend on the client
                      # providing the installation id
                      installation_id="",
                      repo_owner=repo_owner,
                      repo_name=repo_name,
                      issue_num=str(issue_num))

  @staticmethod
  def pod_logs(pod):
    """Pretty print pod logs

    Args:
      pod: Name of the pod
    """
    output = subprocess.check_output(["kubectl", "logs", pod])

    for l in output.splitlines():
      try:
        entry = json.loads(l)
        filename = entry.get("filename")
        line = entry.get("line")
        message = entry.get("message")
        print(f"{filename}:{line}: {message}")
      except json.JSONDecodeError:
        print(l)
        continue
if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO,
                      format=('%(levelname)s|%(asctime)s'
                              '|%(message)s|%(pathname)s|%(lineno)d|'),
                      datefmt='%Y-%m-%dT%H:%M:%S',
                      )

  fire.Fire(Cli)
