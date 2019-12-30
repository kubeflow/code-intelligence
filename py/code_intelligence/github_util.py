import os
import logging
from code_intelligence import github_app
import yaml

def get_issue_handle(installation_id, username, repository, number):
    "get an issue object."
    ghapp = github_app.GitHubApp.create_from_env()
    install = ghapp.get_installation(installation_id)
    return install.issue(username, repository, number)

def get_yaml(owner, repo):
    """
    Looks for the yaml file in a /.github directory.

    yaml file must be named issue_label_bot.yaml
    """
    ghapp = github_app.GitHubApp.create_from_env()
    try:
        # get the app installation handle
        inst_id = ghapp.get_installation_id(owner=owner, repo=repo)
        inst = ghapp.get_installation(installation_id=inst_id)
        # get the repo handle, which allows you got get the file contents
        repo = inst.repository(owner=owner, repository=repo)
        results = repo.file_contents('.github/issue_label_bot.yaml').decoded
    except:
        return None

    return yaml.safe_load(results)
