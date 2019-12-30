#!/usr/bin/python
"""A script to create the required secrets in one namespace by copying them
from another namespace
"""

import fire
from google.cloud import storage
import logging
import subprocess

class SecretCreator:
  @staticmethod
  def create_dev():
    """Create the dev version of the secrets."""
    bucket_name = "issue-label-bot-dev_secrets"
    blob_name = "kf-label-bot-dev.2019-12-30.private-key.pem"

    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    contents = blob.download_as_string().decode()

    subprocess.check_call(["kubectl", "create", "secret", "generic",
                           "github-app",
                           f"--from-literal=kf-label-bot-dev.private-key.pem="
                           f"{contents}"])

if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO,
                      format=('%(levelname)s|%(asctime)s'
                              '|%(message)s|%(pathname)s|%(lineno)d|'),
                      datefmt='%Y-%m-%dT%H:%M:%S',
                      )

  fire.Fire(SecretCreator)
