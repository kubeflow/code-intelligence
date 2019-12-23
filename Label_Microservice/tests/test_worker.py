import unittest
from unittest.mock import Mock
import os
import label_microservice
from label_microservice.worker import Worker
import code_intelligence

class TestWorker(unittest.TestCase):

    #def test_get_issue_embedding(self):
        #"""Testing get_issue_embedding function while status code is not 200"""
        ## init setting
        #os.environ['GH_ISSUE_API_KEY'] = ''
        #os.environ['APP_URL'] = ''
        #label_microservice.worker.github_init = Mock()
        #Worker.create_subscription_if_not_exists = Mock()

        #label_microservice.worker.get_issue_text = Mock()
        #label_microservice.worker.get_issue_text.return_value = {
                #'title': 'test_title',
                #'body': 'test_body'
            #}
        ## let status code to be 404
        #label_microservice.worker.requests.post = Mock()
        #label_microservice.worker.requests.post.return_value.status_code = 404
        #issue_embedding = Worker().get_issue_embedding('repo_owner', 'repo_name', 'issue_num')
        ## issue_embedding should be None
        #assert not issue_embedding

    #def teat_predict_issue_probability_not_retrieve_embedding(self):
        #"""Testing predict_issue_probability function while not retrieving embedding"""
        ## init setting
        #os.environ['GH_ISSUE_API_KEY'] = ''
        #os.environ['APP_URL'] = ''
        #label_microservice.worker.github_init = Mock()
        #Worker.create_subscription_if_not_exists = Mock()

        ## let worker to not retrive embedding of an issue
        #Worker.get_issue_embedding = Mock()
        #Worker.get_issue_embedding.return_value = None
        #label_probabilities, issue_embedding = Worker().predict_issue_probability('repo_owner', 'repo_name', 'issue_num')
        ## issue_embedding is None, no predict probabilities
        #assert label_probabilities == [] and not issue_embedding

    # TODO(jlewi): Delete this code. Its now in repo_specific_model_test
    #def test_predict_labels(self):
        #"""Testing predict_labels function"""
        ## init setting
        #os.environ['GH_ISSUE_API_KEY'] = ''
        #os.environ['APP_URL'] = ''
        #label_microservice.worker.github_init = Mock()
        #Worker.create_subscription_if_not_exists = Mock()

        #Worker.predict_issue_probability = Mock()
        #Worker.predict_issue_probability.return_value = ([0.7, 0.6, 0.5], None)
        #Worker.load_label_columns = Mock()
        #Worker.load_label_columns.return_value = {
                #'labels': ['label1', 'label2', 'label3'],
                #'probability_thresholds': {0: 0.6, 1: 0.7, 2: 0.5}
            #}
        #predictions, _ = Worker().predict_labels('repo_owner', 'repo_name', 'issue_num')
        ## label1 and label3 satisfy thresholds
        #assert predictions['labels'] == ['label1', 'label3'] and\
            #predictions['probabilities'] == [0.7, 0.5]

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
