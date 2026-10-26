"""Local FastAPI backend (binds 127.0.0.1 by default). Deterministic code is the source of truth."""
import collections
import json
import logging
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.adapters import sentry_tracing as tr
from backend.adapters.gemma import GemmaAdapter, GemmaError
from backend.adapters.tabpfn_adapter import TabPFNAdapter
from backend.services.backtesting.backtest import run_backtest
from backend.services.common import DataError, fingerprint, marks_pivot
from backend.services.features.features import build_features
from backend.services.imports.parsers import ParseError, parse_upload
from backend.services.planning.planner import build_plan

log = logging.getLogger("ro")
MAX_UPLOAD = int(os.getenv("RO_MAX_UPLOAD_BYTES", 2_000_000))
tr.init()
app = FastAPI(title="Repeat Offenders (local)", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type"])
TABPFN = TabPFNAdapter()
SCHEMA = """
CREATE TABLE IF NOT EXISTS subjects(id INTEGER PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS units(id INTEGER PRIMARY KEY, subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE, name TEXT NOT NULL, order_index INTEGER);
CREATE TABLE IF NOT EXISTS topics(id INTEGER PRIMARY KEY, subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE, unit_id INTEGER NOT NULL REFERENCES units(id) ON DELETE CASCADE, name TEXT NOT NULL, UNIQUE(subject_id,name));
CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY, subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE, year INTEGER NOT NULL, qnum TEXT NOT NULL, text TEXT NOT NULL, marks REAL NOT NULL, status TEXT NOT NULL DEFAULT 'unreviewed', UNIQUE(subject_id,year,qnum));
CREATE TABLE IF NOT EXISTS assignments(id INTEGER PRIMARY KEY, question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE, topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE, weight REAL NOT NULL, source TEXT NOT NULL, confidence REAL, decision TEXT NOT NULL, updated_at TEXT);
CREATE TABLE IF NOT EXISTS final_runs(subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE, fingerprint TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(subject_id,fingerprint));
CREATE INDEX IF NOT EXISTS ix_q_subject_year ON questions(subject_id,year);
CREATE INDEX IF NOT EXISTS ix_a_question ON assignments(question_id);
"""


def db():
    c = sqlite3.connect(os.getenv("RO_DB", "./repeat_offenders.db"))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON"); c.executescript(SCHEMA)
    return c


def now(): return datetime.now(timezone.utc).isoformat()


def err(status, code, msg, rid=None, fields=None):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": msg, "fields": fields, "request_id": rid}})


class Redact(logging.Filter):
    PATS = [(re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+"), "<user-path>"), (re.compile(r"/(?:home|Users)/[^/\s]+"), "<user-path>"),
            (re.compile(r"(?i)(dsn|token|secret|key)=\S+"), r"\1=<redacted>")]

    def filter(self, rec):
        m = rec.getMessage()
        for p, r in self.PATS: m = p.sub(r, m)
        rec.msg, rec.args = m[:500], ()
        return True


for _n in ("ro", "ro.trace"): logging.getLogger(_n).addFilter(Redact())
RATE = int(os.getenv("RO_RATE_LIMIT_PER_MIN", 600)); _hits: dict = collections.defaultdict(collections.deque)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=os.getenv("RO_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver").split(","))


@app.middleware("http")
async def rid_mw(request: Request, call_next):
    request.state.rid = uuid.uuid4().hex[:12]
    if request.url.path.startswith("/api"):
        dq, t = _hits[request.client.host if request.client else "?"], time.time()
        while dq and t - dq[0] > 60: dq.popleft()
        if len(dq) >= RATE: return err(429, "rate_limited", "Too many requests. Slow down and retry shortly.", request.state.rid)
        dq.append(t)
    try:
        r = await call_next(request)
    except Exception as e:  # never leak stack traces or content
        log.error("unhandled %s rid=%s", type(e).__name__, request.state.rid)
        return err(500, "internal_error", "Unexpected server error.", request.state.rid)
    r.headers.update({"X-Request-ID": request.state.rid, "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
                      "Referrer-Policy": "no-referrer", "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'"})
    if request.url.path.startswith("/api"): r.headers["Cache-Control"] = "no-store"
    return r


@app.exception_handler(HTTPException)
async def http_exc(request, e):
    d = e.detail if isinstance(e.detail, dict) else {"code": "http_error", "message": str(e.detail)}
    return err(e.status_code, d["code"], d["message"], request.state.rid)


@app.exception_handler(RequestValidationError)
async def val_exc(request, e):
    return err(422, "validation_error", "Request validation failed.", request.state.rid,
               [{"field": ".".join(map(str, x["loc"])), "problem": x["msg"]} for x in e.errors()])


def fail(status, code, msg): raise HTTPException(status, {"code": code, "message": msg})


# ---------- system ----------
@app.get("/", include_in_schema=False)
def root():
    ui = os.getenv("RO_FRONTEND_DIST")
    if ui and os.path.isfile(os.path.join(ui, "index.html")):
        from fastapi.responses import FileResponse
        return FileResponse(os.path.join(ui, "index.html"))
    return {"app": "Repeat Offenders (local API)", "status": "ok", "api_docs": "/docs",
            "health": "/api/v1/health", "frontend": "Run the UI separately: cd frontend && npm run dev, then open http://localhost:5173"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    from fastapi import Response
    return Response(status_code=204)


@app.get("/api/v1/health")
def health(): return {"status": "ok", "mode": "local"}


def get_gemma():
    return GemmaAdapter(os.getenv("OLLAMA_ENDPOINT", "http://127.0.0.1:11434"), os.getenv("OLLAMA_MODEL", "gemma3:4b"), timeout=180, retries=1)


@app.get("/api/v1/system/models")
def models():
    return {"tabpfn": TABPFN.status(), "gemma": get_gemma().check(), "sentry_enabled": tr.ENABLED,
            "note": "Deterministic analysis works without either model."}


# ---------- subjects / syllabus ----------
class SubjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    syllabus: str = Field(max_length=50_000, description="Unit names on their own line; topics as '- topic' lines")


@app.post("/api/v1/subjects", status_code=201)
def create_subject(b: SubjectIn):
    c = db(); unit = None; n_t = 0
    with c:
        sid = c.execute("INSERT INTO subjects(name,created_at) VALUES(?,?)", (b.name.strip(), now())).lastrowid
        for ln in (x.strip() for x in b.syllabus.splitlines() if x.strip()):
            if ln.startswith("-"):
                if unit is None: fail(422, "syllabus_format", "A topic appears before any unit line.")
                try: c.execute("INSERT INTO topics(subject_id,unit_id,name) VALUES(?,?,?)", (sid, unit, ln.lstrip("- ").strip())); n_t += 1
                except sqlite3.IntegrityError: fail(422, "duplicate_topic", "Duplicate topic name in this subject.")
            else:
                unit = c.execute("INSERT INTO units(subject_id,name,order_index) VALUES(?,?,?)", (sid, ln, 0)).lastrowid
        if n_t == 0: fail(422, "empty_syllabus", "Syllabus needs at least one topic.")
    return {"id": sid}


@app.get("/api/v1/subjects")
def subjects():
    return [dict(r) for r in db().execute("SELECT s.id,s.name,(SELECT COUNT(*) FROM questions q WHERE q.subject_id=s.id) questions FROM subjects s")]


@app.delete("/api/v1/subjects/{sid}", status_code=204)
def delete_subject(sid: int):
    c = db()
    with c: c.execute("DELETE FROM subjects WHERE id=?", (sid,))


@app.get("/api/v1/subjects/{sid}/topics")
def topics_list(sid: int):
    return [dict(r) for r in db().execute("SELECT t.id,t.name,u.name unit FROM topics t JOIN units u ON u.id=t.unit_id WHERE t.subject_id=? ORDER BY u.id,t.id", (sid,))]


# ---------- imports ----------
class Row(BaseModel):
    year: int = Field(ge=1900, le=2100)
    question_number: str = Field(min_length=1, max_length=32)
    question_text: str = Field(min_length=1, max_length=5000)
    marks: float = Field(ge=0, le=1000)
    topic: Optional[str] = Field(default=None, max_length=200)


class ConfirmIn(BaseModel):
    rows: list[Row] = Field(max_length=3000)
    on_duplicate: Literal["cancel", "replace"] = "cancel"


@app.post("/api/v1/subjects/{sid}/imports/preview")
async def import_preview(sid: int, file: UploadFile = File(...)):
    raw = await file.read(MAX_UPLOAD + 1)
    if len(raw) > MAX_UPLOAD: fail(413, "file_too_large", "File exceeds the upload limit.")
    with tr.span("import_parse", bytes=len(raw)) as sp:
        try: recs = parse_upload(file.filename or "", raw)
        except ParseError as e:
            sp["error_category"] = e.code; fail(e.status, e.code, e.message)
        rows, invalid, seen = [], [], set()
        for i, r in enumerate(recs, start=1):
            try:
                row = Row(year=int(float(r["year"])), marks=float(r["marks"]), question_text=str(r.get("question_text") or "").strip(),
                          question_number=str(r.get("question_number") or len(rows) + 1).strip(), topic=r.get("topic") or None)
                if (row.year, row.question_number) in seen: raise ValueError("duplicate question number")
                seen.add((row.year, row.question_number)); rows.append(row.model_dump())
            except Exception as e:
                invalid.append({"line": i, "problem": type(e).__name__})  # no content echoed
        sp["row_count"] = len(rows)
    ex = {r["year"] for r in db().execute("SELECT DISTINCT year FROM questions WHERE subject_id=?", (sid,))}
    years = sorted({r["year"] for r in rows})
    return {"rows": rows, "invalid": invalid, "years": years, "existing_years": sorted(ex & set(years)),
            "marks_by_year": {str(y): sum(r["marks"] for r in rows if r["year"] == y) for y in years},
            "can_confirm": bool(rows) and not invalid}


@app.post("/api/v1/subjects/{sid}/imports/confirm", status_code=201)
def import_confirm(sid: int, b: ConfirmIn):
    c = db(); years = {r.year for r in b.rows}
    ex = {r["year"] for r in c.execute("SELECT DISTINCT year FROM questions WHERE subject_id=?", (sid,))} & years
    if ex and b.on_duplicate == "cancel":
        fail(409, "duplicate_year", f"Papers already exist for years {sorted(ex)}. Choose replace or cancel.")
    names = {r["name"].lower(): r["id"] for r in c.execute("SELECT id,name FROM topics WHERE subject_id=?", (sid,))}
    with c:
        for y in ex: c.execute("DELETE FROM questions WHERE subject_id=? AND year=?", (sid, y))
        for r in b.rows:
            qid = c.execute("INSERT INTO questions(subject_id,year,qnum,text,marks) VALUES(?,?,?,?,?)", (sid, r.year, r.question_number, r.question_text, r.marks)).lastrowid
            if r.topic and r.topic.lower() in names:  # deterministic hint: stays a SUGGESTION until a human accepts
                c.execute("INSERT INTO assignments(question_id,topic_id,weight,source,decision,updated_at) VALUES(?,?,1,'deterministic_mapping','suggested',?)", (qid, names[r.topic.lower()], now()))
    return {"imported": len(b.rows), "years": sorted(years)}


# ---------- tagging ----------
@app.get("/api/v1/subjects/{sid}/questions")
def questions(sid: int):
    c = db(); out = []
    for q in c.execute("SELECT id,year,qnum question_number,text question_text,marks,status FROM questions WHERE subject_id=? ORDER BY year,id", (sid,)):
        a = [dict(x) for x in c.execute("SELECT topic_id,weight,source,confidence,decision FROM assignments WHERE question_id=?", (q["id"],))]
        out.append({**dict(q), "assignments": a})
    return out


@app.post("/api/v1/questions/{qid}/suggestions")
def suggest(qid: int):
    c = db(); q = c.execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone()
    if not q: fail(404, "not_found", "Question not found.")
    ts = [{"id": str(r["id"]), "name": r["name"], "unit": r["unit"]} for r in c.execute("SELECT t.id,t.name,u.name unit FROM topics t JOIN units u ON u.id=t.unit_id WHERE t.subject_id=?", (q["subject_id"],))]
    with tr.span("topic_tag_suggestion", model_family="gemma", model=os.getenv("OLLAMA_MODEL", "gemma3:4b"), row_count=len(ts)) as sp:
        try:
            res = get_gemma().suggest(str(qid), q["text"], ts)
        except GemmaError as e:
            sp.update(fallback=True, error_category=e.code, retries=e.retries, status="error")
            return {"error": e.code, "manual_assignment_required": True, "message": e.message}
    with tr.span("topic_tag_validation", row_count=len(res["suggestions"])):
        with c:
            c.execute("DELETE FROM assignments WHERE question_id=? AND source='gemma' AND decision='suggested'", (qid,))
            for s in res["suggestions"]:
                c.execute("INSERT INTO assignments(question_id,topic_id,weight,source,confidence,decision,updated_at) VALUES(?,?,?,?,?,'suggested',?)",
                          (qid, int(s["topic_id"]), 1.0, "gemma", s["confidence"], now()))
    return res


class Assign(BaseModel):
    topic_id: int
    weight: float = Field(ge=0, le=1)


class ReviewIn(BaseModel):
    decision: Literal["accept", "unresolved"]
    assignments: list[Assign] = []


@app.post("/api/v1/questions/{qid}/review")
def review(qid: int, b: ReviewIn):
    c = db(); q = c.execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone()
    if not q: fail(404, "not_found", "Question not found.")
    with c:
        if b.decision == "unresolved":
            c.execute("DELETE FROM assignments WHERE question_id=? AND decision='accepted'", (qid,))
            c.execute("UPDATE questions SET status='unresolved' WHERE id=?", (qid,)); return {"status": "unresolved"}
        if not b.assignments or abs(sum(a.weight for a in b.assignments) - 1) > 1e-6:
            fail(422, "weights", "Weights must be non-negative and sum to 1.")
        valid = {r["id"] for r in c.execute("SELECT id FROM topics WHERE subject_id=?", (q["subject_id"],))}
        if any(a.topic_id not in valid for a in b.assignments): fail(422, "unknown_topic", "Topic not in this subject.")
        sug = {r["topic_id"]: r["source"] for r in c.execute("SELECT topic_id,source FROM assignments WHERE question_id=? AND decision='suggested'", (qid,))}
        c.execute("DELETE FROM assignments WHERE question_id=? AND decision='accepted'", (qid,))
        for a in b.assignments:
            src = {"gemma": "model_suggestion_accepted", "deterministic_mapping": "deterministic_mapping_accepted"}.get(sug.get(a.topic_id), "human")
            c.execute("INSERT INTO assignments(question_id,topic_id,weight,source,decision,updated_at) VALUES(?,?,?,?,'accepted',?)", (qid, a.topic_id, a.weight, src, now()))
        c.execute("UPDATE questions SET status='reviewed' WHERE id=?", (qid,))
    return {"status": "reviewed"}


# ---------- analytics ----------
def load(sid: int, exclude_unresolved: bool):
    c = db()
    tp = pd.DataFrame([(f"T{r['id']}", r["name"], f"U{r['unit_id']}") for r in c.execute("SELECT id,name,unit_id FROM topics WHERE subject_id=? ORDER BY id", (sid,))], columns=["topic_id", "name", "unit_id"])
    un = pd.DataFrame([(f"U{r['id']}", r["name"]) for r in c.execute("SELECT id,name FROM units WHERE subject_id=? ORDER BY id", (sid,))], columns=["unit_id", "name"])
    unresolved = c.execute("SELECT COUNT(*) n FROM questions WHERE subject_id=? AND status!='reviewed'", (sid,)).fetchone()["n"]
    if unresolved and not exclude_unresolved:
        fail(409, "unresolved_questions", f"{unresolved} questions are unresolved. Review them or choose to exclude them explicitly.")
    df = pd.DataFrame([(r["year"], str(r["qid"]), r["marks"], f"T{r['topic_id']}", r["weight"]) for r in c.execute(
        "SELECT q.year,q.id qid,q.marks,a.topic_id,a.weight FROM questions q JOIN assignments a ON a.question_id=q.id WHERE q.subject_id=? AND a.decision='accepted' AND q.status='reviewed'", (sid,))],
        columns=["year", "question_id", "marks", "topic_id", "weight"])
    if df.empty: fail(422, "no_reviewed_data", "No reviewed questions yet.")
    return df, tp, un, unresolved




@app.get("/api/v1/subjects/{sid}/analytics")
def analytics(sid: int, exclude_unresolved: bool = False):
    df, tp, un, unresolved = load(sid, exclude_unresolved)
    with tr.span("feature_generation", row_count=len(df)) as sp:
        piv = marks_pivot(df, tp); nxt = int(piv.index.max()) + 1
        f = build_features(piv, tp, nxt); sp["feature_count"] = f.shape[1]
    tot = float(piv.values.sum()); names = tp.set_index("topic_id")["name"]; unit = tp.set_index("topic_id")["unit_id"].map(un.set_index("unit_id")["name"])
    table = pd.DataFrame({"topic": names, "unit": unit, "last_paper_count": f.prev1_occ, "last_3_papers": f.occ_3y, "last_5_papers": f.occ_5y,
                          "papers_since_last": f.years_since_last, "total_marks": f.total_marks, "marks_share": f.total_marks / tot if tot else 0,
                          "recency_score": f.recency_score})
    um = piv.T.groupby(tp.set_index("topic_id")["unit_id"].map(un.set_index("unit_id")["name"])).sum()
    return {"fingerprint": fingerprint(df), "years": [int(y) for y in piv.index], "unresolved_excluded": int(unresolved),
            "table": json.loads(table.reset_index(drop=True).to_json(orient="records")),
            "heatmap": {"topics": names.tolist(), "years": [int(y) for y in piv.index], "marks": json.loads(piv.T.to_json(orient="values"))},
            "unit_marks": {k: float(v) for k, v in um.sum(axis=1).items()}, "forecast_year": nxt}


class BacktestIn(BaseModel):
    include_final: bool = False
    exclude_unresolved: bool = False


@app.post("/api/v1/subjects/{sid}/backtests")
def backtest(sid: int, b: BacktestIn):
    df, tp, _, _ = load(sid, b.exclude_unresolved)
    with tr.span("historical_evaluation", row_count=len(df), model_family="tabpfn+baselines") as sp:
        try: dev = run_backtest(df, tp, which="dev", tabpfn=TABPFN)
        except DataError as e: fail(422, "data_error", str(e))
        sp["status"] = dev["status"]
        final = None
        if b.include_final and dev["status"] == "ok":
            c = db(); row = c.execute("SELECT result_json FROM final_runs WHERE subject_id=? AND fingerprint=?", (sid, dev["data_fingerprint"])).fetchone()
            if row: final = {**json.loads(row["result_json"]), "reused_frozen_result": True}
            else:
                final = run_backtest(df, tp, which="final", tabpfn=TABPFN)
                with c: c.execute("INSERT INTO final_runs VALUES(?,?,?,?)", (sid, dev["data_fingerprint"], json.dumps(final), now()))
    return {"dev": dev, "final": final, "synthetic": False}


class PlanIn(BaseModel):
    days: int = Field(ge=1, le=120)
    daily_minutes: int = Field(ge=10, le=720)
    session_minutes: int = Field(default=30, ge=10, le=120)
    unit_floor_minutes: int = Field(default=15, ge=0, le=240)
    shortlist: int = Field(default=8, ge=1, le=40)
    exclude_unresolved: bool = False


@app.post("/api/v1/subjects/{sid}/study-plans")
def plan(sid: int, b: PlanIn):
    df, tp, un, _ = load(sid, b.exclude_unresolved)
    with tr.span("study_plan_generation", row_count=len(tp), model_family="deterministic", fallback=False):
        f = build_features(marks_pivot(df, tp), tp, int(df.year.max()) + 1)
        return build_plan(un, tp, f.recency_score, b.days, b.daily_minutes, b.session_minutes, b.unit_floor_minutes, b.shortlist, marks_share=f.marks_share_5y)


_ui = os.getenv("RO_FRONTEND_DIST")
if _ui and os.path.isdir(os.path.join(_ui, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(_ui, "assets")), name="assets")
