import abc
import logging
import os

from collections import namedtuple, Counter
import datetime
from dateutil import parser as date_parser
from github3 import GitHub
from pathlib import Path
from cryptography.hazmat.backends import default_backend
import time
import json
import jwt
import requests
from tqdm import tqdm
from typing import List

class GitHubApp(GitHub):
    """
    This is a small wrapper around the github3.py library

    Provides some convenience functions for testing purposes.

    For reference on authenticating as a GitHub App see
    https://developer.github.com/apps/building-github-apps/authenticating-with-github-apps/#authenticating-as-an-installation

    Authenticating as a GitHub App works as follows

    1. We use the PEM key and App Id for the application to generate a JWT
    2. We us the JWT to make a request to the GitHub App to get the id
       for the installation of that App on a particular repository
       or organization
    3. We use the JWT for the GitHub App and the installation id to get
       an access token for the installation of the GitHub app on that
       org or repo
    4. We use the access token for that installation to perform actions on that
       repository or org as that GitHub App


    TODO(jlewi): This class should probably be refactored. We should
    probably separate out helper functions for specific methods
    (e.g. get_reactions) from utilities for authenticating as a GitHubApp

    We should probably create a helper class just for generating access
    tokens as a GitHub App. We should probably create a wrapper for tokens
    that automatically refreshes tokens when needed.
    """

    def __init__(self, pem_path, app_id):
        super().__init__()

        self.path = Path(pem_path)
        self.app_id = app_id

        if not self.path.is_file():
            raise ValueError(f'argument: `pem_path` must be a valid filename. {pem_path} was not found.')

        # Create a cache for installation ids. The key
        # is "{owner}/{repo}"
        self._installation_ids = {}

    @staticmethod
    def create_from_env():
        """Create a new instance based on environment variables."""
        app_id = os.getenv('GITHUB_APP_ID')
        key_file_path = os.getenv("GITHUB_APP_PEM_KEY")
        return GitHubApp(pem_path=key_file_path, app_id=app_id)

    def get_app(self):
        with open(self.path, 'rb') as key_file:
            client = GitHub()
            client.login_as_app(private_key_pem=key_file.read(),
                                app_id=self.app_id)
        return client

    def get_installation(self, installation_id):
        "login as app installation without requesting previously gathered data."
        logging.info("Logging in as GitHub App")
        with open(self.path, 'rb') as key_file:
            client = GitHub()
            client.login_as_app_installation(private_key_pem=key_file.read(),
                                             app_id=self.app_id,
                                             installation_id=installation_id)
        logging.info("Successfully logged in as GitHub App")
        return client

    def get_test_installation_id(self):
        "Get a sample test_installation id."
        client = self.get_app()
        return next(client.app_installations()).id

    def get_test_installation(self):
        "login as app installation with the first installation_id retrieved."
        return self.get_installation(self.get_test_installation_id())

    def get_test_repo(self):
        repo = self.get_all_repos(self.get_test_installation_id())[0]
        appInstallation = self.get_test_installation()
        owner, name = repo['full_name'].split('/')
        return appInstallation.repository(owner, name)

    def get_test_issue(self):
        test_repo = self.get_test_repo()
        return next(test_repo.issues())

    def get_jwt(self):
        """This is needed to retrieve the installation access token.

        Must call .decode() on returned object to get string.
        """
        now = self._now_int()
        payload = {
            "iat": now,
            "exp": now + (60),
            "iss": self.app_id
        }
        with open(self.path, 'rb') as key_file:
            private_key = default_backend().load_pem_private_key(key_file.read(), None)
            return jwt.encode(payload, private_key, algorithm='RS256')

    def get_installation_id(self, owner, repo):
        "https://developer.github.com/v3/apps/#find-repository-installation"
        key = f"{owner}/{repo}"
        if key not in self._installation_ids:
            logging.info(f"No installation id for {owner}/{repo} in cache")
            url = f'https://api.github.com/repos/{owner}/{repo}/installation'

            headers = {'Authorization': f'Bearer {self.get_jwt().decode()}',
                       'Accept': 'application/vnd.github.machine-man-preview+json'}

            response = requests.get(url=url, headers=headers)
            if response.status_code != 200:
                raise Exception(f"There was a problem requesting URL={URL} "
                                f"Status code : {response.status_code}, "
                                f"Response:{response.json()}")
            self._installation_ids[key] = response.json()['id']

        return self._installation_ids[key]

    def get_installation_access_token(self, installation_id):
        """"Get the installation access toke.

        Args:
          installation_id: The id for the install of the App on a particular
            repository or og.
        """

        url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
        headers = {'Authorization': f'Bearer {self.get_jwt().decode()}',
                   'Accept': 'application/vnd.github.machine-man-preview+json'}

        response = requests.post(url=url, headers=headers)
        if response.status_code != 201:
            raise Exception(f'Status code : {response.status_code}, {response.json()}')
        return response.json()['token']

    def get_repo_access_token(self, repo):
        """Get an access token for the specific repo.

        Args:
          repo: Id of the repo in format {owner}/{repo_name}
        """

        owner, name = repo.split("/")

        installation_id = self.get_installation_id(owner, repo)

        return self.get_installation_access_token(installation_id)

    def _extract(self, d, keys):
        "extract selected keys from a dict."
        return dict((k, d[k]) for k in keys if k in d)

    def _now_int(self):
        return int(time.time())

    def get_all_repos(self, installation_id):
        """Get all repos that this installation has access to.
        """
        url = 'https://api.github.com/installation/repositories'
        headers={'Authorization': f'token {self.get_installation_access_token(installation_id)}',
                 'Accept': 'application/vnd.github.machine-man-preview+json'}

        response = requests.get(url=url, headers=headers)

        if response.status_code >= 400:
            raise Exception(f'Status code : {response.status_code}, {response.json()}')

        fields = ['name', 'full_name', 'id']
        return [self._extract(x, fields) for x in response.json()['repositories']]

    def get_reactions(self, owner: str, repo: str, comment_id: int, iat: str):
        """Get a list of reactions.

        https://developer.github.com/v3/reactions/#list-reactions-for-a-commit-comment
        """
        url = f'https://api.github.com/repos/{owner}/{repo}/issues/comments/{comment_id}/reactions'
        # installation_id = self.get_installation_id(owner, repo)
        # headers={'Authorization': f'token {self.get_installation_access_token(installation_id)}',
        #          'Accept': 'application/vnd.github.squirrel-girl-preview+json'}
        headers={'Authorization': f'token {iat}',
                 'Accept': 'application/vnd.github.squirrel-girl-preview+json'}

        response = requests.get(url=url, headers=headers)

        if response.status_code >= 400:
            raise Exception(f'Status code : {response.status_code}, {response.json()}')

        results = [self._extract(x, ['content']) for x in response.json()]
        # count the reactions
        return Counter([x['content'] for x in results])


    @staticmethod
    def unpack_issues(client, owner, repo, label_only=True):
        """
        extract relevant data from issues.

        returns a list of namedtuples which contains the following fields:
            title: str
            number: int
            body: str
            labels: list
            url: str

        """
        Issue = namedtuple('Issue', ['title', 'number', 'body', 'labels', 'url'])

        issue_data = []
        issues = list(client.issues_on(owner, repo))
        for issue in tqdm(issues, total=len(issues)):
            labels=[label.name for label in issue.labels()]

            # if there are no labels, then optionally skip
            if label_only and not labels:
                continue

            issue_data.append(Issue(title=issue.title,
                                    number=issue.number,
                                    body=issue.body,
                                    labels=[label.name for label in issue.labels()],
                                    url=issue.html_url)
                              )
        return issue_data

    def generate_installation_curl(self, endpoint):
        iat = self.get_installation_access_token()
        print(f'curl -i -H "Authorization: token {iat}" -H "Accept: application/vnd.github.machine-man-preview+json" https://api.github.com{endpoint}')


