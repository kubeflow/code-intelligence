import os
import yaml
from google.cloud import storage

class Config:

    def __init__(self, yaml_path=None, owner=None, repo=None):
        assert yaml_path, "No configure yaml path"
        self.yaml_path = yaml_path

        if owner and repo:
            self.load_yaml_from_gcs(owner, repo)
        self.load()

    def load_yaml_from_gcs(self, owner, repo):
        self.yaml_bucket_name = 'repo-yaml'
        self.yaml_dest = f'{owner}/{repo}/issue_label_bot.yaml'
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(self.yaml_bucket_name)
        blob = bucket.get_blob(self.yaml_dest)
        with open(self.yaml_path, 'wb') as f:
            blob.download_to_file(f)

    def load(self):
        with open(self.yaml_path, 'r') as f:
            config = yaml.safe_load(f)

        self.repo_owner = config['repository']['owner']
        self.repo_name = config['repository']['name']

        self.model_bucket_name = 'repo-models'
        self.emb_bucket_name = 'repo-embeddings'

        self.model_gcs_path = f'{self.repo_owner}/{self.repo_name}.model'
        self.labels_gcs_path = f'{self.repo_owner}/{self.repo_name}.labels'
        self.emb_gcs_path = f'{self.repo_owner}/{self.repo_name}'

        self.model_local_path = f'{self.repo_name}.dpkl'
        self.labels_local_path = f'{self.repo_name}.labels.dpkl'
        self.emb_local_path = f'{self.repo_name}.emb.dpkl'


if __name__ == '__main__':
    config = Config(yaml_path='issue_label_bot.yaml')
    print(config)
    print(config.__dict__)
