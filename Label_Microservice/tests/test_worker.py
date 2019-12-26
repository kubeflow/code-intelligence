# TODO(jlewi): Should this code move to py/label_microservice/
import unittest
from unittest.mock import Mock
import os
import label_microservice
from label_microservice.worker import Worker
import code_intelligence

class TestWorker(unittest.TestCase):

    # TODO(jlewi): Need to figure out where the filter_specified_labels code
    # belongs and move the tests to match. The filter_specified_labels
    # code was originally part of the Worker; but now most of the inference
    # code has moved into the individual model classes.
    def test_filter_specified_labels(self):
        """Testing filter_specified_labels function when yaml specifies labels"""
        # init setting
        os.environ['GH_ISSUE_API_KEY'] = ''
        os.environ['APP_URL'] = ''
        label_microservice.worker.github_init = Mock()
        Worker.create_subscription_if_not_exists = Mock()

        label_microservice.worker.get_yaml = Mock()
        label_microservice.worker.get_yaml.return_value = {'predicted-labels': {'label1': None, 'label2': None}}
        predictions = {'labels': ['label1', 'label3'], 'probabilities': [0.7, 0.8]}
        label_names, label_probabilities = Worker().filter_specified_labels('repo_owner', 'repo_name', predictions)
        # only label1 in the predicted label list
        assert label_names == ['label1'] and label_probabilities == [0.7]

    def test_filter_specified_labels_yaml_not_specified(self):
        """Testing filter_specified_labels function when yaml not specifies labels"""
        # init setting
        os.environ['GH_ISSUE_API_KEY'] = ''
        os.environ['APP_URL'] = ''
        label_microservice.worker.github_init = Mock()
        Worker.create_subscription_if_not_exists = Mock()

        label_microservice.worker.get_yaml = Mock()
        label_microservice.worker.get_yaml.return_value = None
        predictions = {'labels': ['label1', 'label3'], 'probabilities': [0.7, 0.8]}
        label_names, label_probabilities = Worker().filter_specified_labels('repo_owner', 'repo_name', predictions)
        # not specified in the yaml, predict all satisfying thresholds
        assert label_names == predictions['labels'] and label_probabilities == predictions['probabilities']
