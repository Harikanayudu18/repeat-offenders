"""Reproducible synthetic evaluation: python scripts/run_evaluation.py --version v1
Dev folds run every time. The frozen final-year holdout runs ONCE per --version (stored in eval/final_lock.json)."""
import argparse
import csv
import datetime as dt
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.adapters.tabpfn_adapter import TabPFNAdapter
from backend.services.backtesting.backtest import run_backtest
from backend.services.synthetic.generate import generate

MODELS = ["naive_frequency", "recency_weighted", "logistic_regression", "tabpfn", "random"]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--version", default="v1"); a = ap.parse_args()
    root = Path(__file__).resolve().parents[1]; out = root / "eval" / "results"; out.mkdir(parents=True, exist_ok=True)
    topics, _, df = generate(); tp = TabPFNAdapter(); t0 = time.perf_counter()
    dev = run_backtest(df, topics, which="dev", tabpfn=tp)
    lock_p = root / "eval" / "final_lock.json"
    lock = json.loads(lock_p.read_text()) if lock_p.exists() else {}
    key = f"{a.version}:{dev['data_fingerprint']}"
    if key in lock:
        final, reused = lock[key], True
    else:
        final, reused = run_backtest(df, topics, which="final", tabpfn=tp), False
        lock[key] = final; lock_p.write_text(json.dumps(lock, indent=1))
    res = {"synthetic": True, "eval_version": a.version, "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
           "runtime_s": round(time.perf_counter() - t0, 2), "final_reused_from_lock": reused, "dev": dev, "final": final}
    (out / "synthetic_results.json").write_text(json.dumps(res, indent=1))
    with open(out / "synthetic_per_fold.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["year", "is_final", "model", "status", "k", "coverage", "covered_marks", "total_marks"])
        for fo in dev["folds"] + final["folds"]:
            for m in MODELS:
                r = fo["models"][m]
                if r["status"] != "ok": w.writerow([fo["forecast_year"], fo["is_final_holdout"], m, r["status"] + ":" + r["code"]]); continue
                for k, v in r["metrics"].items():
                    w.writerow([fo["forecast_year"], fo["is_final_holdout"], m, "ok", k, round(v["coverage"], 4), v.get("covered_marks", ""), v["total_marks"]])
    md = ["# Synthetic evaluation (SYNTHETIC DATA: demonstrates workflow, not real exam performance)", "",
          f"- Version `{a.version}`; fingerprint `{dev['data_fingerprint'][:16]}...`; years {dev['years']}; final holdout {dev['final_holdout_year']}",
          f"- TabPFN status: `{json.dumps(dev['tabpfn_status'])}`", "- Coverage = held-out marks in top-K topics / total held-out marks.", "",
          f"## Dev folds ({len(dev['folds'])}, years {[f['forecast_year'] for f in dev['folds']]}) mean coverage (± std across folds)", "",
          "| model | folds | " + " | ".join(f"K={k}" for k in dev["ks"]) + " |", "|---|---|" + "---|" * len(dev["ks"])]
    for m in MODELS:
        ag = dev["aggregate"][m]
        cells = [f"{ag['by_k'][str(k)]['mean_coverage']:.1%} ± {ag['by_k'][str(k)]['std_coverage']:.1%}" for k in dev["ks"]] if ag["by_k"] else ["not run"] * len(dev["ks"])
        md.append(f"| {m} | {ag['n_folds']}/{ag['n_folds_total']} | " + " | ".join(cells) + " |")
    fo = final["folds"][0]
    md += ["", f"## Frozen final holdout: {fo['forecast_year']} ({fo['held_out_total_marks']:.0f} marks){' (reused from lock)' if reused else ''}", "",
           "| model | " + " | ".join(f"K={k}" for k in dev["ks"]) + " |", "|---|" + "---|" * len(dev["ks"])]
    for m in MODELS:
        r = fo["models"][m]
        md.append(f"| {m} | " + (" | ".join(f"{r['metrics'][str(k)]['coverage']:.1%}" for k in dev["ks"]) if r["status"] == "ok" else f"{r['status']} ({r['code']})") + " |")
    md += ["", "## Comparison (dev folds, mean coverage)"]
    for k in dev["ks"]:
        tb = dev["aggregate"]["tabpfn"]["by_k"]
        for b in MODELS[:3] + ["random"]:
            if tb is None: md.append(f"- K={k}: TabPFN vs {b}: **not run** (TabPFN unavailable)")
            else:
                d = tb[str(k)]["mean_coverage"] - dev["aggregate"][b]["by_k"][str(k)]["mean_coverage"]
                md.append(f"- K={k}: TabPFN {'beat' if d > 0 else 'did not beat'} {b} ({d:+.1%})")
    md += ["", "## Limitations", f"- Only {len(dev['folds'])} dev folds and one final year: differences are not statistically reliable.",
           "- Synthetic data; real papers will differ. A baseline winning is a valid outcome."]
    (out / "synthetic_summary.md").write_text("\n".join(md))
    print("\n".join(md))

main()
