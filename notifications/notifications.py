import fire
import github3
import logging
import os
import retrying

TOKEN_NAME = "GITHUB_TOKEN"
PULL_REQUEST_TYPE = "PullRequest"

def process_notification(n):
  # Mark as read anything that isn't an explicit mention.
  # For PRs there doesn't seem like a simple way to detect if the notice
  # is because the state changed
  if n.reason == "mention":
    return

  title = n.subject.get("title")
  logging.info("Marking as read: type: %s reason: %s title: %s",
               n.subject.get("type"), n.reason, title)
  n.mark()

class NotificationManager(object):
  def mark_read(user):
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


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO,
                    format=('%(levelname)s|%(asctime)s'
                            '|%(message)s|%(pathname)s|%(lineno)d|'),
                    datefmt='%Y-%m-%dT%H:%M:%S',
                    )

  fire.Fire(NotificationManager)




  print("Done")