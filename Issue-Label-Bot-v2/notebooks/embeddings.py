from bs4 import BeautifulSoup
import requests
from fastai.core import parallel, partial
from collections import Counter
from tqdm import tqdm
import torch
import pandas as pd
from inference import InferenceWrapper
from pathlib import Path
from urllib import request as request_url


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

def verify_issue(owner, repo, num):
    """
    Verify that owner/repo/issues/num exists.

    Returns
    -------
    bool
        True/False if issue exists.

    Note that pull requests are also issues but will
    get redirected with a status code 302, allowing
    this function to return False.
    """

    url = f'https://github.com/{owner}/{repo}/issues/{num}'

    if requests.head(url).status_code != 200:
        return False
    else:
        return True

def get_issue_text(num, idx, owner, repo, skip_issue=True):
    """
    Get the raw text of an issue body and label.

    Returns
    ------
    dict
        {'title':str, 'body':str}
    """
    url = f'https://github.com/{owner}/{repo}/issues/{num}'
    if not verify_issue(owner, repo, num):
        if skip_issue:
            return None
        raise Exception(f'{url} is not an issue.')

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
        return None

    return {'title':title,
            'url':url,
            'body': body,
            'labels': labels,
            'num': num}

def get_all_issue_text(owner, repo, inf_wrapper, workers=64):
    # prepare list of issue nums
    owner=owner
    repo=repo
    max_num = find_max_issue_num(owner, repo)

    get = partial(get_issue_text, owner=owner, repo=repo, skip_issue=True)
    issues = parallel(get, list(range(1, max_num+1)), max_workers=workers)
    # filter out issues with problems
    filtered_issues = []

    for issue in issues:
        if issue:
            filtered_issues.append(issue)

    print(f'Retrieved {len(filtered_issues)} issues.')

    features = []
    labels = []
    nums = []
    for issue in tqdm(filtered_issues):
        labels.append(issue['labels'])
        nums.append(issue['num'])
        # calculate embedding
        text = inf_wrapper.process_dict(issue)['text']
        feature = inf_wrapper.get_pooled_features(text).detach().cpu()
        # only need the first 1600 dimensions
        features.append(feature[:, :1600])

    assert len(features) == len(labels), 'Error you have mismatch b/w number of observations and labels.'

    return {'features':torch.cat(features).numpy(),
            'labels': labels,
            'nums': nums}

def pass_through(x):
    return x

def load_model_artifact():
    model_url = 'https://storage.googleapis.com/issue_label_bot/model/lang_model/models_22zkdqlr/trained_model_22zkdqlr.pkl'
    path = Path('./model_files')
    full_path = path/'model.pkl'

    if not full_path.exists():
        print('Loading model.')
        path.mkdir(exist_ok=True)
        request_url.urlretrieve(model_url, path/'model.pkl')
    return InferenceWrapper(model_path=path, model_file_name='model.pkl')


if __name__ == '__main__':
    test = get_all_issue_text(owner='kubeflow', repo='examples', inf_wrapper=load_model_artifact())
