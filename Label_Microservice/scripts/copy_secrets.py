#!/usr/bin/python
"""A script to create the required secrets in one namespace by copying them
from another namespace
"""

raise NotImplementedError("Not implemented")
import fire
import logging
import subprocess

class SecretCopier:
  def copy(self, target_namespace):
    NAMESPACE=<new kubeflow namespace>
    SOURCE=kubeflow
    NAME=user-gcp-sa
    SECRET=$(kubectl -n ${SOURCE} get secrets ${NAME} -o jsonpath="{.data.${NAME}\.json}" | base64 -d)

if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO,
                      format=('%(levelname)s|%(asctime)s'
                              '|%(message)s|%(pathname)s|%(lineno)d|'),
                      datefmt='%Y-%m-%dT%H:%M:%S',
                      )

  fire.Fire(SecretCopier)
