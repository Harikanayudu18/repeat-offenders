"""Shared deterministic data helpers. Assignment rows: one row per (question, topic)."""
import hashlib
import pandas as pd

REQUIRED = ["year", "question_id", "marks", "topic_id", "weight"]


class DataError(ValueError):
    pass


def validate_assignments(df: pd.DataFrame, topics: pd.DataFrame, tol: float = 1e-6) -> None:
    miss = [c for c in REQUIRED if c not in df.columns]
    if miss:
        raise DataError(f"missing columns: {miss}")
    if df.empty:
        raise DataError("no reviewed assignments")
    if df[["marks", "weight"]].isna().any().any() or (df.marks < 0).any() or (df.weight < 0).any():
        raise DataError("marks/weights must be present and non-negative")
    unknown = set(df.topic_id) - set(topics.topic_id)
    if unknown:
        raise DataError(f"unknown topic ids: {sorted(unknown)}")
    g = df.groupby(["year", "question_id"])
    if (g.weight.sum() - 1).abs().max() > tol:
        raise DataError("weights per question must sum to 1")
    if (g.marks.nunique() > 1).any():
        raise DataError("a question has inconsistent marks")


def allocate(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["alloc"] = out["marks"] * out["weight"]  # marks split by weight: never double counted
    return out


def paper_totals(df: pd.DataFrame) -> pd.Series:
    return df.drop_duplicates(["year", "question_id"]).groupby("year").marks.sum()


def marks_pivot(df: pd.DataFrame, topics: pd.DataFrame) -> pd.DataFrame:
    p = allocate(df).groupby(["year", "topic_id"]).alloc.sum().unstack(fill_value=0.0)
    return p.reindex(columns=topics.topic_id.tolist(), fill_value=0.0).sort_index()


def fingerprint(df: pd.DataFrame) -> str:
    c = df[REQUIRED].sort_values(REQUIRED).round(9).to_csv(index=False)
    return hashlib.sha256(c.encode()).hexdigest()
