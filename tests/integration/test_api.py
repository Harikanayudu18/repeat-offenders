import logging
import pytest
from fastapi.testclient import TestClient
from backend.adapters.sentry_tracing import sanitize_event, safe_attrs
from backend.services.synthetic.generate import generate

SECRET = "SECRET-QUESTION-TEXT-XYZ"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("RO_DB", str(tmp_path / "t.db"))
    monkeypatch.setenv("OLLAMA_ENDPOINT", "http://127.0.0.1:9")
    from backend.main import app
    return TestClient(app)


def csv_bytes(df, extra=""):
    q = df.drop_duplicates(["year", "question_id"])
    lines = ["year,question_number,question_text,marks,topic"] + [f'{r.year},{r.question_id},"{r.question_text} {extra}",{r.marks},' for r in q.itertuples()]
    return "\n".join(lines).encode()


def setup(client, extra=""):
    topics, units, df = generate()
    syl = "\n".join(f"{u.name}\n" + "\n".join(f"- {t.name}" for t in topics[topics.unit_id == u.unit_id].itertuples()) for u in units.itertuples())
    sid = client.post("/api/v1/subjects", json={"name": "Synthetic", "syllabus": syl}).json()["id"]
    prev = client.post(f"/api/v1/subjects/{sid}/imports/preview", files={"file": ("p.csv", csv_bytes(df, extra), "text/csv")}).json()
    assert prev["can_confirm"]
    assert client.post(f"/api/v1/subjects/{sid}/imports/confirm", json={"rows": prev["rows"]}).status_code == 201
    return sid, topics, df


def review_all(client, sid, topics, df, skip=0):
    tid = {t["name"]: t["id"] for t in client.get(f"/api/v1/subjects/{sid}/topics").json()}
    name = topics.set_index("topic_id").name
    for i, q in enumerate(client.get(f"/api/v1/subjects/{sid}/questions").json()):
        if i < skip: continue
        a = df[df.question_id == q["question_number"]]
        r = client.post(f"/api/v1/questions/{q['id']}/review", json={"decision": "accept", "assignments": [{"topic_id": tid[name[x.topic_id]], "weight": x.weight} for x in a.itertuples()]})
        assert r.status_code == 200


def test_full_journey_and_privacy(client, caplog):
    caplog.set_level(logging.DEBUG)
    sid, topics, df = setup(client, SECRET)
    qs = client.get(f"/api/v1/subjects/{sid}/questions").json()
    assert client.post(f"/api/v1/questions/{qs[0]['id']}/suggestions").json()["manual_assignment_required"] is True  # Gemma offline -> honest fallback
    assert client.get(f"/api/v1/subjects/{sid}/analytics").status_code == 409  # unresolved never silently counted
    review_all(client, sid, topics, df)
    a = client.get(f"/api/v1/subjects/{sid}/analytics").json()
    assert len(a["years"]) == 9 and len(a["table"]) == 28
    assert all(isinstance(v, float) for v in a["unit_marks"].values())
    b = client.post(f"/api/v1/subjects/{sid}/backtests", json={"include_final": True}).json()
    assert b["dev"]["status"] == "ok" and b["final"]["folds"][0]["is_final_holdout"]
    assert b["dev"]["aggregate"]["tabpfn"]["n_folds"] == 0 or b["dev"]["tabpfn_status"]["available"]
    again = client.post(f"/api/v1/subjects/{sid}/backtests", json={"include_final": True}).json()
    assert again["final"]["reused_frozen_result"] is True
    p = client.post(f"/api/v1/subjects/{sid}/study-plans", json={"days": 7, "daily_minutes": 60}).json()
    assert p["status"] == "ok" and p["allocated_minutes"] <= 420
    assert SECRET not in caplog.text


def test_duplicate_year_oversize_and_unresolved_exclusion(client, monkeypatch):
    sid, topics, df = setup(client)
    rows = client.post(f"/api/v1/subjects/{sid}/imports/preview", files={"file": ("p.csv", csv_bytes(df), "text/csv")}).json()
    assert rows["existing_years"] and client.post(f"/api/v1/subjects/{sid}/imports/confirm", json={"rows": rows["rows"]}).status_code == 409
    monkeypatch.setenv("RO_MAX_UPLOAD_BYTES", "100")
    import backend.main as m; monkeypatch.setattr(m, "MAX_UPLOAD", 100)
    assert client.post(f"/api/v1/subjects/{sid}/imports/preview", files={"file": ("p.csv", b"x" * 500, "text/csv")}).status_code == 413
    assert client.post(f"/api/v1/subjects/{sid}/imports/preview", files={"file": ("../../evil.exe", b"x", "text/plain")}).status_code == 415
    review_all(client, sid, topics, df, skip=3)  # first 3 stay unresolved
    assert client.get(f"/api/v1/subjects/{sid}/analytics").status_code == 409
    ok = client.get(f"/api/v1/subjects/{sid}/analytics?exclude_unresolved=true").json()
    assert ok["unresolved_excluded"] == 3


def test_sentry_sanitization():
    ev = {"request": {"data": SECRET}, "extra": {"q": SECRET}, "exception": {"values": [{"type": "ValueError", "value": SECRET, "stacktrace": {"frames": [{"vars": {"t": SECRET}}]}}]},
          "spans": [{"op": "x", "description": SECRET, "data": {"question_text": SECRET, "row_count": 3, "model_family": "gemma"}}]}
    assert SECRET not in str(sanitize_event(ev))
    assert safe_attrs({"question_text": "abc", "n": 1}) == {"n": 1}


def test_bad_weights_rejected(client):
    sid, topics, df = setup(client)
    q = client.get(f"/api/v1/subjects/{sid}/questions").json()[0]
    t = client.get(f"/api/v1/subjects/{sid}/topics").json()[0]["id"]
    r = client.post(f"/api/v1/questions/{q['id']}/review", json={"decision": "accept", "assignments": [{"topic_id": t, "weight": 0.4}]})
    assert r.status_code == 422 and "stack" not in r.text.lower() and r.json()["error"]["request_id"]


def test_root_and_favicon_do_not_404(client):
    assert client.get("/").status_code == 200 and client.get("/favicon.ico").status_code == 204
