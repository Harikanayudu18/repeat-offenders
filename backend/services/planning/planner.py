"""Deterministic 'lazy payoff' planner. Every unit gets a minimum floor; budget never exceeded."""
import math
import pandas as pd

NOTICE = "This plan prioritises historical patterns. It does not predict or guarantee future examination questions."


def build_plan(units, topics, priority, days, daily_minutes, session_minutes=30, unit_floor_minutes=15,
               shortlist=8, mastery=None, marks_share=None):
    """units: df(unit_id,name); topics: df(topic_id,name,unit_id); priority: Series topic_id->score>=0;
    mastery: optional dict topic_id->0..1 (low mastery gets more time)."""
    total = int(days * daily_minutes)
    need = unit_floor_minutes * len(units)
    if need > total:
        return {"status": "conflict", "notice": NOTICE, "needed_minutes": need, "available_minutes": total,
                "message": "Unit floors do not fit in the time budget. Increase time or lower the per-unit floor."}
    mastery = mastery or {}
    ms = marks_share if marks_share is not None else pd.Series(0.0, index=priority.index)
    p = priority.reindex(topics.topic_id).fillna(0.0)
    m = ms.reindex(topics.topic_id).fillna(0.0)
    w = (p / p.max() if p.max() > 0 else p) + (m / m.max() if m.max() > 0 else m)
    w = w * pd.Series({t: 1 + (1 - mastery.get(t, 0.5)) for t in w.index})
    top = sorted(w.index, key=lambda t: (-w[t], str(t)))[:shortlist]
    top = [t for t in top if w[t] > 0] or top[:1]
    rest = total - need
    final = (int(rest * 0.1) // 5) * 5 if days >= 2 else 0
    pool_q = (rest - final) // 5
    raw = w[top] / w[top].sum() * pool_q
    q = raw.apply(math.floor)
    for t in sorted(top, key=lambda t: (-(raw[t] - q[t]), str(t)))[: int(pool_q - q.sum())]:
        q[t] += 1
    tn, un = topics.set_index("topic_id"), units.set_index("unit_id")
    blocks = []
    for uid, u in un.iterrows():
        blocks.append(dict(topic_id=None, topic=f"Unit overview: {u['name']}", unit=u["name"], minutes=unit_floor_minutes,
                           reason="Minimum unit-coverage review (no unit is skipped).", is_unit_floor=True,
                           action="Skim notes and re-read headings; list 3 key terms."))
    for t in top:
        if q[t] > 0:
            blocks.append(dict(topic_id=t, topic=tn.loc[t, "name"], unit=un.loc[tn.loc[t, "unit_id"], "name"],
                               minutes=int(q[t] * 5), reason=f"Historical priority score {w[t]:.2f} (recurrence + marks share"
                               + (", weaker mastery" if mastery.get(t, 0.5) < 0.5 else "") + ").", is_unit_floor=False,
                               action="Solve past-paper questions on this topic, then write a 5-line summary."))
    if final:
        blocks.append(dict(topic_id=None, topic="Final mixed review of shortlisted topics", unit="All", minutes=final,
                           reason="Final review session.", is_unit_floor=False, action="Timed mixed practice; fix gaps."))
    allocated = sum(b["minutes"] for b in blocks)
    chunks = []  # round-robin so topics interleave across days
    split = [[(b, min(session_minutes, b["minutes"] - i)) for i in range(0, b["minutes"], session_minutes)] for b in blocks]
    split[-1] = split[-1] if not final else split[-1]
    n = max(len(s) for s in split)
    for i in range(n):
        for s in split[:-1] if final else split:
            if i < len(s): chunks.append(s[i])
    if final:
        chunks += split[-1]
    cap = min(daily_minutes, math.ceil(allocated / days / 5) * 5)
    sessions, day, used, k = [], 1, 0, 0
    for b, mins in chunks:
        while mins > 0:
            if used >= cap: day, used = day + 1, 0
            take = min(mins, cap - used)
            k += 1
            sessions.append({"day": day, "session": k, **{x: b[x] for x in ("topic_id", "topic", "unit", "reason", "is_unit_floor", "action")}, "minutes": take})
            used += take; mins -= take
    assert sum(s["minutes"] for s in sessions) == allocated <= total
    return {"status": "ok", "notice": NOTICE, "total_minutes": total, "allocated_minutes": allocated,
            "unallocated_minutes": total - allocated, "days_used": day, "sessions": sessions}
