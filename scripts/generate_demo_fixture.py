"""Builds frontend/public/demo-fixture.json by running the REAL pipeline on SYNTHETIC data (temp DB)."""
import json
import os
import sys
import tempfile
from pathlib import Path
root = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(root))
os.environ["RO_DB"] = str(Path(tempfile.mkdtemp()) / "demo.db"); os.environ["OLLAMA_ENDPOINT"] = "http://127.0.0.1:9"
from fastapi.testclient import TestClient
from backend.main import app
from tests.integration.test_api import setup, review_all

c = TestClient(app); sid, topics, df = setup(c); review_all(c, sid, topics, df)
fx = {"synthetic": True, "notice": "Sample dataset is synthetic. Results demonstrate the workflow and are not evidence of real examination performance.",
      "analytics": c.get(f"/api/v1/subjects/{sid}/analytics").json(),
      "backtest": c.post(f"/api/v1/subjects/{sid}/backtests", json={"include_final": True}).json(),
      "plan": c.post(f"/api/v1/subjects/{sid}/study-plans", json={"days": 7, "daily_minutes": 60}).json()}
fx["backtest"]["synthetic"] = True
(root / "frontend/public/demo-fixture.json").write_text(json.dumps(fx))
print("fixture written; tabpfn:", fx["backtest"]["dev"]["tabpfn_status"]["code"])
