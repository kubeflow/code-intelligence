"""This module contains utilities for working with GitHub's graphql API"""

import os
import requests

class GraphQLClient(object):
  """A graphql client for GitHub"""

  def __init__(self):
    if not os.getenv("GITHUB_TOKEN"):
      raise ValueError("GITHUB_TOKEN must be provided")
    self._headers = {"Authorization":
                     "Bearer {0}".format(os.getenv("GITHUB_TOKEN"))}

  def run_query(self, query):
    """Issue the GraphQL query and return the results."""
    request = requests.post('https://api.github.com/graphql',
                            json={'query': query}, headers=self._headers)
    if request.status_code == 200:
      return request.json()
    else:
      raise Exception("Query failed to run by returning code of {}. {}".format(
        request.status_code, query))