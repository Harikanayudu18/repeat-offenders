import { useEffect, useRef, useState } from "react";
import { api, post, DEMO, J } from "./api";
import { FoldBars, HBar, LineChart } from "./components/charts";
import Dashboard from "./components/Dashboard";

const ICONS: Record<string, string> = { Dashboard: "🏠", Setup: "🧭", Import: "📥", Review: "🏷️", Analytics: "📊", Backtest: "🧪", "Study plan": "🗓️", Privacy: "🔒" };
const HINTS: Record<string, string> = {
  Dashboard: "Your overview: progress, readiness of the local models, and the next thing to do.",
  Setup: "Step 1 — Name your subject and list its units and topics (a unit on its own line, topics start with “-”).",
  Import: "Step 2 — Upload a CSV of past-paper questions (columns: year, marks, question_text). Check the preview, then confirm.",
  Review: "Step 3 — Give every question a topic. Gemma suggestions are optional helpers; nothing counts until you Accept.",
  Analytics: "Step 4 — See which topics keep coming back, by year and by marks.",
  Backtest: "Step 5 — Test how well each ranking would have covered past papers it had not seen (needs 5+ years).",
  "Study plan": "Step 6 — Turn the patterns into a day-by-day plan that never skips a unit.",
  Privacy: "What stays on your computer, and which AI models are ready.",
};
const MODELS = ["naive_frequency", "recency_weighted", "logistic_regression", "tabpfn", "random"];
const pct = (x: number) => (x * 100).toFixed(1) + "%";

function Heatmap({ h }: { h: J }) {
  const mx = Math.max(1, ...h.marks.flat());
  return (<div className="scroll"><table className="hm" aria-label="Topic by year marks heatmap"><thead><tr><th>Topic</th>{h.years.map((y: number) => <th key={y}>{y}</th>)}</tr></thead>
    <tbody>{h.topics.map((t: string, i: number) => (<tr key={t}><th scope="row" style={{ fontWeight: 400, whiteSpace: "nowrap" }}>{t}</th>
      {h.marks[i].map((m: number, j: number) => <td key={j} title={`${m} marks`} style={{ background: `rgba(31,95,74,${m / mx})`, color: m / mx > 0.5 ? "#fff" : "#000" }}>{m ? Math.round(m) : ""}</td>)}</tr>))}</tbody></table></div>);
}

function Analytics({ a }: { a: J }) {
  const rows = [...a.table].sort((x: J, y: J) => y.recency_score - x.recency_score);
  const dist = [0, 1, 2, 3, 4, 5].map(n => ({ label: `${n} of last 5 papers`, value: a.table.filter((r: J) => r.last_5_papers === n).length }));
  return (<>
    {a.unresolved_excluded > 0 && <p className="err">{a.unresolved_excluded} unresolved questions were excluded from this analysis.</p>}
    <h3>Topic × year marks (verified assignments)</h3><Heatmap h={a.heatmap} />
    <h3>Recurrence table (before {a.forecast_year})</h3>
    <div className="scroll"><table><thead><tr><th>Topic</th><th>Unit</th><th>Last paper</th><th>Last 3</th><th>Last 5</th><th>Papers since</th><th>Marks</th><th>Share</th><th>Recency</th></tr></thead>
      <tbody>{rows.map((r: J) => <tr key={r.topic}><td>{r.topic}</td><td>{r.unit}</td><td>{r.last_paper_count}</td><td>{r.last_3_papers}</td><td>{r.last_5_papers}</td>
        <td>{r.papers_since_last ?? "never"}</td><td>{r.total_marks}</td><td>{pct(r.marks_share)}</td><td>{r.recency_score.toFixed(2)}</td></tr>)}</tbody></table></div>
    <h3>Marks by syllabus unit</h3><HBar items={Object.entries(a.unit_marks).map(([u, v]: J) => ({ label: u, value: Number(v) }))} unit="marks" /><h3>How often topics recur</h3><HBar items={dist} unit="topics" /></>);
}

