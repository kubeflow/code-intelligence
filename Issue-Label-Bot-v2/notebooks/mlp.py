from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import roc_auc_score
import dill as dpickle
import numpy as np
import pandas as pd


class MLP:
    def __init__(self,
                 activation='relu',
                 alpha=0.0001,
                 counter=None,  # for calculate auc
                 early_stopping=True,
                 epsilon=1e-08,
                 hidden_layer_sizes=(100,),
                 label_columns=None,
                 learning_rate='constant',
                 learning_rate_init=0.001,
                 max_iter=500,
                 model_file="model.dpkl",
                 momentum=0.9,
                 n_iter_no_change=5,
                 precision_thre=0.7,
                 prob_thre=0.0,
                 random_state=1234,
                 recall_thre=0.5,
                 solver='adam',
                 validation_fraction=0.1):
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
        self.precision_thre = precision_thre
        self.prob_thre = prob_thre
        self.recall_thre = recall_thre
        self.counter = counter
        self.label_columns = label_columns
        self.precision = None
        self.recall = None
        self.exclusion_list = None

    def fit(self, X, y):
        self.clf.fit(X, y)

    def predict_proba(self, X):
        return self.clf.predict_proba(X)

    def calculate_auc(self, y_holdout, predictions):
        if not self.counter or not self.label_columns:
            raise Exception('Need to set counter and label columns to calculate AUC')
        auc_scores = []
        counts = []

        for i, l in enumerate(self.label_columns):
            y_hat = predictions[:, i]
            y = y_holdout[:, i]
            auc = roc_auc_score(y_true=y, y_score=y_hat)
            auc_scores.append(auc)
            counts.append(self.counter[l])

        df = pd.DataFrame({'label': self.label_columns,
                           'auc': auc_scores,
                           'count': counts})
        weightedavg_auc = df.apply(lambda x: x.auc * x['count'], axis=1).sum() / df['count'].sum()
        print(f'Weighted Average AUC: {weightedavg_auc}')
        return df, weightedavg_auc

    def calculate_max_range_count(self, prob):
        thresholds_lower = [0.1 * i for i in range(11)]
        thresholds_upper = [0.1 * (i+1) for i in range(10)] + [1]
        max_range_count = [0] * 11  # [0,0.1), [0.1,0.2), ... , [0.9,1), [1,1]
        for i in prob:
            max_range_count[int(max(i) // 0.1)] += 1

        df = pd.DataFrame({'l': thresholds_lower,
                           'u': thresholds_upper,
                           'count': max_range_count})
        return df, max_range_count

    def calculate_result(self, y_true, y_pred, prob_thre=None):
        if prob_thre:
            self.prob_thre = prob_thre

        total_true = np.array([0] * len(y_pred[0]))
        total_pred_true = np.array([0] * len(y_pred[0]))
        pred_correct = np.array([0] * len(y_pred[0]))
        for i in range(len(y_pred)):
            y_true_label = np.where(y_true[i] == 1)[0]
            total_true[y_true_label] += 1

            y_pred_true = np.where(y_pred[i] >= self.prob_thre)[0]
            total_pred_true[y_pred_true] += 1

            for j in y_true_label:
                if j in y_pred_true:
                    pred_correct[j] += 1

        self.precision = pred_correct / total_pred_true
        self.recall = pred_correct / total_true

        df = pd.DataFrame({'label': self.label_columns,
                           'precision': self.precision,
                           'recall': self.recall})
        return df, self.precision, self.recall

    def find_best_prob_thre(self, y_true, y_pred):
        best_prob_thre = 0
        prec_count = 0
        reca_count = 0

        print(f'Precision threshold: {self.precision_thre}\nRecall threshold:{self.recall_thre}')
        thre = 0.0
        while thre < 1:
            _, prec, reca = self.calculate_result(y_true, y_pred, prob_thre=thre)

            pc = 0
            for p in prec:
                if p >= self.precision_thre:
                    pc += 1
            rc = 0
            for r in reca:
                if r >= self.recall_thre:
                    rc += 1

            if pc > prec_count or pc == prec_count and rc >= reca_count:
                best_prob_thre = thre
                prec_count = pc
                reca_count = rc
            thre += 0.1

        self.best_prob_thre = best_prob_thre
        print(f'Best probability threshold: {best_prob_thre},\n{min(prec_count, reca_count)} labels meet both of the precision threshold and the recall threshold')

    def get_exclusion_list(self):
        assert len(self.precision) == len(self.recall)
        self.exclusion_list = []

        for p, r, label in zip(self.precision, self.recall, self.label_columns):
            if p < self.precision_thre or r < self.recall_thre:
                self.exclusion_list.append(label)
        return self.exclusion_list

    def grid_search(self, params, cv=5, n_jobs=-1):
        self.clf = GridSearchCV(self.clf, params, cv=cv, n_jobs=n_jobs)

    def save_model(self, model_file=None):
        if model_file:
            self.model_file = model_file
        with open(self.model_file, 'wb') as f:
            dpickle.dump(self.clf, f)

    def load_model(self, model_file=None):
        if model_file:
            self.model_file = model_file
        with open(self.model_file, 'rb') as f:
            self.clf = dpickle.load(f)
