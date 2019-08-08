import os
import dill as dpickle
import requests
import json
import numpy as np
from bs4 import BeautifulSoup
from passlib.apps import custom_app_context as pwd_context
from google.cloud import pubsub
from google.cloud import storage
import logging
from repo_config import RepoConfig
from mlp import MLPWrapper
from github_utils import init as github_init
from github_utils import get_issue_handle, get_yaml

class Worker:
    """Worker aims to
    Listen to events in Google Cloud PubSub.
    Load the model mapped to the current event.
    Generate label prediction and check thresholds.
    Call GitHub API to add labels if needed.
    """

    def __init__(self):
        self.project_id = 'issue-label-bot-dev'
        self.topic_name = 'event_queue'
        self.subscription_name = 'subscription_for_event_queue'

        # init GitHub app
        github_init()

    def load_yaml(self, repo_owner, repo_name):
        """
        Load config from the YAML of the specific repo_owner/repo_name.
        Args:
          repo_owner: str
          repo_name: str
        """
        config = RepoConfig(repo_owner=repo_owner, repo_name=repo_name)
        self.repo_owner = config.repo_owner
        self.repo_name = config.repo_name

        self.model_bucket_name = config.model_bucket_name
        self.model_file = config.model_local_path
        self.model_dest = config.model_gcs_path

        self.labels_file = config.labels_local_path
        self.labels_dest = config.labels_gcs_path

        self.embeddings_bucket_name = config.embeddings_bucket_name
        self.embeddings_file = config.embeddings_local_path
        self.embeddings_dest = config.embeddings_gcs_path

    def create_subscription(self):
        """
        Create a new pull subscription on the topic.
        This function should only be called once for all workers while setup,
        not once for each worker.

        While multiple subscribers listen to the same subscription,
        subscribers receive a subset of the messages.
        """
        subscriber = pubsub.SubscriberClient()
        publisher = pubsub.PublisherClient()
        topic_path = publisher.topic_path(self.project_id,
                                          self.topic_name)
        subscription_path = subscriber.subscription_path(self.project_id,
                                                         self.subscription_name)
        subscriber.create_subscription(name=subscription_path, topic=topic_path)

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
            installation_id = message.attributes['installation_id']
            repo_owner = message.attributes['repo_owner']
            repo_name = message.attributes['repo_name']
            issue_num = message.attributes['issue_num']
            logging.info(f'Receive issue #{issue_num} from {repo_owner}/{repo_name}')

            # predict labels
            self.load_yaml(repo_owner, repo_name)
            self.download_model_from_gcs()
            predictions, issue_embedding = self.predict_labels(repo_owner, repo_name, issue_num)
            self.add_labels_to_issue(installation_id, repo_owner, repo_name,
                                     issue_num, predictions)

            # log the prediction, which will be used to track the performance
            log_dict = {
                'repo_owner': repo_owner,
                'repo_name': repo_name,
                'issue_num': int(issue_num),
                'labels': predictions['labels']
            }
            logging.info(log_dict)

            # acknowledge the message, or pubsub will repeatedly attempt to deliver it
            message.ack()

        # limit the subscriber to only have one outstanding message at a time
        flow_control = pubsub.types.FlowControl(max_messages=1)
        future = subscriber.subscribe(subscription_path,
                                      callback=callback,
                                      flow_control=flow_control)
        try:
            logging.info(future.result())
        except KeyboardInterrupt:
            logging.info(future.cancel())

    def get_issue_text(self, repo_owner, repo_name, issue_num, skip_issue=True):
        """
        Get the raw text of an issue body and label.
        Args:
          repo_owner: repo owner
          repo_name: repo name
          issue_num: issue index
          skip_issue: raise exception or not. If True, ignore exception

        Return
        ------
        dict
            {'title': str, 'body': str, 'url': str, 'num': int}
        """
        url = f'https://github.com/{repo_owner}/{repo_name}/issues/{issue_num}'
        status_code = requests.head(url).status_code
        if status_code != 200:
            if skip_issue:
                return None
            raise Exception(f'Status code is {status_code} not 200:\n'
                            '{url} is not an issue.\n'
                            'Note: status code is 302 if it is a pull request')

        soup = BeautifulSoup(requests.get(url).content, 'html.parser')
        title_find = soup.find("span", class_="js-issue-title")
        body_find = soup.find("td", class_="js-comment-body")

        if not title_find or not body_find:
            return None

        title = title_find.get_text().strip()
        body = body_find.get_text().strip()

        return {'title': title,
                'body': body,
                'url': url,
                'num': issue_num}

    def get_issue_embedding(self, repo_owner, repo_name, issue_num):
        """
        Get the embedding of the issue by calling GitHub Issue
        Embeddings API endpoint.
        Args:
          repo_owner: repo owner
          repo_name: repo name
          issue_num: issue index

        Return
        ------
        numpy.ndarray
            shape: (1600,)
        """
        api_endpoint = 'https://embeddings.gh-issue-labeler.com/text'
        api_key = os.environ['GH_ISSUE_API_KEY']

        issue_text = self.get_issue_text(repo_owner=repo_owner,
                                         repo_name=repo_name,
                                         issue_num=issue_num)
        data = {'title': issue_text['title'],
                'body': issue_text['body']}

        # sending post request and saving response as response object
        r = requests.post(url=api_endpoint,
                          headers={'Token': pwd_context.hash(api_key)},
                          json=data)

        embeddings = np.frombuffer(r.content, dtype='<f4')[:1600]
        return embeddings

    def download_model_from_gcs(self):
        """Download the model from GCS to local path."""
        # download model
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(self.model_bucket_name)
        blob = bucket.get_blob(self.model_dest)
        with open(self.model_file, 'wb') as f:
            blob.download_to_file(f)

        # download lable columns
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(self.model_bucket_name)
        blob = bucket.get_blob(self.labels_dest)
        with open(self.labels_file, 'wb') as f:
            blob.download_to_file(f)

    def load_label_columns(self):
        """
        Load label info from local path.

        Return
        ------
        dict
            {'labels': list, 'probability_thresholds': {label_index: threshold}}
        """
        with open(self.labels_file, 'rb') as f:
            label_columns = dpickle.load(f)
        return label_columns

    def predict_labels(self, repo_owner, repo_name, issue_num):
        """
        Predict labels for given issue.
        Args:
          repo_owner: repo owner
          repo_name: repo name
          issue_num: issue index

        Return
        ------
        dict
            {'labels': list, 'probabilities': list}
        numpy.ndarray
            shape: (1600,)
        """
        logging.info(f'Predicting labels for the issue #{issue_num} from {repo_owner}/{repo_name}')
        issue_embedding = self.get_issue_embedding(repo_owner=repo_owner,
                                                   repo_name=repo_name,
                                                   issue_num=issue_num)
        mlp_wrapper = MLPWrapper(clf=None,
                                 model_file=self.model_file,
                                 load_from_model=True)
        # change embedding from 1d to 2d for prediction and extract the result
        label_probabilities = mlp_wrapper.predict_proba([issue_embedding])[0]

        # get label info from local file
        label_columns = self.load_label_columns()
        label_names = label_columns['labels']
        label_thresholds = label_columns['probability_thresholds']

        # check thresholds to get labels that need to be predicted
        predictions = {'labels': [], 'probabilities': []}
        for i in range(len(label_probabilities)):
            # if the threshold of any label is None, just ignore it
            # because the label does not meet both of precision & recall thresholds
            if label_thresholds[i] and label_probabilities[i] >= label_thresholds[i]:
                predictions['labels'].append(label_names[i])
                predictions['probabilities'].append(label_probabilities[i])
        return predictions, issue_embedding

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
        label_names = []
        label_probabilities = []
        if predictions['labels']:
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

        # get the isssue handle
        issue = get_issue_handle(installation_id, repo_owner, repo_name, issue_num)

        if label_names:
            # create message
            message = f'Issue-Label Bot is automatically applying the labels '\
                      f'`{"`, `".join(label_names)}` to this issue, with the confidence of '\
                      f'{", ".join(["{:.2f}".format(p) for p in label_probabilities])}. '\
                       'Please mark this comment with :thumbsup: or :thumbsdown: to give our '\
                       'bot feedback! \n\n Links: [app homepage](https://github.com/marketplace/issue-label-bot), '\
                       '[dashboard]({app_url}data/{username}/{repo}) and [code](https://github.com/hamelsmu/MLapp) for this bot.'
            # label the issue using the GitHub api
            issue.add_labels(*label_names)
            logging.info(f'Add `{"`, `".join(label_names)}` to the issue # {issue_num}')
        else:
            message = f'Issue Label Bot is not confident enough to auto-label this issue. '\
                       'See [dashboard]({app_url}data/{username}/{repo}) for more details.'
            logging.warning(f'Not confident enough to label this issue: # {issue_num}')

        # make a comment using the GitHub api
        comment = issue.create_comment(message)
