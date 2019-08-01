import pytest
# TODO: Use absolute import instead of relative import.
#       Should make a decision on what are top level python packages.
import sys
sys.path.insert(1, '../notebooks')

from mlp import MLPWrapper
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split

def test_predict_proba():
    n_classes = 5
    n_samples = 20
    embedding_size = 5
    random_state = 1234
    X_train = np.random.rand(n_samples, embedding_size)
    y_train = np.random.choice([0, 1], size=(n_samples, n_classes))
    X_test = np.random.rand(n_samples, embedding_size)

    mlp_clf = MLPClassifier(random_state=random_state)
    mlp_clf.fit(X_train, y_train)
    mlp_clf_pred = mlp_clf.predict_proba(X_test)

    mlp_wrap = MLPWrapper(clf=mlp_clf)
    mlp_wrap.fit(X_train, y_train)
    mlp_wrap_pred = mlp_wrap.predict_proba(X_test)
    assert mlp_clf_pred.all() == mlp_wrap_pred.all()


def test_find_probability_thresholds():
    X = np.array([
        [0.1, 0.1],
        [0.2, 0.2],
        [0.3, 0.3],
        [0.4, 0.4],
        [0.5, 0.5],
        [0.6, 0.6]
    ])
    y = np.array([
        [1, 0, 0],
        [1, 0, 0],
        [0, 1, 0],
        [0, 1, 0],
        [0, 0, 1],
        [0, 0, 1]
    ])
    random_state = 1234
    precision_threshold = 0.7
    recall_threshold = 0.5

    mlp_clf = MLPClassifier(random_state=random_state)

    mlp_wrap = MLPWrapper(clf=mlp_clf, precision_threshold=precision_threshold,
                          recall_threshold=recall_threshold)
    mlp_wrap.find_probability_thresholds(X, y)
    # thresholds is a dict {label_index: threshold}
    # if value of threshold is None, the label should not be predicted
    # because it does not meet the precision and recall thresholds
    thresholds = mlp_wrap.probability_thresholds
    precision_0, recall_0 = mlp_wrap.precisions[0], mlp_wrap.recalls[0]
    # in this case, only label 0 meets precision & recall thresholds
    assert not thresholds[1] and not thresholds[2] and\
        precision_0 >= precision_threshold and recall_0 >= recall_threshold
