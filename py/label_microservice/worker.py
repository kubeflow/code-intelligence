import os
import fire
import requests
import yaml
from google.cloud import pubsub
import logging
from label_microservice.repo_config import RepoConfig
from code_intelligence.github_util import init as github_init
from code_intelligence.github_util import get_issue_handle
from code_intelligence.github_util import get_yaml
from code_intelligence.pubsub_util import check_subscription_name_exists
from code_intelligence.pubsub_util import create_subscription_if_not_exists
from label_microservice import issue_label_predictor

class Worker:
    """
    The worker class aims to do label prediction for issues from github repos.
    The processes are the following:
    Listen to events in Google Cloud PubSub.
    Load the model mapped to the current event.
    Generate label prediction and check thresholds.
    Call GitHub API to add labels if needed.
    """

    def __init__(self,
                 project_id='issue-label-bot-dev',
                 topic_name='event_queue',
                 subscription_name='subscription_for_event_queue',):
        """
        Initialize the parameters and GitHub app.
        Args:
          project_id: gcp project id, str
          topic_name: pubsub topic name, str
          subscription_name: pubsub subscription name, str
          embedding_api_endpoint: endpoint of embedding api microservice, str
        """
        self.project_id = project_id
        self.topic_name = topic_name
        self.subscription_name = subscription_name

        self.app_url = os.environ['APP_URL']

        # init GitHub app
        github_init()
        # init pubsub subscription
        self.create_subscription_if_not_exists()

        self._predictor = None

    @classmethod
    def subscribe_from_env(cls):
        """Build the worker from environment variables and subscribe"""
        required_env = ["PROJECT", "ISSUE_EVENT_TOPIC",
                        "ISSUE_EVENT_SUBSCRIPTION"]
        missing = []
        for e in required_env:
            if not os.environ.get(e):
                missing.append(e)

        if missing:
            raise ValueError(f"Missing required environment variables "
                             f"{','.join(required)}")
        worker = Worker(project_id=os.getenv("PROJECT"),
                        topic_name=os.getenv("ISSUE_EVENT_TOPIC"),
                        subscription_name=os.getenv("ISSUE_EVENT_SUBSCRIPTION"))
        worker.subscribe()

        return worker
    def check_subscription_name_exists(self):
        """
        Check if the subscription name exists in the project.

        Return
        ------
        bool
            subscription_name exists in the project or not
        """
        return check_subscription_name_exists(self.project_id, self.subscription_name)

    def create_subscription_if_not_exists(self):
        """
        Create a new pull subscription on the topic if not exists.

        While multiple subscribers listen to the same subscription,
        subscribers receive a subset of the messages.
        """
        create_subscription_if_not_exists(self.project_id, self.topic_name, self.subscription_name)

    def subscribe(self):
        """
        Receive messages from a pull subscription.
        When the subscriber receives a message from pubsub,
        it will call the `callback` function to do label
        prediction and add labels to the issue.
        """
        subscriber = pubsub.SubscriberClient()
        subscription_path = subscriber.subscription_path(self.project_id,
                                                         self.subscription_name)

        def callback(message):
            """
            Address events in pubsub by sequential procedures.
            Load the model mapped to the events.
            Do label prediction.
            Add labels if the confidence is enough.
            Args:
              Object:
              message =
                  Message {
                      data: b'New issue.',
                      attributes: {
                          'installation_id': '10000',
                          'repo_owner': 'kubeflow',
                          'repo_name': 'examples',
                          'issue_num': '1'
                      }
                  }
            """
            if self._predictor is None:
                # We load the models here and not in __init__ because we
                # need to create the TensorFlow models inside the thread used
                # by pubsub for the callbacks. If we load them in __init__
                # they get created in a different thread and TF will return
                # errors when trying to use the models in a different thread.
                logging.info("Creating predictor")
                self._predictor = issue_label_predictor.IssueLabelPredictor()

            # The code that publishes the message is:
            # https://github.com/machine-learning-apps/Issue-Label-Bot/blob/26d8fb65be3b39de244c4be9e32b2838111dac10/flask_app/forward_utils.py#L57
            # The front end does have access to the title and body
            # but its not being sent right now.
            logging.info(f"Recieved message {message}")
            installation_id = message.attributes['installation_id']
            repo_owner = message.attributes['repo_owner']
            repo_name = message.attributes['repo_name']
            issue_num = message.attributes['issue_num']

            data = {
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "issue_num": issue_num,
            }
            try:
                predictions = self._predictor.predict(data)

                logging.warning("Need to add labels to issue")
                #self.add_labels_to_issue(installation_id, repo_owner, repo_name,
                                         #issue_num, predictions)

                # log the prediction, which will be used to track the performance
                # TODO(https://github.com/kubeflow/code-intelligence/issues/79)
                # Ensure we capture the information needed to measure performance
                # in stackdriver
                log_dict = {
                    'repo_owner': repo_owner,
                    'repo_name': repo_name,
                    'issue_num': int(issue_num),
                    'labels': predictions['labels']
                }
                logging.info(log_dict)

            except Exception as e:
                # hard to find out which errors should be handled differently (e.g., retrying for multiple times)
                # and how to handle the error that the same message causes for multiple times
                # so use generic exception to ignore all errors for now
                logging.error(f'Addressing issue #{issue_num} from {repo_owner}/{repo_name} causes an error')
                logging.error(f'Error type: {type(e)}')
                logging.error(e)

            # acknowledge the message, or pubsub will repeatedly attempt to deliver it
            message.ack()

        # limit the subscriber to only have one outstanding message at a time
        flow_control = pubsub.types.FlowControl(max_messages=1)
        future = subscriber.subscribe(subscription_path,
                                      callback=callback,
                                      flow_control=flow_control)

        # Calling future.result will block forever. future.cancel can be called
        # to interrupt it.
        # TODO(jlewi): It might be better to return the future. This would
        # allow the caller to potentially cancel the process
        try:
            logging.info("Wait forever or until pubsub future is cancelled")
            logging.info(future.result())
        except KeyboardInterrupt:
            logging.info(future.cancel())

    # TODO(jlewi): Where should this function go after the refactor in
    # https://github.com/kubeflow/code-intelligence/pull/77? This function
    # is fetching the repo specific bot config and applying it. Need to think
    # about what we want to do there. e.g. do we want to use it for label
    # aliases? This was originally only applied to the repo specific labels?
    # Do we really need this? This feels redundant with the probability thresholds
    # for the labels.
    def filter_specified_labels(self, repo_owner, repo_name, predictions):
        """
        Only select those labels which are specified by yaml file to be predicted.
        If there is no setting in the yaml file, return all predicted items.
        Args:
          repo_owner: repo owner, str
          repo_name: repo name, str
          prediction: predicted result from `predict_labels()` function
                      dict {'labels': list, 'probabilities': list}
        """
        label_names = []
        label_probabilities = []
        # handle the yaml file
        yaml = get_yaml(owner=repo_owner, repo=repo_name)
        # user may set the labels they want to predict
        if yaml and 'predicted-labels' in yaml:
            for name, proba in zip(predictions['labels'], predictions['probabilities']):
                if name in yaml['predicted-labels']:
                    label_names.append(name)
                    label_probabilities.append(proba)
        else:
            logging.warning(f'YAML file does not contain `predicted-labels`, '
                             'bot will predict all labels with enough confidence')
            # if user do not set `predicted-labels`,
            # predict all labels with enough confidence
            label_names = predictions['labels']
            label_probabilities = predictions['probabilities']
        return label_names, label_probabilities

    def add_labels_to_issue(self, installation_id, repo_owner, repo_name,
                            issue_num, predictions):
        """
        Add predicted labels to issue using GitHub API.
        Args:
          installation_id: repo installation id
          repo_owner: repo owner
          repo_name: repo name
          issue_num: issue index
          prediction: predicted result from `predict_labels()` function
                      dict {'labels': list, 'probabilities': list}
        """
        # take an action if the prediction is confident enough
        if predictions['labels']:
            label_names, label_probabilities = self.filter_specified_labels(repo_owner,
                                                                            repo_name,
                                                                            predictions)
        else:
            label_names = []

        # get the isssue handle
        issue = get_issue_handle(installation_id, repo_owner, repo_name, issue_num)

        if label_names:
            # create message
            message = """Issue-Label Bot is automatically applying the labels `{labels}` to this issue, with the confidence of {confidence}.
            Please mark this comment with :thumbsup: or :thumbsdown: to give our bot feedback!
            Links: [app homepage](https://github.com/marketplace/issue-label-bot), [dashboard]({app_url}data/{repo_owner}/{repo_name}) and [code](https://github.com/hamelsmu/MLapp) for this bot.
            """.format(labels="`, `".join(label_names),
                       confidence=", ".join(["{:.2f}".format(p) for p in label_probabilities]),
                       app_url=self.app_url,
                       repo_owner=repo_owner,
                       repo_name=repo_name)
            # label the issue using the GitHub api
            issue.add_labels(*label_names)
            logging.info(f'Add `{"`, `".join(label_names)}` to the issue # {issue_num}')
        else:
            message = """Issue Label Bot is not confident enough to auto-label this issue.
            See [dashboard]({app_url}data/{repo_owner}/{repo_name}) for more details.
            """.format(app_url=self.app_url,
                       repo_owner=repo_owner,
                       repo_name=repo_name)
            logging.warning(f'Not confident enough to label this issue: # {issue_num}')

        # make a comment using the GitHub api
        comment = issue.create_comment(message)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format=('%(levelname)s|%(asctime)s'
                                '|%(message)s|%(pathname)s|%(lineno)d|'),
                        datefmt='%Y-%m-%dT%H:%M:%S',
                        )

    fire.Fire(Worker)
