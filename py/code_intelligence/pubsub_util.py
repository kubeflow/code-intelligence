from google.cloud import pubsub
from google.api_core.exceptions import AlreadyExists
import logging

def check_subscription_name_exists(project_id, subscription_name, subscriber=None):
    """
    Check if the subscription name exists in the project.
    Args:
      project_id: project id on GCP
      subscription_name: subscription name that listens to the topic
      subscriber: subscriber client for Google Cloud Pub/Sub

    Return
    ------
    bool
        subscription name exists in the project or not
    """
    if not subscriber:
        subscriber = pubsub.SubscriberClient()
    project_path = subscriber.project_path(project_id)
    subscription_path = subscriber.subscription_path(project_id,
                                                     subscription_name)
    for existing_subscription_path in subscriber.list_subscriptions(project_path):
        if existing_subscription_path.name == subscription_path:
            logging.info(f'The subscription path {subscription_path} already exists')
            return True
    return False

def create_subscription_if_not_exists(project_id, topic_name, subscription_name, subscriber=None, publisher=None):
    """
    Create a new pull subscription on the topic if not exists.
    Args:
      project_id: project id on GCP
      topic_name: the topic name that subscribers listen to
      subscription_name: subscription name that listens to the topic
      subscriber: subscriber client for Google Cloud Pub/Sub
      publisher: publisher client for Google Cloud Pub/Sub
    """
    if not subscriber:
        subscriber = pubsub.SubscriberClient()
    if not publisher:
        publisher = pubsub.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)
    subscription_path = subscriber.subscription_path(project_id,
                                                     subscription_name)
    try:
        subscriber.create_subscription(name=subscription_path, topic=topic_path)
    except AlreadyExists:
        logging.info(f'The subscription path {subscription_path} already exists')
    except Exception as e:
        raise e

def check_topic_name_exists(project_id, topic_name, publisher=None):
    """
    Check if the topic path exists in the project.
    Args:
      project_id: project id on GCP
      topic_path: topic path in pubsub
      publisher: publisher client for Google Cloud Pub/Sub

    Return
    ------
    bool
        topic_path exists or not
    """
    if not publisher:
        publisher = pubsub.PublisherClient()
    project_path = publisher.project_path(project_id)
    topic_path = publisher.topic_path(project_id, topic_name)
    for existing_topic_path in publisher.list_topics(project_path):
        if existing_topic_path.name == topic_path:
            logging.info(f'The topic path {topic_path} already exists')
            return True
    return False

def create_topic_if_not_exists(project_id, topic_name, publisher=None):
    """
    Create a new pubsub topic if the topic name does not exist in the project.
    Args:
      project_id: project id on GCP
      topic_name: topic name that will be created
      publisher: publisher client for Google Cloud Pub/Sub
    """
    if not publisher:
        publisher = pubsub.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)
    try:
        publisher.create_topic(topic_path)
    except AlreadyExists:
        logging.info(f'The topic path {topic_path} already exists')
    except Exception as e:
        raise e
