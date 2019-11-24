from issue_triage.triage import IssueTriage
import os
import logging

PROJECT_CARD_ID = os.getenv('INPUT_PROJECT_CARD_ID')
ISSUE_NUMBER = os.getenv('INPUT_ISSUE_NUMBER')
REPO = os.getenv('GITHUB_REPOSITORY')

assert PROJECT_CARD_ID, "Input PROJECT_CARD_ID not supplied."
assert ISSUE_NUMBER, "Input ISSUE_NUMBER not supplied."
assert os.getenv("INPUT_PERSONAL_ACCESS_TOKEN"), "Must supply input PERSONAL_ACCESS_TOKEN for Action to Run."

if __name__ == '__main__':
    triager = IssueTriage()
    url = f"https://github.com/{REPO}/issues/{ISSUE_NUMBER}"
    logging.info(f'Triaging issue {ISSUE_NUMBER} - {url}')
    issue_info = triager.triage_issue(url)
    logging.info(issue_info)