export const DEMO = import.meta.env.VITE_DEMO_MODE === "true";
const BASE = import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type J = any;
export async function api(path: string, opts: RequestInit = {}): Promise<J> {
  if (DEMO) throw new Error("Disabled in the public demo (no backend, no uploads).");
  let r: Response;
  try { r = await fetch(BASE + "/api/v1" + path, opts); }
  catch { throw new Error("Cannot reach the local backend. Start it with scripts/start_unix.sh (or start_windows.ps1)."); }
  if (r.status === 204) return null;
  const j = await r.json().catch(() => null);
  if (!r.ok) throw new Error(j?.error?.message ?? `Request failed (${r.status})`);
  return j;
}
export const post = (p: string, body: J) => api(p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
