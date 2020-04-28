from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_recall_curve
from sklearn.metrics import roc_auc_score

import os
import dill as dpickle
import numpy as np
import pandas as pd
import logging


class MLPWrapper:
    """Wrapper for Multi-Layer Perceptron classifier"""
    def __init__(self,
                 clf,
                 model_file="model.dpkl",
                 precision_threshold=0.7,
                 recall_threshold=0.5,
                 load_from_model=False):
        """Initialize parameters of the MLP classifier
        Args:
          clf: a sklearn.neural_network.MLPClassifier object
          model_file: the local path to save or load model
          precision_threshold: the threshold that the precision of one label must meet in order to be predicted
          recall_threshold: the threshold that the recall of one label must meet in order to be predicted
          load_from_model: load classifier from model file or not
        """
        if clf:
            self.clf = clf
        elif load_from_model:
            self.load_model(model_file=model_file)
        else:
            raise Exception("You need to pass a MLPClassifier object to the wrapper")
        self.model_file = model_file
        self.precision_threshold = precision_threshold
        self.recall_threshold = recall_threshold

        # precisions/probability_thresholds/recalls are dict
        # {label_index: number or None}
        self.precisions = None
        self.probability_thresholds = None
        self.recalls = None
        # count of labels
        self.total_labels_count = None

    def fit(self, X, y):
        """Train the classifier
        Args:
          X: features, numpy.array
          y: labels, numpy.array
        """
        self.clf.fit(X, y)

    def predict_probabilities(self, X):
        """Predict probabilities of all labels for data
        Args:
          X: features, numpy.array

        Return: a list, shape (n_samples, n_classes)
        """
        return self.clf.predict_proba(X)

    def find_probability_thresholds(self, X, y, test_size=0.3):
        """Split the dataset into training and testing to find probability thresholds for all labels
        Args:
          X: features, numpy.array
          y: labels, numpy.array
        """
        # split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=1234)
        self.fit(X_train, y_train)
        y_pred = self.predict_probabilities(X_test)

        self.probability_thresholds = {}
        self.precisions = {}
        self.recalls = {}
        self.total_labels_count = len(y_test[0])
        for label in range(self.total_labels_count):
            # find the probability for each label
            best_precision, best_recall, best_threshold = 0.0, 0.0, None
            precision, recall, threshold = precision_recall_curve(np.array(y_test)[:, label], y_pred[:, label])
            for prec, reca, thre in zip(precision[:-1], recall[:-1], threshold):
                # precision, recall must meet two thresholds respecitively
                if prec >= self.precision_threshold and reca >= self.recall_threshold:
                    # choose the threshold with the higher precision
                    if prec > best_precision:
                        best_precision = prec
                        best_recall = reca
                        best_threshold = thre
            # self.probability_thresholds is a dict {label_index: probability_threshold}
            # If probability_thresholds[label] is None, do not predict this label always, which
            # means this label is in the excluded list because it does not satisfy
            # both of the precision and recall thresholds
            self.probability_thresholds[label] = best_threshold
            self.precisions[label] = best_precision
            self.recalls[label] = best_recall

    def grid_search(self, params=None, cv=5, n_jobs=-1):
        """Grid search to find the parameters for the best classifier
        Args:
          params: parameter settings to try
                  a dict with param names as keys and lists of settings as values
          cv: cross-validation splitting strategy, int
          n_jobs: number of jobs to run in parallel, int or None
        """
        if not params:
            # default parameters to try
            params = {'hidden_layer_sizes': [(100,), (200,), (400, ), (50, 50), (100, 100), (200, 200)],
                      'alpha': [.001, .01, .1, 1, 10],
                      'learning_rate': ['constant', 'adaptive'],
                      'learning_rate_init': [.001, .01, .1]}
        self.clf = GridSearchCV(self.clf, params, cv=cv, n_jobs=n_jobs)

    def save_model(self, model_file=None):
        """Save the model to the local path
        Args:
          model_file: The local path to save the model, str or None
                      if None, use the property of this class.
        """
        if model_file:
            self.model_file = model_file
        with open(self.model_file, 'wb') as f:
            dpickle.dump(self.clf, f)

    def load_model(self, model_file=None):
        """Load the model from the local path
        Args:
          model_file: The local path to load the model, str or None
                      if None, use the property of this class.
        """
        if model_file:
            self.model_file = model_file
        if not os.path.exists(self.model_file):
            raise Exception("Model path {self.model_file} does not exist")
        with open(self.model_file, 'rb') as f:
            self.clf = dpickle.load(f)

def calculate_auc(predictions, y_holdout, label_columns):
    """Calculate AUC.
    
    Args:
      Predictions: num_samples x num_features array
      y_holdout: Labels "one" hot encoded; num_samples x num_labels
      label_columns: List of labels
    """
    auc_scores = []
    counts = []

    for i, l in enumerate(label_columns):
        y_hat = predictions[:, i]
        y = y_holdout[:, i]
        auc = roc_auc_score(y_true=y, y_score=y_hat)
        auc_scores.append(auc)
        
    counts = y_holdout.sum(axis=0)
    
    df = pd.DataFrame({'label': label_columns, 'auc': auc_scores, 'count': counts})    
    display(df)
    weightedavg_auc = df.apply(lambda x: x.auc * x['count'], axis=1).sum() / df['count'].sum()
    print(f'Weighted Average AUC: {weightedavg_auc}')
    return df, weightedavg_auc            