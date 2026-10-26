import type { J } from "../api";

export const MODEL_COLORS: Record<string, string> = { naive_frequency: "#6366f1", recency_weighted: "#f59e0b", logistic_regression: "#10b981", tabpfn: "#ec4899", random: "#94a3b8" };
export const MODEL_LABELS: Record<string, string> = { naive_frequency: "Naive frequency", recency_weighted: "Recency-weighted", logistic_regression: "Logistic regression", tabpfn: "TabPFN", random: "Random (mean of 20 seeds)" };
const W = 560, H = 280, L = 46, R = 14, T = 14, B = 46;
const pct = (v: number) => `${Math.round(v * 100)}%`;

export function Empty({ text }: { text: string }) { return <div className="empty" role="status">{text}</div>; }

function Legend({ names, missing }: { names: string[]; missing: Set<string> }) {
  return <div className="legend">{names.map(n => <span key={n}><i style={{ background: MODEL_COLORS[n] ?? "#888" }} />{MODEL_LABELS[n] ?? n}{missing.has(n) ? " — not run" : ""}</span>)}</div>;
}

type Series = { name: string; values: (number | null)[] };

function Table({ xs, series, xHead }: { xs: (string | number)[]; series: Series[]; xHead: string }) {
  return <details><summary>View as table</summary><div className="scroll"><table><thead><tr><th>{xHead}</th>{series.map(s => <th key={s.name}>{MODEL_LABELS[s.name] ?? s.name}</th>)}</tr></thead>
    <tbody>{xs.map((x, i) => <tr key={x}><td>{x}</td>{series.map(s => <td key={s.name}>{s.values[i] == null ? "not run" : pct(s.values[i]!)}</td>)}</tr>)}</tbody></table></div></details>;
}

function Axes({ yTicks = [0, 0.25, 0.5, 0.75, 1], xLabel, yLabel }: { yTicks?: number[]; xLabel: string; yLabel: string }) {
  const y = (v: number) => T + (1 - v) * (H - T - B);
  return <g className="axes">{yTicks.map(t => <g key={t}><line x1={L} x2={W - R} y1={y(t)} y2={y(t)} /><text x={L - 6} y={y(t) + 4} textAnchor="end">{pct(t)}</text></g>)}
    <text x={(L + W - R) / 2} y={H - 6} textAnchor="middle" className="lbl">{xLabel}</text>
    <text transform={`translate(12 ${(T + H - B) / 2}) rotate(-90)`} textAnchor="middle" className="lbl">{yLabel}</text></g>;
}

export function LineChart({ xs, series, xLabel, yLabel }: { xs: number[]; series: Series[]; xLabel: string; yLabel: string }) {
  if (!xs.length || !series.some(s => s.values.some(v => v != null))) return <Empty text="No results to chart yet." />;
  const x = (i: number) => L + (xs.length === 1 ? (W - L - R) / 2 : (i * (W - L - R)) / (xs.length - 1));
  const y = (v: number) => T + (1 - v) * (H - T - B);
  return <figure className="chart"><svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${yLabel} by ${xLabel}`}><Axes xLabel={xLabel} yLabel={yLabel} />
    {xs.map((k, i) => <text key={k} x={x(i)} y={H - B + 16} textAnchor="middle">{k}</text>)}
    {series.map(s => { const pts = s.values.map((v, i) => (v == null ? null : [x(i), y(v)])).filter(Boolean) as number[][]; const c = MODEL_COLORS[s.name] ?? "#888";
      return <g key={s.name}><polyline fill="none" stroke={c} strokeWidth={2.5} strokeDasharray={s.name === "random" ? "5 4" : undefined} points={pts.map(p => p.join(",")).join(" ")} />
        {pts.map((p, i) => <circle key={i} cx={p[0]} cy={p[1]} r={4} fill={c} />)}</g>; })}</svg>
    <Legend names={series.map(s => s.name)} missing={new Set(series.filter(s => s.values.every(v => v == null)).map(s => s.name))} />
    <Table xs={xs} series={series} xHead={xLabel} /></figure>;
}

export function FoldBars({ years, series, xLabel, yLabel }: { years: number[]; series: Series[]; xLabel: string; yLabel: string }) {
  if (!years.length || !series.some(s => s.values.some(v => v != null))) return <Empty text="No folds to chart yet." />;
  const gw = (W - L - R) / years.length, bw = Math.min(18, (gw - 8) / series.length), y = (v: number) => T + (1 - v) * (H - T - B);
  return <figure className="chart"><svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${yLabel} per ${xLabel}`}><Axes xLabel={xLabel} yLabel={yLabel} />
    {years.map((yr, i) => <g key={yr}><text x={L + gw * i + gw / 2} y={H - B + 16} textAnchor="middle">{yr}</text>
      {series.map((s, j) => { const v = s.values[i]; if (v == null) return null; const bx = L + gw * i + (gw - bw * series.length) / 2 + bw * j;
        return <rect key={s.name} x={bx} y={y(v)} width={bw - 2} height={H - B - y(v)} rx={3} fill={MODEL_COLORS[s.name] ?? "#888"}><title>{`${MODEL_LABELS[s.name] ?? s.name}, ${yr}: ${pct(v)}`}</title></rect>; })}</g>)}</svg>
    <Legend names={series.map(s => s.name)} missing={new Set(series.filter(s => s.values.every(v => v == null)).map(s => s.name))} />
    <Table xs={years} series={series} xHead={xLabel} /></figure>;
}

export function HBar({ items, unit }: { items: { label: string; value: number }[]; unit: string }) {
  const mx = Math.max(0, ...items.map(i => i.value));
  if (!items.length || mx === 0) return <Empty text="Nothing to show yet." />;
  return <div className="hbar" role="list">{items.map(i => <div key={i.label} role="listitem"><span className="hl">{i.label}</span>
    <span className="ht"><span style={{ width: `${(i.value / mx) * 100}%` }} /></span><b>{Math.round(i.value)} {unit}</b></div>)}</div>;
}

export type { J };
