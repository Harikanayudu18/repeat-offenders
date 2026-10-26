"""Expanding-window rolling backtest. No random splits. Final year is a frozen holdout."""
import time
import numpy as np
import pandas as pd
from backend.adapters.tabpfn_adapter import ModelUnavailable
from backend.services.common import fingerprint, marks_pivot, paper_totals, validate_assignments
from backend.services.features.features import FEATURES, build_features, training_table
from backend.services.forecasting import models as M

DEFAULT_KS, DEFAULT_SEEDS = (3, 5, 8), tuple(range(20))
MIN_YEARS, MIN_HISTORY = 5, 3


def topk_metrics(ranking, held: pd.Series, total: float, ks) -> dict:
    actual = set(held[held > 0].index)
    out = {}
    for k in ks:
        top = list(ranking[:k])
        cov = float(held[top].sum())
        hits = len(actual & set(top))
        out[str(k)] = {"covered_marks": cov, "total_marks": float(total),
                       "coverage": cov / total if total > 0 else None, "precision": hits / k,
                       "recall": hits / len(actual) if actual else None}
    return out


def _run_fold(piv, totals, topics, T, is_final, ks, seeds, tabpfn):
    Xtr, ytr, meta = training_table(piv, topics, T)
    Xte = build_features(piv, topics, T)
    held, total = piv.loc[T], totals[T]
    res = {}

    def det(name, scores):
        t0 = time.perf_counter()
        r = M.rank(scores)
        res[name] = {"status": "ok", "metrics": topk_metrics(r, held, total, ks),
                     "top_ranking": [str(t) for t in r[:max(ks)]], "duration_s": time.perf_counter() - t0}

    det("naive_frequency", M.score_naive_frequency(Xte))
    det("recency_weighted", M.score_recency_weighted(Xte))
    for name, fn in (("logistic_regression", lambda: M.score_logreg(Xtr, ytr, Xte)),
                     ("tabpfn", (lambda: pd.Series(tabpfn.score(Xtr, ytr, Xte), index=Xte.index)) if tabpfn else None)):
        if fn is None:
            res[name] = {"status": "unavailable", "code": "not_configured", "message": "TabPFN adapter not supplied"}
            continue
        t0 = time.perf_counter()
        try:
            s = fn()
            r = M.rank(s)
            res[name] = {"status": "ok", "metrics": topk_metrics(r, held, total, ks),
                         "top_ranking": [str(t) for t in r[:max(ks)]], "duration_s": time.perf_counter() - t0}
        except ModelUnavailable as e:
            res[name] = {"status": "unavailable", "code": e.code, "message": e.message}
    per = [topk_metrics(r, held, total, ks) for r in M.random_rankings(Xte.index, seeds)]
    res["random"] = {"status": "ok", "n_seeds": len(seeds), "metrics": {
        str(k): {"coverage": float(np.mean([p[str(k)]["coverage"] for p in per])),
                 "coverage_std": float(np.std([p[str(k)]["coverage"] for p in per])),
                 "precision": float(np.mean([p[str(k)]["precision"] for p in per])),
                 "total_marks": float(total)} for k in ks}}
    return {"forecast_year": int(T), "is_final_holdout": is_final,
            "training_source_years": [int(y) for y in piv.index if y < T],
            "training_target_years": sorted({int(y) for y in meta.year}),
            "n_training_rows": int(len(Xtr)), "n_topics": int(len(Xte)), "n_features": len(FEATURES),
            "held_out_total_marks": float(total), "models": res}


def aggregate(folds, ks):
    agg = {}
    for name in ("naive_frequency", "recency_weighted", "logistic_regression", "tabpfn", "random"):
        ok = [f for f in folds if f["models"][name]["status"] == "ok"]
        agg[name] = {"n_folds": len(ok), "n_folds_total": len(folds), "folds_years": [f["forecast_year"] for f in ok],
                     "by_k": {str(k): {"mean_coverage": float(np.mean([f["models"][name]["metrics"][str(k)]["coverage"] for f in ok])),
                                      "std_coverage": float(np.std([f["models"][name]["metrics"][str(k)]["coverage"] for f in ok]))}
                              for k in ks} if ok else None}
    return agg


def run_backtest(df, topics, ks=DEFAULT_KS, seeds=DEFAULT_SEEDS, which="dev", tabpfn=None):
    """which='dev' -> development folds only; 'final' -> the frozen last-year holdout only."""
    validate_assignments(df, topics)
    piv, totals = marks_pivot(df, topics), paper_totals(df)
    years = [int(y) for y in piv.index]
    base = {"data_fingerprint": fingerprint(df), "n_years": len(years), "years": years}
    if len(years) < MIN_YEARS:
        return {**base, "status": "insufficient_data",
                "message": f"need >= {MIN_YEARS} examination years for a validated backtest; found {len(years)}. Showing descriptive statistics only."}
    ks = [k for k in ks if k <= len(topics)]
    final = years[-1]
    targets = [final] if which == "final" else [y for y in years[MIN_HISTORY:] if y != final]
    folds = [_run_fold(piv, totals, topics, y, y == final, ks, seeds, tabpfn) for y in targets]
    return {**base, "status": "ok", "which": which, "ks": ks, "final_holdout_year": final,
            "min_history_years": MIN_HISTORY, "folds": folds, "aggregate": aggregate(folds, ks),
            "tabpfn_status": tabpfn.status() if tabpfn else {"available": False, "code": "not_configured"}}