# Tuple to represent a GitHub access token
GITHUB_ACCESS_TOKEN = namedtuple("GitHubAccessToken", ("token", "expires_at"))

class GitHubTokenGenerator(abc.ABC):
    """A class for generating GitHub access tokens."""

    @abc.abstractclassmethod
    def token(self):
        """Return an instance of GITHUB_ACCESS_TOKEN."""

    @abc.abstractclassmethod
    def auth_headers(self):
        """Generate headers to attach to GitHub API requests."""

class FixedAccessTokenGenerator(GitHubTokenGenerator):
    """Represent a constant access token.

    The primary use cases for this are personal access tokens.
    """
    def __init__(self):
        self._token = None

    @staticmethod
    def from_env():
        """Create the token from environment variables"""
        # INPUT_ prefix is used when this is run inside the context of a
        # GitHub Action
        TRIAGE_TOKEN = os.getenv("INPUT_GITHUB_PERSONAL_ACCESS_TOKEN",
                                 os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"))
        GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

        if not TRIAGE_TOKEN and not GITHUB_TOKEN :
            raise ValueError("GITHUB_PERSONAL_ACCESS_TOKEN or GITHUB_TOKEN "
                             "must be present as an environment variable upon "
                             "instantiating this object.")

        token = TRIAGE_TOKEN if TRIAGE_TOKEN else GITHUB_TOKEN

        # Set an expiration time really far in the future to indicate the
        # token never expires
        forever = datetime.datetime.now() + datetime.timedelta(weeks=52*2)
        self = FixedAccessTokenGenerator()
        self._token = GITHUB_ACCESS_TOKEN(token, forever)
        return self

    def token(self):
        return self._token

    def auth_headers(self):
        headers={'Authorization': f'token {self._token.token}',
                 'Accept': 'application/vnd.github.machine-man-preview+json'}

        return headers

class GitHubAppTokenGenerator:
    """A helper class for generating access tokens for installations.

    To Authenticate to GitHub Apps as the installation of that app on some
    repo we need to generate an access token.

    This class handles generating and refreshing those tokens.

    It provides convenience methods for generating the headers as well.
    """

    def __init__(self, app, repo,
                 min_expire_time=datetime.timedelta(minutes=5)):
        """Create a token generator.

        Args:
          app: Instance of GitHubApp
          repo: Repo in the form of {owner}/{name} on which to generate tokens
          min_expire_time: Minimum time until token expiration before we
            refresh.
        """

        self._token = None
        self._app = app
        self._repo = repo
        # Generate a fake expired token to force a refresh on first call
        self._token = GITHUB_ACCESS_TOKEN("", datetime.datetime.now())

    def token(self):
        """Return the access token."""

        now = datetime.datetime.now(tz=self._token.expires_at.tzinfo)
        if now > self._token.expires_at:
            logging.info(f"Refreshing access token")

            owner, name = self._repo.split("/")

            installation_id = self._app.get_installation_id(owner, name)

            url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
            headers = {'Authorization': f'Bearer {self._app.get_jwt().decode()}',
                       'Accept': 'application/vnd.github.machine-man-preview+json'}

            response = requests.post(url=url, headers=headers)
            if response.status_code != 201:
                raise Exception(f'Status code : {response.status_code}, {response.json()}')

            response_json = response.json()
            token = response_json['token']
            expires_at = date_parser.parse(response_json['expires_at'])
            self._token = GITHUB_ACCESS_TOKEN(token, expires_at)

        return self._token

    def auth_headers(self):
        """Generate headers to attach to GitHub API requests."""
        headers ={
            'Authorization': f'token {self.token().token}',
            'Accept': 'application/vnd.github.machine-man-preview+json'}
        return headers


