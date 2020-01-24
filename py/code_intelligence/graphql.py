"""This module contains utilities for working with GitHub's graphql API"""
from code_intelligence import github_app
from code_intelligence import util
import logging
import json
import os
import requests
import traceback

class GraphQLClient(object):
  """A graphql client for GitHub"""

  def __init__(self, headers=None):
    """Create a GraphQL Client

    Args:
      headers: (func () -> dict) Generate headers to be added to the
       requests. This can be used to generate authorization tokens.
       A commone use case is an instance of
       FixedAccessTokenGenerator.auth_headers
    """
    if headers is None:

      # INPUT_ prefix is used when this is run inside the context of a GitHub Action
      TRIAGE_TOKEN = os.getenv("INPUT_GITHUB_PERSONAL_ACCESS_TOKEN",
                               os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"))
      GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()

      if TRIAGE_TOKEN or GITHUB_TOKEN :
        logging.warning(f"GraphQLClient is defaulting to "
                         "FixedAccessTokenGenerator based on environment "
                         "variables. This is deprecated. Caller should "
                         "explicitly pass in a instance via header_generator. "
                         f"Traceback:\n{traceback.extract_stack}")


        headers = github_app.FixedAccessTokenGenerator.from_env().auth_headers

    self._headers = headers

  def run_query(self, query, variables=None, headers=None):
    """Issue the GraphQL query and return the results.

    Args:
     query: String containing the query
     variables: Dictionary of variables
     headers: (func () -> dict) Generate headers to be added to the
       requests. This can be used to generate authorization tokens.
       A commone use case is an instance of
       FixedAccessTokenGenerator.auth_headers
    """
    payload = {'query': query}

    if variables:
      payload["variables"] = variables

    header_values = {}
    if self._headers:
      header_values.update(self._headers())

    if headers:
      header_values.update(headers())

    request = requests.post('https://api.github.com/graphql',
                            json=payload, headers=header_values)
    if request.status_code == 200:
      return request.json()
    else:

      raise Exception("Query failed to run by returning code of {}. {}".format(
        request.status_code, query))

def unpack_and_split_nodes(data, path):
  """Unpack a list of results

  Args:
    data: A dictionary containing the results
    path: A list of fields indicating the fields to select.
      final one should be a list of nodes

  Returns:
    issues: A list of dicts; each dict is the data for some of
    the results
  """

  children = [data]

  for i, f in enumerate(path):
    last_child = children[-1]
    if not f in last_child:
      # If there are no edges then the field will not exist
      return []
    children.append(last_child.get(f))


  child = children[-1]

  items = []
  for i in child:
    items.append(i["node"])

  return items

class ShardWriter(object):
  """Write items as a set of file shards"""

  def __init__(self, total_shards, output_dir, prefix="items"):
    self.output_dir = output_dir
    self.total_shards = total_shards
    self.shard = 0
    self.prefix = prefix

  def write_shard(self, items):
    """Write the shard"""
    shard_file = os.path.join(
      self.output_dir,
      self.prefix + "-{0:03d}-of-{1:03d}.json".format(
        self.shard, self.total_shards))
    with open(shard_file, "w") as hf:
      hf.write(json.dumps(items, indent=2))
    self.shard += 1
