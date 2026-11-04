import type { FindingAnalysis, PatchOp, ScanResult, VerifyResult } from "./types";

export const API = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

/** Static demo mode (vite --mode demo): replay a recorded real run from /demo/*.json, no backend. */
export const DEMO = import.meta.env.VITE_DEMO === "1";
export const DEMO_URL =
  (import.meta.env.VITE_DEMO_URL as string | undefined) ?? "https://www.w3.org/WAI/demos/bad/before/home.html";
const demoFile = (name: string) => `${import.meta.env.BASE_URL}demo/${name}`;
async function demoJson<T>(name: string): Promise<T> {
  const res = await fetch(demoFile(name));
  if (!res.ok) throw new Error("Demo data is missing. Run export_demo.py, then rebuild with npm run build:demo.");
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error("Cannot reach the AccessLens server. Is the backend running?");
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const j = await res.json();
      if (j.detail) msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail).slice(0, 300);
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export const scanUrl = (url: string) => (DEMO ? demoJson<ScanResult>("scan.json") : post<ScanResult>("/scan", { url }));
export interface AnalyzeResponse {
  scan_id: string;
  analyses: FindingAnalysis[];
  source?: "live" | "cache";
  cached_at?: string | null;
}
export const analyze = (scan_id: string) =>
  DEMO ? demoJson<AnalyzeResponse>("analysis.json") : post<AnalyzeResponse>("/analyze", { scan_id });
export const verify = (scan_id: string, patches: PatchOp[]) =>
  DEMO ? demoJson<VerifyResult>("verify.json") : post<VerifyResult>("/verify", { scan_id, patches });

/** Screenshot paths come back as e.g. "scans\\abc.png" on Windows; serve them via /scans/<file>. */
export const shotUrl = (path?: string | null) => {
  if (!path) return "";
  const name = path.split(/[\\/]/).pop();
  return DEMO ? demoFile(name ?? "") : `${API}/scans/${name}`;
};