function Backtest({ b }: { b: J }) {
  const d = b.dev;
  if (d.status !== "ok") return <div className="card"><p className="err">{d.message}</p><p className="note">Years with reviewed questions: {d.years?.join(", ") || "none"}. Import and review at least 5 different years (and tick/untick the exclude option carefully: a year with no reviewed questions does not count). The Analytics tab still shows descriptive statistics.</p></div>;
  const f = b.final?.folds?.[0];
  return (<>
    {b.synthetic && <p className="note">Synthetic data: demonstrates the workflow only.</p>}
    <div className="card"><b>TabPFN status:</b> {d.tabpfn_status.available ? "available" : `unavailable (${d.tabpfn_status.code}) — TabPFN was NOT run; its row is empty, not substituted.`}</div>
    <h3>Coverage by number of topics studied</h3><LineChart xs={d.ks} xLabel="Topics studied (K)" yLabel="Mean marks covered" series={MODELS.map(m => ({ name: m, values: d.ks.map((k: number) => (d.aggregate[m].by_k ? d.aggregate[m].by_k[k].mean_coverage : null)) }))} />
    <h3>Coverage in each held-out year (K={d.ks[d.ks.length - 1]})</h3><FoldBars years={d.folds.map((x: J) => x.forecast_year)} xLabel="Held-out year" yLabel="Marks covered" series={MODELS.map(m => ({ name: m, values: d.folds.map((x: J) => (x.models[m].status === "ok" ? x.models[m].metrics[String(d.ks[d.ks.length - 1])].coverage : null)) }))} />
    <h3>Development folds: mean top-K marks coverage ({d.folds.length} folds: {d.folds.map((x: J) => x.forecast_year).join(", ")})</h3>
    <table><thead><tr><th>Model</th><th>Folds</th>{d.ks.map((k: number) => <th key={k}>K={k}</th>)}</tr></thead><tbody>
      {MODELS.map(m => { const g = d.aggregate[m]; return <tr key={m}><td>{m}</td><td>{g.n_folds}/{g.n_folds_total}</td>
        {d.ks.map((k: number) => <td key={k}>{g.by_k ? <><span className="bar" style={{ width: g.by_k[k].mean_coverage * 100 }} /> {pct(g.by_k[k].mean_coverage)} ± {pct(g.by_k[k].std_coverage)}</> : "not run"}</td>)}</tr>; })}</tbody></table>
    <h3>Per-fold results</h3><div className="scroll"><table><thead><tr><th>Year</th><th>Train years</th><th>Marks</th>{MODELS.map(m => <th key={m}>{m} @{d.ks[d.ks.length - 1]}</th>)}</tr></thead><tbody>
      {d.folds.map((x: J) => <tr key={x.forecast_year}><td>{x.forecast_year}</td><td>{x.training_source_years.length}</td><td>{x.held_out_total_marks}</td>
        {MODELS.map(m => { const r = x.models[m]; return <td key={m}>{r.status === "ok" ? pct(r.metrics[String(d.ks[d.ks.length - 1])].coverage) : "unavailable"}</td>; })}</tr>)}</tbody></table></div>
    {f && <><h3>Frozen final holdout: {f.forecast_year} ({f.held_out_total_marks} marks){b.final.reused_frozen_result ? " — stored result reused" : ""}</h3>
      <table><thead><tr><th>Model</th>{d.ks.map((k: number) => <th key={k}>K={k} (covered / total)</th>)}</tr></thead><tbody>{MODELS.map(m => { const r = f.models[m]; return <tr key={m}><td>{m}</td>
        {d.ks.map((k: number) => <td key={k}>{r.status === "ok" ? (r.metrics[k].covered_marks !== undefined ? `${r.metrics[k].covered_marks}/${r.metrics[k].total_marks} = ` : "") + pct(r.metrics[k].coverage) : "unavailable"}</td>)}</tr>; })}</tbody></table></>}
    <p className="note">Few folds ⇒ differences between models are not statistically reliable. A simple baseline winning is a valid result. Coverage on past papers does not promise future coverage.</p></>);
}

