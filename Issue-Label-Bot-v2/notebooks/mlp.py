from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_recall_curve
import dill as dpickle
import numpy as np
import pandas as pd
import logging


class MLPWrapper:
    """Wrapper for Multi-Layer Perceptron classifier"""
    def __init__(self,
                 activation='relu',
                 alpha=0.0001,
                 clf=None,
                 early_stopping=True,
                 epsilon=1e-08,
                 hidden_layer_sizes=(100,),
                 learning_rate='constant',
                 learning_rate_init=0.001,
                 max_iter=500,
                 model_file="model.dpkl",
                 momentum=0.9,
                 n_iter_no_change=5,
                 precision_threshold=0.7,
                 random_state=1234,
                 recall_threshold=0.5,
                 solver='adam',
                 validation_fraction=0.1):
        """Initialize parameters of the MLP classifier
        Args:
          clf: MLPClassifier object for testing
          model_file: the local path to save or load model
          precision_threshold: the threshold that the precision of one label must meet in order to be predicted
          recall_threshold: the threshold that the recall of one label must meet in order to be predicted
        """
        if clf:
            self.clf = clf
        else:
            self.clf = MLPClassifier(activation=activation,
                                     alpha=alpha,
                                     early_stopping=early_stopping,
                                     epsilon=epsilon,
                                     hidden_layer_sizes=hidden_layer_sizes,
                                     learning_rate=learning_rate,
                                     learning_rate_init=learning_rate_init,
                                     max_iter=max_iter,
                                     momentum=momentum,
                                     n_iter_no_change=n_iter_no_change,
                                     random_state=random_state,
                                     solver=solver,
                                     validation_fraction=validation_fraction)
        self.model_file = model_file
        self.precision_threshold = precision_threshold
        self.recall_threshold = recall_threshold

        self.exclusion_list = None
        self.precisions = None
        self.probability_thresholds = None
        self.recalls = None
        self.total_labels = None

    def fit(self, X, y):
        """Train the classifier
        Args:
          X: features, numpy.array
          y: labels, numpy.array
        """
        self.clf.fit(X, y)

    def predict_proba(self, X):
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
        y_pred = self.predict_proba(X_test)

        self.probability_thresholds = {}
        self.precisions = {}
        self.recalls = {}
        self.total_labels = len(y_test[0])
        for label in range(self.total_labels):
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
            # if best_threshold is None, do not predict this label always
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
        with open(self.model_file, 'rb') as f:
            self.clf = dpickle.load(f)
