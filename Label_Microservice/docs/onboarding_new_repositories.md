# Onboarding new repositories

2019-08-21

Authors: Chun-Hsiang Wang ([chunhsiang@google.com](mailto:chunhsiang@google.com))

[go/label-bot-onboarding](go/label-bot-onboarding)


# TL;DR

Currently, users install [GitHub issue label bot](https://github.com/marketplace/issue-label-bot) to their own repositories. The bot can predict three types of labels, questions, features and bugs, for each new issue of installed repositories. According to users’ suggestions, we create a new design of the [repository specific issue label bot](https://docs.google.com/document/d/1jXP0LjwWYJakKFkpvc2A_YT1E1HchBhgHEALmqsV2iM/edit) which is able to predict other labels specified by repo maintainers. We have a [rollout design](https://docs.google.com/document/d/1HoY7rNGlDj_W5U74Ax8DC4umqz5wrW4ef4SB64N3vN4/edit#) to replace the existing bot with the new one. And this doc describes how users train models, configure settings for precision and recall thresholds, and allow the new bot to work on their own repositories.

We describe how users need to do to move from existing issue label bot to the repository specific issue label bot.


# Steps for the installation of the repo-specific bot


## Step 1. Install issue label bot

According to the [installation instructions](https://github.com/marketplace/issue-label-bot) for the existing issue label bot, users can install the issue label bot to their repositories. After installing the bot, three types of labels, including questions, features and bugs, can be added to issues while new issues are filed in the installed repositories. For those users who want to use the repository specific issue label bot to predict labels for their repositories, they need to follow all other steps to finish the installation.


## Step 2. Train model on the repository

For repository specific issue label bot, we need to scrape all issues of repositories and train a model on each specific repository. To scrape issues from GitHub, we need to know the repository information including the owner and the name that users want to install the new issue label bot. Given the repository information, we will manually run the training pipeline created by Kubeflow Pipelines to scrape all issues of the repository and train an MLP classifier for it. All the results including embeddings, models and label columns of models will be stored in GCS.

In specific, we need to run the notebook file [Label_Microservice/notebooks/Training_Pipeline.ipynb](../notebooks/Training_Pipeline.ipynb) in the repository [kubeflow/code-intelligence](https://github.com/kubeflow/code-intelligence) in the kubeflow notebook servers. We only need to run the notebook starting from the section [Build pipeline](../notebooks/Training_Pipeline.ipynb#L388) to the end of the notebook and do not need to create the image using fairing again. We need to modify [the argument](../notebooks/Training_Pipeline.ipynb#L528) in the last cell, which should be the repository information, including repo owner and name, that we need to train a model on. For example, if we want to train a model on issues from `kubeflow/code-intelligence` repo, the argument should be specified as `arguments = {'owner': 'kubeflow', 'repo': 'code-intelligence'}`. After running the pipeline, the new model should be trained and stored in GCS.

Noted that those models trained in this step, precision and recall thresholds of them are set to default values, which are 0.7 and 0.5 respectively. We use these two thresholds to pick up probability thresholds for all labels.


## Step 3. Users put yaml config file

Users need to define their own yaml config files and put them to the path `.github/issue_label_bot.yaml` in their repositories. This yaml files configure the information that needs to be used when the issue label bot does label prediction.

The following is an example configuration in the yaml file,


```
predicted-labels:
    - area/tfjob
    - area/inference
    - area/kfctl
    - area/jupyter
    - area/front-end
    - area/docs
    - area/build-release
```


This file specifies the labels that are able to be predicted by the issue label bot for this repository. In this example, there are seven labels that users allow the bot to add to issues. All other labels will not be added to issues even though the predicted confidence of them are high enough. If users do not specify the `predicted-labels` in the yaml file, all labels which satisfy the probability thresholds will be added to issues.