function Plan({ p }: { p: J }) {
  if (p.status !== "ok") return <p className="err">{p.message} (needed {p.needed_minutes}, available {p.available_minutes} min)</p>;
  const csv = () => { const t = ["day,session,topic,unit,minutes,unit_floor,reason,action", ...p.sessions.map((s: J) => [s.day, s.session, s.topic, s.unit, s.minutes, s.is_unit_floor, s.reason, s.action].map(v => `"${String(v).replace(/"/g, '""')}"`).join(","))].join("\n");
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([t], { type: "text/csv" })); a.download = "study-plan.csv"; a.click(); };
  return (<><p className="note"><b>{p.notice}</b> Allocated {p.allocated_minutes} of {p.total_minutes} min.</p>
    <button onClick={csv}>Download CSV</button> <button onClick={() => window.print()}>Print</button>
    <div className="scroll"><table><thead><tr><th>Day</th><th>#</th><th>Topic</th><th>Unit</th><th>Min</th><th>Floor?</th><th>Why</th><th>Action</th></tr></thead>
      <tbody>{p.sessions.map((s: J) => <tr key={s.session}><td>{s.day}</td><td>{s.session}</td><td>{s.topic}</td><td>{s.unit}</td><td>{s.minutes}</td><td>{s.is_unit_floor ? "yes" : ""}</td><td>{s.reason}</td><td>{s.action}</td></tr>)}</tbody></table></div></>);
}

function Setup({ onDone }: { onDone: (id: number) => void }) {
  const [name, setName] = useState("My subject"); const [syl, setSyl] = useState("Unit 1\n- Topic A\n- Topic B\nUnit 2\n- Topic C"); const [e, setE] = useState("");
  return (<div><p className="note">Unit names on their own line; topics start with "-".</p>
    <label>Subject <input value={name} onChange={x => setName(x.target.value)} /></label><br /><textarea aria-label="Syllabus" rows={10} cols={50} value={syl} onChange={x => setSyl(x.target.value)} /><br />
    <button className="primary" onClick={() => post("/subjects", { name, syllabus: syl }).then(r => onDone(r.id)).catch(x => setE(x.message))}>Create subject</button><p className="err">{e}</p></div>);
}

function ImportView({ sid, onDone }: { sid: number; onDone: () => void }) {
  const [prev, setPrev] = useState<J>(null); const [e, setE] = useState(""); const [rep, setRep] = useState(false); const [ok, setOk] = useState("");
  const up = (f?: File) => { if (!f) return; const fd = new FormData(); fd.append("file", f); setE(""); setOk("");
    api(`/subjects/${sid}/imports/preview`, { method: "POST", body: fd }).then(setPrev).catch(x => setE(x.message)); };
  return (<div><p className="note">Formats: CSV/XLSX with columns year, marks, question_text (optional question_number, topic); or TXT/DOCX/text-PDF with lines like “1. question text [5 marks]” under a “YEAR 2021” line. Scanned PDFs are not supported. Files stay on this computer.</p>
    <input type="file" accept=".csv,.xlsx,.docx,.txt,.pdf" aria-label="Past paper file" onChange={x => up(x.target.files?.[0])} /><p className="err">{e}</p>
    {prev && <div className="card">Years: {prev.years.join(", ")} · {prev.rows.length} valid rows · {prev.invalid.length} invalid{prev.invalid.length > 0 && ` (lines ${prev.invalid.slice(0, 10).map((i: J) => i.line).join(", ")})`}
      {prev.existing_years.length > 0 && <p className="err">Papers for {prev.existing_years.join(", ")} already exist. <label><input type="checkbox" checked={rep} onChange={x => setRep(x.target.checked)} /> Replace them</label></p>}
      <br /><button className="primary" disabled={!prev.can_confirm || (prev.existing_years.length > 0 && !rep)} onClick={() => post(`/subjects/${sid}/imports/confirm`, { rows: prev.rows, on_duplicate: rep ? "replace" : "cancel" }).then(r => { setOk(`Imported ${r.imported} questions`); setPrev(null); onDone(); }).catch(x => setE(x.message))}>Confirm import</button></div>}
    <p>{ok}</p></div>);
}

const band = (c: number | null) => (c == null ? "mapped" : c >= 0.8 ? "high" : c >= 0.5 ? "medium" : "low");

