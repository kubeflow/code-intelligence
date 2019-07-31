"""This module contains utilities for working with GitHub's graphql API"""
from code_intelligence import util
import logging
import os
import requests

class GraphQLClient(object):
  """A graphql client for GitHub"""

  def __init__(self):
    if not os.getenv("GITHUB_TOKEN"):
      raise ValueError("GITHUB_TOKEN must be present as an environment variable upon instantiating this object.")
    self._headers = {"Authorization":
                     "Bearer {0}".format(os.getenv("GITHUB_TOKEN"))}

  def run_query(self, query, variables=None):
    """Issue the GraphQL query and return the results.

    Args:
     query: String containing the query
     variables: Dictionary of variables
    """
    payload = {'query': query}

    if variables:
      payload["variables"] = variables

    request = requests.post('https://api.github.com/graphql',
                            json=payload, headers=self._headers)
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
    util.write_items_to_json(shard_file, items)
    self.shard += 1