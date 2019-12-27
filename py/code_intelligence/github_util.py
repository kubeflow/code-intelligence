import os
import logging
from code_intelligence.github_app import GitHubApp
import yaml


def init():
    "Load all necessary artifacts to make predictions."
    #save keyfile
    pem_string = os.getenv('PRIVATE_KEY')
    if not pem_string:
        raise ValueError('Environment variable PRIVATE_KEY was not supplied.')

    with open('private-key.pem', 'wb') as f:
        f.write(str.encode(pem_string))

# TODO(jlewi): init is taking the PRIVATE_KEY from an environment variable
# and then writing it to a file. It would probably be better to follow
# the pattern of GOOGLE_APPLICATION_CREDENTIALS; i.e. mount the K8s secret
# to a volume and then use an environment variable to specify the path of
# the key file.
def get_app():
    "grab a fresh instance of the app handle."
    app_id = os.getenv('APP_ID')
    key_file_path = 'private-key.pem'
    ghapp = GitHubApp(pem_path=key_file_path, app_id=app_id)
    return ghapp

def get_issue_handle(installation_id, username, repository, number):
    "get an issue object."
    ghapp = get_app()
    install = ghapp.get_installation(installation_id)
    return install.issue(username, repository, number)

def get_yaml(owner, repo):
    """
    Looks for the yaml file in a /.github directory.

    yaml file must be named issue_label_bot.yaml
    """
    ghapp = get_app()
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
