import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from backend.adapters.tabpfn_adapter import ModelUnavailable

NEVER_SEEN_FILL = 10.0  # logistic regression only: imputes years_since_last for never-seen topics


def rank(scores: pd.Series) -> list:
    """Deterministic ranking: score desc, topic_id asc."""
    return sorted(scores.index, key=lambda t: (-float(scores[t]), str(t)))


def score_naive_frequency(X): return X["total_occ"]
def score_recency_weighted(X): return X["recency_score"]


def score_logreg(Xtr, ytr, Xte) -> pd.Series:
    if ytr.nunique() < 2:
        raise ModelUnavailable("single_class", "training labels contain a single class")
    m = make_pipeline(SimpleImputer(strategy="constant", fill_value=NEVER_SEEN_FILL), StandardScaler(),
                      LogisticRegression(C=0.5, max_iter=1000, random_state=0))
    m.fit(Xtr, ytr)
    return pd.Series(m.predict_proba(Xte)[:, 1], index=Xte.index)


def random_rankings(topic_ids, seeds):
    for s in seeds:
        yield list(np.random.default_rng(s).permutation(list(topic_ids)))
