import os
import yaml
from google.cloud import storage
import logging

class RepoConfig:
    """Load YAML file for configs including repo info and corresponding GCS path"""

    def __init__(self, yaml_path=None, repo_owner=None, repo_name=None):
        """Load config from a local YAML file.
        If the local YAML file does not exist, download it from GCS given repo owner and name.
        Args:
          yaml_path: local YAML file, str
          repo_owner: repository owner, str
          repo_name: repository name, str
        """

        if not yaml_path:
            self.yaml_path = 'issue_label_bot.yaml'
            self.download_yaml_from_gcs(repo_owner, repo_name)
        elif not os.path.exists(yaml_path):
            self.yaml_path = yaml_path
            self.download_yaml_from_gcs(repo_owner, repo_name)
        else:
            self.yaml_path = yaml_path

        with open(self.yaml_path, 'r') as f:
            config = yaml.safe_load(f)

        self.repo_owner = config['repository']['owner']
        self.repo_name = config['repository']['name']

        self.model_bucket_name = 'repo-models'
        self.embeddings_bucket_name = 'repo-embeddings'

        self.model_gcs_path = f'{self.repo_owner}/{self.repo_name}.model'
        self.labels_gcs_path = f'{self.repo_owner}/{self.repo_name}.labels'
        self.embeddings_gcs_path = f'{self.repo_owner}/{self.repo_name}'

        self.model_local_path = f'{self.repo_name}.dpkl'
        self.labels_local_path = f'{self.repo_name}.labels.dpkl'
        self.embeddings_local_path = f'{self.repo_name}.emb.dpkl'

    def download_yaml_from_gcs(self, repo_owner, repo_name):
        """Download YAML file from GCS to the local path.
        Args:
          repo_owner: str, e.g.: 'kubeflow'
          repo_name: str, e.g.: 'examples'
        """
        yaml_bucket_name = 'repo-yaml'
        yaml_dest = f'{repo_owner}/{repo_name}/issue_label_bot.yaml'
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(yaml_bucket_name)
        blob = bucket.get_blob(yaml_dest)
        with open(self.yaml_path, 'wb') as f:
            blob.download_to_file(f)

    @classmethod
    def load(clf, repo_owner, repo_name):
        """Load config given repo owner and name.
        Args:
          repo_owner: str, e.g.: 'kubeflow'
          repo_name: str, e.g.: 'examples'
        """
        return clf(repo_owner=repo_owner, repo_name=repo_name)


if __name__ == '__main__':
    logging.basicConfig(format='%(message)s')
    logging.getLogger().setLevel(logging.INFO)

    config = RepoConfig(yaml_path='issue_label_bot.yaml')
    logging.info(config.__dict__)

    config2 = RepoConfig.load(repo_owner='kubeflow', repo_name='examples')
    logging.info(config2.__dict__)