function Review({ sid }: { sid: number }) {
  const [qs, setQs] = useState<J[]>([]); const [ts, setTs] = useState<J[]>([]); const [sel, setSel] = useState<Record<number, [string, string]>>({});
  const [msg, setMsg] = useState<Record<number, string>>({}); const [busy, setBusy] = useState<Record<number, boolean>>({});
  const [gem, setGem] = useState<J>(null); const [filter, setFilter] = useState<"todo" | "all">("todo");
  const [prog, setProg] = useState<{ done: number; total: number } | null>(null); const [top, setTop] = useState("");
  const stop = useRef(false);
  const load = () => { api(`/subjects/${sid}/questions`).then(setQs).catch(x => setTop(x.message)); api(`/subjects/${sid}/topics`).then(setTs); api("/system/models").then(m => setGem(m.gemma)).catch(() => { }); };
  useEffect(load, [sid]);
  const say = (id: number, m: string) => setMsg(s => ({ ...s, [id]: m }));
  const accept = (q: J, ids?: number[]) => {
    const [a, b] = sel[q.id] ?? ["", ""]; const picks = ids ?? [a, b].filter(Boolean).map(Number);
    if (!picks.length) return say(q.id, "Choose a topic first.");
    const u = [...new Set(picks)]; const as = u.map(t => ({ topic_id: t, weight: 1 / u.length }));
    return post(`/questions/${q.id}/review`, { decision: "accept", assignments: as }).then(() => { say(q.id, ""); load(); }).catch(x => say(q.id, x.message));
  };
  const suggest = async (q: J): Promise<string | null> => {
    setBusy(s => ({ ...s, [q.id]: true })); say(q.id, "Gemma is thinking… (can take up to a minute on a laptop CPU)");
    try {
      const r = await post(`/questions/${q.id}/suggestions`, {});
      if (r.error) { say(q.id, `Gemma could not help (${r.error}): ${r.message}. Pick a topic manually.`); return r.error; }
      say(q.id, r.suggestions.length ? "" : "Gemma had no confident suggestion. Pick a topic manually."); load(); return null;
    } catch (x) { say(q.id, (x as Error).message); return "error"; } finally { setBusy(s => ({ ...s, [q.id]: false })); }
  };
  const suggestAll = async () => {
    const todo = qs.filter(q => q.status !== "reviewed" && !q.assignments.some((a: J) => a.source === "gemma")); stop.current = false; setProg({ done: 0, total: todo.length });
    for (let i = 0; i < todo.length && !stop.current; i++) { const e = await suggest(todo[i]); setProg({ done: i + 1, total: todo.length }); if (e === "unavailable" || e === "model_missing") { setTop("Gemma is not reachable, so batch suggesting was stopped. Start Ollama (see Privacy tab) or assign manually."); break; } }
    setProg(null);
  };
  const acceptAll = async () => {
    for (const q of qs) {
      if (q.status === "reviewed") continue;
      const sg = q.assignments.filter((a: J) => a.decision === "suggested" && (a.confidence == null || a.confidence >= 0.5)); if (!sg.length) continue;
      const best = sg.reduce((m: J, a: J) => ((a.confidence ?? 1) > (m.confidence ?? 1) ? a : m));
      await post(`/questions/${q.id}/review`, { decision: "accept", assignments: [{ topic_id: best.topic_id, weight: 1 }] }).catch(() => { });
    }
    load();
  };
  const tn = (id: number) => ts.find(t => t.id === id)?.name ?? "?";
  const done = qs.filter(q => q.status === "reviewed").length; const shown = filter === "all" ? qs : qs.filter(q => q.status !== "reviewed");
  const gemOk = gem?.available;
  return (<div>
    <div className="card help"><b>What do the buttons do?</b>
      <ul><li><b>Accept</b> — saves the topic you picked (or a suggestion) for that question. Only accepted topics are counted in the analysis.</li>
        <li><b>Suggest with Gemma</b> — asks the AI model running on <i>your own computer</i> (Ollama) to propose a topic. It only suggests; you still click Accept.</li>
        <li><b>Can't decide?</b> Press <i>Skip / unresolved</i>; unresolved questions are left out only if you tick the exclude box.</li></ul>
      <p className={gemOk ? "ok" : "err"}>{gem == null ? "Checking Gemma…" : gemOk ? `Gemma ready (${gem.model}).` : gem.code === "model_missing" ? `Gemma model not installed. Run: ollama pull ${gem.model ?? "gemma3:4b"}` : "Gemma not running. Start Ollama, or just assign topics manually — everything else works."}</p></div>
    <div className="progress" aria-label="Review progress"><div style={{ width: `${qs.length ? (done / qs.length) * 100 : 0}%` }} /></div>
    <p><b>{done}/{qs.length}</b> reviewed</p>
    <div className="row"><button className="primary" disabled={!gemOk || !!prog} title={gemOk ? "" : "Gemma is not available"} onClick={suggestAll}>Suggest with Gemma for all pending</button>
      {prog && <><span>Asking Gemma {prog.done}/{prog.total}…</span><button onClick={() => { stop.current = true; }}>Stop</button></>}
      <button onClick={acceptAll}>Accept all medium/high suggestions (I reviewed them)</button>
      <select aria-label="Filter" value={filter} onChange={x => setFilter(x.target.value as "todo" | "all")}><option value="todo">Show: needs review</option><option value="all">Show: all questions</option></select></div>
    {top && <p className="err" role="alert">{top}</p>}
    {shown.length === 0 && <p className="ok">Nothing left to review 🎉 — continue to the Analytics tab.</p>}
    {shown.map(q => <div className="card q" key={q.id}>
      <div className="qhead"><span className="badge">{q.year}</span><b>Q{q.question_number}</b><span className="badge">{q.marks} marks</span><span className={"badge st-" + q.status}>{q.status}</span></div>
      <p className="qtext">{q.question_text}</p>
      {q.assignments.filter((a: J) => a.decision === "accepted").map((a: J, i: number) => <p key={i} className="ok">✓ Accepted: <b>{tn(a.topic_id)}</b> {a.weight < 1 && `(${Math.round(a.weight * 100)}%)`} <span className="note">[{a.source}]</span></p>)}
      {q.assignments.filter((a: J) => a.decision === "suggested").map((a: J, i: number) => <div className="chip" key={i}>
        <span className={"badge b-" + band(a.confidence)}>{a.source === "gemma" ? `Gemma · ${band(a.confidence)}` : "From your CSV"}</span> <b>{tn(a.topic_id)}</b>
        <button disabled={q.status === "reviewed"} onClick={() => accept(q, [a.topic_id])}>Accept this</button></div>)}
      <div className="row">{[0, 1].map(i => <select key={i} aria-label={`Topic ${i + 1} for question ${q.question_number}`} value={(sel[q.id] ?? ["", ""])[i]} onChange={x => setSel(s => { const c = [...(s[q.id] ?? ["", ""])] as [string, string]; c[i] = x.target.value; return { ...s, [q.id]: c }; })}>
        <option value="">{i ? "(optional 2nd topic)" : "Choose topic…"}</option>{ts.map(t => <option key={t.id} value={t.id}>{t.unit}: {t.name}</option>)}</select>)}
        <button className="primary" onClick={() => accept(q)}>Accept</button>
        <button disabled={!gemOk || busy[q.id]} title={gemOk ? "Ask local Gemma for a suggestion" : "Gemma is not available"} onClick={() => suggest(q)}>{busy[q.id] ? "Thinking…" : "Suggest with Gemma"}</button>
        <button onClick={() => post(`/questions/${q.id}/review`, { decision: "unresolved" }).then(load)}>Skip / unresolved</button></div>
      {msg[q.id] && <p className={busy[q.id] ? "note" : "err"} role="status">{msg[q.id]}</p>}</div>)}</div>);
}

