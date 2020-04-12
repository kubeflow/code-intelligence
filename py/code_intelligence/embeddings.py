from bs4 import BeautifulSoup
import requests
from fastai.core import parallel, partial
from collections import Counter
from tqdm import tqdm
import torch
import pandas as pd
from code_intelligence.inference import InferenceWrapper
from pathlib import Path
from urllib import request as request_url
import logging


def find_max_issue_num(owner, repo):
    """
    Find the maximum issue number associated with a repo.

    Returns
    -------
    int
        the highest issue number associated with this repo.
    """
    url = f'https://github.com/{owner}/{repo}/issues'
    r = requests.get(url)
    if not r.ok:
        r.raise_for_status()
    soup = BeautifulSoup(r.content, 'html.parser')
    # get grey text under issue preview cards
    issue_meta = soup.find('span', class_="opened-by").text
    # parse the first issue number visible, which is also the highest issue number
    issue_num = issue_meta.strip().split('\n')[0][1:]
    return int(issue_num)

# TODO(jlewi): Looks like idx isn't used can we remove it?
# TODO(https://github.com/kubeflow/code-intelligence/issues/126): Should we use the GitHub API rather than using the web?
def get_issue_text(num, idx, owner, repo, skip_issue=True):
    """
    Get the raw text of an issue body and label.

    Returns
    ------
    dict
        {'title':str, 'body':str}
    """
    url = f'https://github.com/{owner}/{repo}/issues/{num}'
    status_code = requests.head(url).status_code
    if status_code != 200:
        if skip_issue:
            return None
        raise Exception(f'Status code is {status_code} not 200:\n'
                        '{url} is not an issue.\n'
                        'Note: status code is 302 if it is a pull request')

    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    title_find = soup.find("span", class_="js-issue-title")
    body_find = soup.find("td", class_="js-comment-body")
    label_find = soup.find(class_='js-issue-labels')

    if not title_find or not body_find:
        return None

    title = title_find.get_text().strip()
    body = body_find.get_text().strip()
    labels = label_find.get_text().strip().split('\n')

    if labels[0] == 'None yet':
        # return issues even though they haven't been labeled
        labels = []

    return {'title':title,
            'url':url,
            'body': body,
            'labels': labels,
            'num': num}

# TODO(https://github.com/kubeflow/code-intelligence/issues/126): This function should replace
# get_issue_text
def get_issue(url, gh_client):
  """Fetch the issue data using GraphQL
  
  Args:
    url: Url of the GitHub isue to fetch
    gh_client: GitHub GraphQl client.
    
  Returns
    ------
    dict
        {'title':str, 'body':str}
  """
  issue_query = """query getIssue($url: URI!) {
  resource(url: $url) {
    __typename
    ... on Issue {
      author {
        __typename
        ... on User {
          login
        }
        ... on Bot {
          login
        }
      }
      id
      title
      body
      url
      state
      labels(first: 30) {
        totalCount
        edges {
          node {
            name
          }
        }
      }
    }
  }
}"""

  variables = {
          "url": url,
  }
  issue_results = gh_client.run_query(issue_query, variables)
  
  if "errors" in issue_results:
    logging.error(f"There was a problem running the github query; {issue_results['errors']}")
    raise ValueError(f"There was a problem running the github query: {issue_results['errors']}")
  return issue_results["data"]["resource"]
  
def get_all_issue_text(owner, repo, inf_wrapper, workers=64):
    """
    Prepare embedding features of all issues in a given repository.

    Returns
    ------
    dict
        {'features':list, 'labels':list, 'nums':list}
    """
    # prepare list of issue nums
    max_num = find_max_issue_num(owner, repo)

    get = partial(get_issue_text, owner=owner, repo=repo, skip_issue=True)
    issues = parallel(get, list(range(1, max_num+1)), max_workers=workers)
    # filter out issues with problems
    filtered_issues = []

    if not issues:
      raise ValueError(f"No issues retrieved for {owner}/{repo}")
    for issue in issues:
        if issue:
            filtered_issues.append(issue)

    logging.info(f'Repo {owner}/{repo} Retrieved {len(filtered_issues)} issues.')

    features = []
    labels = []
    nums = []
    issues_dict = {'title': [], 'body': []}
    for issue in tqdm(filtered_issues):
        labels.append(issue['labels'])
        nums.append(issue['num'])
        issues_dict['title'].append(issue['title'])
        issues_dict['body'].append(issue['body'])

    features = inf_wrapper.df_to_embedding(pd.DataFrame.from_dict(issues_dict))

    assert len(features) == len(labels), 'Error you have mismatch b/w number of observations and labels.'

    return {'features': features[:, :1600],
            'labels': labels,
            'nums': nums}

def pass_through(x):
    """Avoid messages when the model is deserialized in fastai library."""
    return x

def load_model_artifact(model_url):
    """
    Download the pretrained language model from URL
    Args:
      model_url: URL to store the pretrained model

    Returns
    ------
    InferenceWrapper
        a wrapper for a Learner object in fastai.
    """
    path = Path('./model_files')
    full_path = path/'model.pkl'

    if not full_path.exists():
        logging.info('Loading model.')
        path.mkdir(exist_ok=True)
        request_url.urlretrieve(model_url, path/'model.pkl')
    return InferenceWrapper(model_path=path, model_file_name='model.pkl')


if __name__ == '__main__':
    test = get_all_issue_text(owner='kubeflow', repo='examples',
        inf_wrapper=load_model_artifact('https://storage.googleapis.com/issue_label_bot/model/lang_model/models_22zkdqlr/trained_model_22zkdqlr.pkl'))
