"""Single feature implementation used by forecasts AND backtests.
Every feature for target year T uses only papers with year < T.
Occurrence = topic has allocated marks > 0 in a paper. Windows count the last N *available* papers.
years_since_last: papers since last appearance (0 = in the latest prior paper); NaN if never seen
(plus never_seen indicator) -- no fabricated date.
"""
import numpy as np
import pandas as pd
from backend.services.common import DataError

FEATURES = ["prev1_occ", "occ_3y", "occ_5y", "prev1_marks", "marks_3y", "marks_5y", "total_occ",
            "total_marks", "years_since_last", "never_seen", "share_recent_papers",
            "marks_share_5y", "recency_score", "unit_index", "n_history_years"]
DECAY = 0.5


def build_features(pivot: pd.DataFrame, topics: pd.DataFrame, target_year: int) -> pd.DataFrame:
    prior = pivot[pivot.index < target_year]
    n = len(prior)
    if n == 0:
        raise DataError("no history before target year")
    occ = (prior > 0).astype(int)
    pos = np.arange(n)
    w = DECAY ** (n - pos - 1)
    last_pos = (occ.values * (pos[:, None] + 1)).max(axis=0)
    never = last_pos == 0
    t5 = prior.tail(5)
    denom = t5.values.sum()
    f = pd.DataFrame({
        "prev1_occ": occ.iloc[-1], "occ_3y": occ.tail(3).sum(), "occ_5y": occ.tail(5).sum(),
        "prev1_marks": prior.iloc[-1], "marks_3y": prior.tail(3).sum(), "marks_5y": t5.sum(),
        "total_occ": occ.sum(), "total_marks": prior.sum(),
        "years_since_last": np.where(never, np.nan, n - last_pos),
        "never_seen": never.astype(int),
        "share_recent_papers": occ.tail(5).mean(),
        "marks_share_5y": (t5.sum() / denom) if denom > 0 else 0.0,
        "recency_score": (occ.mul(w, axis=0)).sum(),
        "n_history_years": n,
    }, index=prior.columns)
    unit_idx = pd.factorize(topics.set_index("topic_id").loc[f.index, "unit_id"], sort=True)[0]
    f["unit_index"] = unit_idx
    return f.loc[topics.topic_id.tolist(), FEATURES].astype(float)


def label_for_year(pivot: pd.DataFrame, year: int) -> pd.Series:
    return (pivot.loc[year] > 0).astype(int)


def training_table(pivot, topics, target_year):
    """Supervised rows for target years strictly before target_year (each with >=1 prior paper)."""
    ys = [y for y in pivot.index if y < target_year][1:]
    Xs, labels, meta = [], [], []
    for y in ys:
        X = build_features(pivot, topics, y)
        Xs.append(X)
        labels.append(label_for_year(pivot, y).loc[X.index])
        meta.append(pd.DataFrame({"year": y, "topic_id": X.index}))
    if not Xs:
        raise DataError("no training rows")
    return pd.concat(Xs, ignore_index=True), pd.concat(labels, ignore_index=True), pd.concat(meta, ignore_index=True)
