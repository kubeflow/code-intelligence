import os
import logging
from code_intelligence import github_app
import typing
import yaml

def get_issue_handle(installation_id, username, repository, number):
    "get an issue object."
    ghapp = github_app.GitHubApp.create_from_env()
    install = ghapp.get_installation(installation_id)
    return install.issue(username, repository, number)

def get_yaml(owner, repo, ghapp=None):
    """
    Looks for the yaml file in a /.github directory.

    yaml file must be named issue_label_bot.yaml
    """

    if not ghapp:
        # TODO(jlewi): Should we deprecate this code path and always pass
        # in the github app?
        ghapp = github_app.GitHubApp.create_from_env()

    try:
        # get the app installation handle
        inst_id = ghapp.get_installation_id(owner=owner, repo=repo)
        inst = ghapp.get_installation(installation_id=inst_id)
        # get the repo handle, which allows you got get the file contents
        repo = inst.repository(owner=owner, repository=repo)
        results = repo.file_contents('.github/issue_label_bot.yaml').decoded
    # TODO(jlewi): We should probably catching more narrow exceptions and
    # not swallowing all exceptions. The exceptions we should swallow are
    # the ones related to the configuration file not existing.
    except Exception as e:
        logging.info(f"Exception occured getting .github/issue_label_bot.yaml: {e}")
        return None

    return yaml.safe_load(results)

def build_issue_doc(org:str, repo:str, title:str, text:typing.List[str]):
    """Build a document string out of various github features.

    Args:
     org: The organization the issue belongs in
     repo: The repository.
     title: Issue title
     text: List of contents of the comments on the issue

    Returns:
     content: The document to classify
    """
    pieces = [title]
    pieces.append(f"{org.lower()}_{repo.lower()}")
    pieces.extend(text)
    content = "\n".join(pieces)
    return content
