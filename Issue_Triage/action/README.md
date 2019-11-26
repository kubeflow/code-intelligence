# Triage Issues For Kubeflow
A GitHub Action that automatically adds/removes issues from the Project [Needs Triage](https://github.com/orgs/kubeflow/projects/26)

* Kubeflow's triage criterion are defined in [issue_triage.md](https://github.com/kubeflow/community/blob/master/proposals/issue_triage.md) 

  * This doc provides more information about Kubeflow's process for triaging issues

* The code for actually triaging issues is in [triage.py](https://github.com/kubeflow/code-intelligence/blob/master/py/issue_triage/triage.py)

## Discussion

- [Notebook](https://github.com/kubeflow/code-intelligence/blob/master/Issue_Triage/notebooks/triage.ipynb) exploring ways to programatically triage issues.
- [Issue](https://github.com/kubeflow/community/issues/278) describing requirements for automatic triage.

# Usage

## Example Workflow

```yaml
name: Check Triage Status of Issue
on: 
  issues:
    types: [opened, closed, reopened, transferred, labeled, unlabeled]
    # Issue is created, Issue is closed, Issue added or removed from projects, Labels added/removed

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Update Kanban
        uses: kubeflow/code-intelligence/Issue_Triage/action@master
        with:
          NEEDS_TRIAGE_PROJECT_CARD_ID: 'MDEzOlByb2plY3RDb2x1bW41OTM0MzEz'
          ISSUE_NUMBER: ${{ github.event.issue.number }}
          GITHUB_PERSONAL_ACCESS_TOKEN: ${{ secrets.triage_projects_github_token }}
```

## Mandatory Inputs

1. **NEEDS_TRIAGE_PROJECT_CARD_ID**: The Project Card ID that you want to move issues to.  Defaults to `MDEzOlByb2plY3RDb2x1bW41OTM0MzEz`
2. **ISSUE_NUMBER**: The issue number in the current repo that you want to triage
3. **GITHUB_PERSONAL_ACCESS_TOKEN**: A personal access token with authorization to modify the project board.

### Installing the action on a repository

1. Create a workflow like the one above in your repository in the directory

   ```
   .github/workflows/
   ```

1. Create a secret for the repository called `triage_projects_github_token` which has a GitHub personal access token with the following permissions

   * admin:org read & write
     * Needed to modify projects

   * repo:public_repo
      * needed to see issues

1. Kubeflow repositories should use the personal access token **issue-triage** for the **kubeflow-bot** GitHub account

   * The access token is currently stored in Google's internal key management system
   * The google team has access and can add the key to repositories as necessary