import { useEffect, useState } from "react";
import { api, DEMO, J } from "../api";

export default function Dashboard({ sid, fx, setTab }: { sid: number | null; fx: J; setTab: (t: string) => void }) {
  const [qs, setQs] = useState<J[] | null>(null); const [ts, setTs] = useState<J[]>([]); const [m, setM] = useState<J>(null);
  useEffect(() => {
    if (DEMO) return;
    api("/system/models").then(setM).catch(() => { });
    if (sid != null) { api(`/subjects/${sid}/questions`).then(setQs).catch(() => setQs([])); api(`/subjects/${sid}/topics`).then(setTs).catch(() => { }); }
  }, [sid]);
  const tp = DEMO ? fx?.backtest?.dev?.tabpfn_status : m?.tabpfn;
  const years = DEMO ? fx?.analytics?.years?.length : new Set((qs ?? []).map(q => q.year)).size;
  const reviewed = (qs ?? []).filter(q => q.status === "reviewed").length;
  const marks = DEMO ? fx?.analytics?.table?.reduce((s: number, r: J) => s + r.total_marks, 0) : (qs ?? []).filter(q => q.status === "reviewed").reduce((s, q) => s + q.marks, 0);
  const topics = DEMO ? fx?.analytics?.table?.length : ts.length;
  const next: [string, string] = DEMO ? ["Explore the synthetic analytics", "Analytics"] : sid == null ? ["Create your subject and syllabus", "Setup"] : !qs?.length ? ["Import your past papers", "Import"]
    : reviewed < qs.length ? [`Review ${qs.length - reviewed} remaining questions`, "Review"] : years >= 5 ? ["Run the backtest and build your plan", "Backtest"] : ["Add more years (need 5+ for a backtest)", "Import"];
  const tile = (icon: string, v: string | number, l: string) => <div className="tile"><span className="ti">{icon}</span><b>{v}</b><small>{l}</small></div>;
  const pill = (name: string, ok: boolean | undefined, text: string) => <span className={"pill " + (ok ? "pill-ok" : "pill-off")}>{name}: {text}</span>;
  return (<div>
    <div className="tiles">{tile("📅", years ?? "–", "exam years")}{!DEMO && tile("📝", qs?.length ?? "–", "questions")}{tile("🎯", Math.round(marks ?? 0) || "–", "verified marks")}{tile("🗂️", topics ?? "–", "topics")}
      {!DEMO && tile("✅", qs?.length ? `${Math.round((reviewed / qs.length) * 100)}%` : "–", "review complete")}</div>
    <div className="card cta"><div><small>NEXT STEP</small><h3>{next[0]}</h3></div><button className="primary" onClick={() => setTab(next[1])}>Go →</button></div>
    <h3>Model readiness</h3><div className="row">{pill("TabPFN", tp?.available, tp ? (tp.available ? "ready" : `unavailable (${tp.code})`) : "checking…")}
      {!DEMO && pill("Gemma", m?.gemma?.available, m ? (m.gemma.available ? `ready (${m.gemma.model})` : `unavailable (${m.gemma.code})`) : "checking…")}
      {!DEMO && pill("Telemetry", m?.sentry_enabled, m?.sentry_enabled ? "on (opt-in)" : "off")}</div>
    <p className="note">The deterministic analysis, backtest baselines and study plan work without either model.</p></div>);
}
