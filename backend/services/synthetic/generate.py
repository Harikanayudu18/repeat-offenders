"""Deterministic SYNTHETIC data (original, template-based). Not real exam data."""
import numpy as np
import pandas as pd

UNITS = [("U1", "Foundations", 5), ("U2", "Core Methods", 5), ("U3", "Systems", 5),
         ("U4", "Applications", 5), ("U5", "Analysis", 4), ("U6", "Professional Practice", 4)]


def generate(seed=42, start_year=2016, n_years=9):
    rng = np.random.default_rng(seed)
    rows = []
    for uid, un, c in UNITS:
        for i in range(c):
            rows.append((f"T{len(rows)+1:02d}", f"{un} topic {i+1} (synthetic)", uid))
    topics = pd.DataFrame(rows, columns=["topic_id", "name", "unit_id"])
    units = pd.DataFrame([(u, n) for u, n, _ in UNITS], columns=["unit_id", "name"])
    p = np.array([0.8] * 7 + [0.45] * 11 + [0.12] * 10)
    p = p[rng.permutation(len(p))]
    out = []
    for y in range(start_year, start_year + n_years):
        pp = np.clip(p + rng.normal(0, 0.08, len(p)), 0.02, 0.95)
        app = list(np.flatnonzero(rng.random(len(p)) < pp))
        while len(app) < 8:
            c = int(rng.integers(len(p)))
            if c not in app: app.append(c)
        rng.shuffle(app)
        qn, i = 0, 0
        while i < len(app):
            qn += 1
            marks = int(rng.choice([4, 6, 8, 10]))
            pair = i + 1 < len(app) and rng.random() < 0.2
            ts = [(app[i], 0.6), (app[i + 1], 0.4)] if pair else [(app[i], 1.0)]
            i += 2 if pair else 1
            for t, w in ts:
                out.append((y, f"{y}-Q{qn}", marks, topics.topic_id[t], w,
                            f"[SYNTHETIC] Q{qn} ({y}): Explain the key idea of '{topics.name[t]}' with a short scenario."))
    return topics, units, pd.DataFrame(out, columns=["year", "question_id", "marks", "topic_id", "weight", "question_text"])
