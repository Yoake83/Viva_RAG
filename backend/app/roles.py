"""Role catalogue. Roles pick which books are searched and which syllabus areas are probed."""
from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import ValidationFailed


@dataclass(frozen=True)
class FocusArea:
    id: str
    topic: str
    queries: tuple[str, ...]
    keywords: tuple[str, ...] = ()  # resume terms that count as evidence for this area


_AREAS = [
    FocusArea("bias_variance", "Bias-variance trade-off and generalization",
              ("bias variance tradeoff underfitting overfitting", "model complexity and generalization error")),
    FocusArea("regularization", "Regularization (L1, L2, dropout, early stopping)",
              ("regularization L1 L2 penalty to reduce overfitting", "dropout and early stopping"),
              ("regulariz", "dropout", "lasso", "ridge")),
    FocusArea("evaluation", "Model evaluation, metrics and validation",
              ("precision recall F1 confusion matrix", "cross-validation train validation test split", "ROC curve AUC"),
              ("metric", "precision", "recall", "f1", "auc", "cross-validation", "evaluation")),
    FocusArea("imbalanced", "Learning from imbalanced data",
              ("class imbalance oversampling undersampling", "cost-sensitive learning rare classes"),
              ("imbalanc", "fraud", "anomaly", "smote")),
    FocusArea("features", "Feature engineering and preprocessing",
              ("feature engineering one-hot encoding scaling normalization", "missing data imputation feature selection"),
              ("feature", "pandas", "preprocess", "etl", "data cleaning", "data analysis")),
    FocusArea("linear_models", "Linear and logistic regression",
              ("linear regression least squares", "logistic regression decision boundary"),
              ("regression", "scikit", "sklearn", "statsmodels")),
    FocusArea("trees_ensembles", "Decision trees and ensemble methods",
              ("decision tree splitting criterion", "random forest bagging boosting gradient boosting"),
              ("xgboost", "lightgbm", "random forest", "boosting", "decision tree", "catboost")),
    FocusArea("svm", "Support vector machines and kernels",
              ("support vector machine margin kernel trick",), ("svm", "kernel")),
    FocusArea("neural_nets", "Neural networks and backpropagation",
              ("neural network backpropagation activation functions", "deep learning layers weight initialization"),
              ("neural", "pytorch", "tensorflow", "keras", "deep learning", "transformer")),
    FocusArea("optimization", "Gradient descent and optimization",
              ("gradient descent learning rate convergence", "stochastic gradient descent mini-batch"),
              ("gradient", "optimi", "adam", "sgd")),
    FocusArea("cnn_rnn", "Convolutional and sequence models",
              ("convolutional neural network filters pooling", "recurrent neural network LSTM sequences"),
              ("cnn", "computer vision", "opencv", "image", "rnn", "lstm", "nlp")),
    FocusArea("unsupervised", "Clustering and dimensionality reduction",
              ("k-means clustering", "principal component analysis dimensionality reduction"),
              ("cluster", "pca", "k-means", "unsupervised")),
    FocusArea("hyperparameters", "Hyperparameter tuning and model selection",
              ("hyperparameter tuning grid search random search", "model selection with a validation set"),
              ("hyperparameter", "grid search", "optuna", "tuning")),
    FocusArea("probabilistic", "Probabilistic and Bayesian learning",
              ("bayes theorem naive bayes classifier", "maximum likelihood estimation Bayesian inference"),
              ("bayes", "probabilistic", "likelihood")),
    FocusArea("learning_theory", "Learning theory and inductive bias",
              ("PAC learning sample complexity VC dimension", "inductive bias and hypothesis space")),
    FocusArea("efficiency", "Scaling and efficiency of learning algorithms",
              ("algorithmic efficiency training time scalability", "large datasets parallelization"),
              ("scal", "distributed", "spark", "latency", "inference", "fastapi", "docker", "kubernetes")),
    FocusArea("transfer", "Transfer learning and pretrained models",
              ("transfer learning fine-tuning pretrained models", "domain adaptation"),
              ("fine-tun", "transfer", "pretrained", "bert", "llm", "huggingface")),
    FocusArea("knn", "Nearest neighbours and instance-based learning",
              ("k-nearest neighbors distance metric", "instance-based learning"), ("knn", "nearest")),
    FocusArea("embeddings", "Representation learning and embeddings",
              ("word embeddings representation learning", "dense vector representations of text"),
              ("embedding", "word2vec", "rag", "vector", "nlp", "llm")),
]
FOCUS_AREAS = {a.id: a for a in _AREAS}


@dataclass(frozen=True)
class Role:
    id: str
    label: str
    tagline: str
    description: str
    focus: tuple[str, ...]

    def focus_areas(self) -> list[FocusArea]:
        return [FOCUS_AREAS[i] for i in self.focus]


ROLES: dict[str, Role] = {
    r.id: r
    for r in [
        Role("ai_ml_engineer", "AI/ML Engineer", "Models, training and deep learning fundamentals",
             "Builds and trains models. Probed on learning fundamentals, neural networks, optimization and evaluation.",
             ("bias_variance", "neural_nets", "optimization", "evaluation", "regularization", "cnn_rnn",
              "transfer", "features", "trees_ensembles", "unsupervised", "efficiency", "embeddings")),
        Role("data_scientist", "Data Scientist (Applied ML)", "Features, evaluation and applied modelling",
             "Turns messy data into dependable models. Probed on preprocessing, validation and classical algorithms.",
             ("features", "evaluation", "linear_models", "trees_ensembles", "imbalanced", "hyperparameters",
              "bias_variance", "regularization", "unsupervised", "svm", "knn")),
        Role("ml_backend_engineer", "ML Backend Engineer", "Serving, scaling and keeping models honest",
             "Ships ML behind services. Probed on evaluation discipline, efficiency and the practical side of training.",
             ("evaluation", "efficiency", "bias_variance", "features", "trees_ensembles", "neural_nets",
              "hyperparameters", "imbalanced", "transfer", "optimization")),
        Role("ml_researcher", "ML Researcher (Theory)", "Probabilistic and theoretical foundations",
             "Reasons about why learning works. Probed on theory, probabilistic methods and optimization.",
             ("learning_theory", "probabilistic", "bias_variance", "svm", "regularization", "optimization",
              "neural_nets", "unsupervised", "linear_models", "evaluation")),
    ]
}


def get_role(role_id: str) -> Role:
    role = ROLES.get(role_id)
    if not role:
        raise ValidationFailed(f"Unknown role '{role_id}'.", code="unknown_role", details={"roles": list(ROLES)})
    return role