function Privacy({ models }: { models: J }) {
  return (<div><h3>Privacy</h3><ul><li>{DEMO ? "Public Demo: synthetic data only; no uploads; nothing is stored." : "Local Workspace: papers stay in your local SQLite file; Gemma runs through your local Ollama."}</li>
    <li>No telemetry unless you set SENTRY_DSN. Sentry never receives question text, prompts or filenames (numeric/stage metadata only).</li></ul>
    {models && <div className="card"><b>Model status</b><br />TabPFN: {models.tabpfn.available ? "available" : `unavailable (${models.tabpfn.code})`}<br />Gemma: {models.gemma.available ? "ready" : `unavailable (${models.gemma.code})`}<br />Sentry: {models.sentry_enabled ? "enabled (opt-in)" : "off"}<br /><span className="note">{models.note}</span></div>}</div>);
}

export default function App() {
  const tabs = DEMO ? ["Dashboard", "Analytics", "Backtest", "Study plan", "Privacy"] : ["Dashboard", "Setup", "Import", "Review", "Analytics", "Backtest", "Study plan", "Privacy"];
  const [tab, setTab] = useState("Dashboard"); const [fx, setFx] = useState<J>(null); const [sid, setSid] = useState<number | null>(null); const [subs, setSubs] = useState<J[]>([]);
  const [a, setA] = useState<J>(null); const [b, setB] = useState<J>(null); const [p, setP] = useState<J>(null); const [models, setModels] = useState<J>(null);
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false); const [excl, setExcl] = useState(false); const [fin, setFin] = useState(false);
  const [pi, setPi] = useState({ days: 7, daily_minutes: 60, unit_floor_minutes: 15 });
  useEffect(() => { if (DEMO) fetch("demo-fixture.json").then(r => r.json()).then(setFx).catch(() => setErr("Could not load demo fixture")); else { api("/subjects").then(s => { setSubs(s); if (s.length && !sid) setSid(s[0].id); }).catch(x => setErr(x.message)); api("/system/models").then(setModels).catch(() => { }); } }, [tab]);
  const run = (f: () => Promise<void>) => { setBusy(true); setErr(""); f().catch(x => setErr(x.message)).finally(() => setBusy(false)); };
  const A = DEMO ? fx?.analytics : a, B = DEMO ? fx?.backtest : b, P = DEMO ? fx?.plan : p;
  const need = !DEMO && sid == null;
  return (<><div className={"banner" + (DEMO ? " demo" : "")}>{DEMO ? "Public Demo — SYNTHETIC data, read-only, no uploads" : "Local Workspace — your data stays on this computer"}</div>
    <header className="hero"><div><h1><span aria-hidden="true">🔁</span> Repeat Offenders</h1><p>Study the pattern, not the prediction.</p><div className="chips"><span>Local-first</span><span>Open-weight AI</span><span>Honest backtests</span></div></div></header>
    <main>{DEMO && <p className="note">{fx?.notice}</p>}
      {!DEMO && subs.length > 0 && <label>Subject <select value={sid ?? ""} onChange={x => { setSid(+x.target.value); setA(null); setB(null); setP(null); }}>{subs.map(s => <option key={s.id} value={s.id}>{s.name} ({s.questions} q)</option>)}</select></label>}
      {!DEMO && <p><label><input type="checkbox" checked={excl} onChange={x => setExcl(x.target.checked)} /> Exclude unresolved questions from analysis, backtest and study plan (otherwise finish reviewing them in the Review tab)</label></p>}
      <nav aria-label="Sections">{tabs.map(t => <button key={t} className={t === tab ? "on" : ""} onClick={() => setTab(t)}><span aria-hidden="true">{ICONS[t]}</span> {t}</button>)}</nav>
      <p className="hint">{HINTS[tab]}</p>
      {err && <p className="err" role="alert">{err}</p>}{busy && <p>Working…</p>}
      {tab === "Dashboard" && <Dashboard sid={sid} fx={fx} setTab={setTab} />}
      {tab === "Setup" && <Setup onDone={id => { setSid(id); setTab("Import"); }} />}
      {tab === "Import" && (need ? <p>Create a subject first.</p> : <ImportView sid={sid!} onDone={() => { }} />)}
      {tab === "Review" && (need ? <p>Create a subject first.</p> : <Review sid={sid!} />)}
      {tab === "Analytics" && <>{!DEMO && !need && <p><button className="primary" onClick={() => run(async () => setA(await api(`/subjects/${sid}/analytics?exclude_unresolved=${excl}`)))}>Build analysis</button></p>}{A ? <Analytics a={A} /> : <p>{DEMO ? "Loading…" : "No analysis yet. Import and review papers, then build."}</p>}</>}
      {tab === "Backtest" && <>{!DEMO && !need && <p><label><input type="checkbox" checked={fin} onChange={x => setFin(x.target.checked)} /> Also evaluate the frozen final year (runs once; result is stored)</label> <button className="primary" onClick={() => run(async () => setB(await post(`/subjects/${sid}/backtests`, { include_final: fin, exclude_unresolved: excl })))}>Run backtest</button></p>}{B ? <Backtest b={B} /> : <p>{DEMO ? "Loading…" : "Not run yet."}</p>}</>}
      {tab === "Study plan" && <>{!DEMO && !need && <p>{(["days", "daily_minutes", "unit_floor_minutes"] as const).map(k => <label key={k}>{k.replace(/_/g, " ")} <input type="number" min={1} style={{ width: 70 }} value={pi[k]} onChange={x => setPi({ ...pi, [k]: +x.target.value })} /> </label>)}<button className="primary" onClick={() => run(async () => setP(await post(`/subjects/${sid}/study-plans`, { ...pi, exclude_unresolved: excl })))}>Generate plan</button></p>}{P ? <Plan p={P} /> : <p>{DEMO ? "Loading…" : "No plan yet."}</p>}</>}
      {tab === "Privacy" && <Privacy models={models} />}
    </main></>);
}
