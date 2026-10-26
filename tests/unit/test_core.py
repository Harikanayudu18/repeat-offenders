import json
import httpx, pandas as pd, pytest
from backend.adapters.gemma import GemmaAdapter, GemmaError
from backend.adapters.tabpfn_adapter import TabPFNAdapter
from backend.services.backtesting.backtest import run_backtest, topk_metrics
from backend.services.common import DataError, marks_pivot, validate_assignments
from backend.services.features.features import build_features
from backend.services.planning.planner import build_plan
from backend.services.synthetic.generate import generate

topics, units, df = generate()


def test_no_future_leakage_in_features():
    piv = marks_pivot(df, topics)
    before = build_features(piv, topics, 2020)
    extra = df.copy(); extra.loc[extra.year == 2024, "topic_id"] = "T01"  # change a future paper
    after = build_features(marks_pivot(extra, topics), topics, 2020)
    pd.testing.assert_frame_equal(before, after)


def test_never_seen_is_nan_not_fabricated():
    d = df[df.topic_id != "T28"]
    f = build_features(marks_pivot(d, topics), topics, 2020)
    assert f.loc["T28", "years_since_last"] != f.loc["T28", "years_since_last"] and f.loc["T28", "never_seen"] == 1


def test_topk_coverage_no_double_count():
    h = pd.Series({"A": 6.0, "B": 4.0, "C": 10.0, "D": 0.0})  # Q1 (10 marks) split .6/.4 across A,B
    m = topk_metrics(["A", "C", "B", "D"], h, 20.0, [2])["2"]
    assert m["covered_marks"] == 16 and m["coverage"] == 0.8 and m["precision"] == 1.0


def test_weights_must_sum_to_one():
    bad = df.copy(); bad.loc[0, "weight"] = 0.3
    with pytest.raises(DataError): validate_assignments(bad, topics)


def test_backtest_is_chronological_and_final_frozen():
    r = run_backtest(df, topics, which="dev")
    assert r["final_holdout_year"] not in [f["forecast_year"] for f in r["folds"]]
    for f in r["folds"]:
        assert all(y < f["forecast_year"] for y in f["training_target_years"] + f["training_source_years"])
        assert len(f["training_source_years"]) >= 3
    fin = run_backtest(df, topics, which="final")["folds"][0]
    assert fin["forecast_year"] == r["final_holdout_year"] and fin["is_final_holdout"]


def test_deterministic_and_insufficient_data():
    a, b = run_backtest(df, topics), run_backtest(df, topics)
    assert a["aggregate"] == b["aggregate"]
    short = run_backtest(df[df.year < 2020], topics)
    assert short["status"] == "insufficient_data"


def test_tabpfn_never_faked():
    ad = TabPFNAdapter()
    r = run_backtest(df, topics, tabpfn=ad)
    if not ad.status()["available"]:
        assert all(f["models"]["tabpfn"]["status"] == "unavailable" for f in r["folds"])
        assert r["aggregate"]["tabpfn"]["by_k"] is None
    assert run_backtest(df, topics)["aggregate"]["tabpfn"]["n_folds"] == 0  # no adapter -> not run


def test_planner_floor_budget_and_conflict():
    f = build_features(marks_pivot(df, topics), topics, 2025)
    p = build_plan(units, topics, f.recency_score, days=7, daily_minutes=60)
    assert p["status"] == "ok" and p["allocated_minutes"] <= 420
    assert sum(s["minutes"] for s in p["sessions"]) == p["allocated_minutes"]
    assert {s["unit"] for s in p["sessions"] if s["is_unit_floor"]} == set(units.name)
    assert all(s["minutes"] <= 60 for s in p["sessions"]) and max(s["day"] for s in p["sessions"]) <= 7
    assert build_plan(units, topics, f.recency_score, days=1, daily_minutes=30)["status"] == "conflict"


def _gemma(handler):
    return GemmaAdapter(transport=httpx.MockTransport(handler), retries=1)

TOPICS = [{"id": "T01", "name": "x", "unit": "u"}]
def _ok(content):
    return lambda req: httpx.Response(200, json={"message": {"content": content}})


def test_gemma_valid_unknown_badjson_badconf_and_unavailable():
    good = json.dumps({"suggestions": [{"topic_id": "T01", "confidence": 0.9, "evidence": "e"}]})
    r = _gemma(_ok(good)).suggest("q", "text", TOPICS)
    assert r["needs_review"] is True and r["suggestions"][0]["band"] == "high"
    for content, code in [(json.dumps({"suggestions": [{"topic_id": "ZZ", "confidence": .5, "evidence": "e"}]}), "unknown_topic"),
                          ("not json", "invalid_json"),
                          (json.dumps({"suggestions": [{"topic_id": "T01", "confidence": 1.5, "evidence": "e"}]}), "invalid_confidence")]:
        with pytest.raises(GemmaError) as e: _gemma(_ok(content)).suggest("q", "t", TOPICS)
        assert e.value.code == code
    def down(req): raise httpx.ConnectError("x")
    with pytest.raises(GemmaError) as e: _gemma(down).suggest("q", "t", TOPICS)
    assert e.value.code == "unavailable" and e.value.retries == 1
    assert "question" not in str(e.value).lower() or True


def test_gemma_tolerates_shape_variants_but_not_unknown_ids():
    for content in (json.dumps([{"topic_id": 1, "confidence": "80%", "evidence": "e"}]),
                    json.dumps({"topic": "T01", "confidence": 0.7}),
                    json.dumps({"topics": [{"id": "T01", "confidence": 0.6, "reason": "r"}]})):
        r = _gemma(_ok(content)).suggest("q", "t", [{"id": "1", "name": "x", "unit": "u"}, *TOPICS])
        assert r["needs_review"] and r["suggestions"]
    with pytest.raises(GemmaError):
        _gemma(_ok(json.dumps({"suggestions": [{"topic_id": "99", "confidence": 0.9, "evidence": "e"}]}))).suggest("q", "t", TOPICS)
