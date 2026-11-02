import type { FindingAnalysis, PatchOp, ScanResult, VerifyResult } from "./types";

export const API = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

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

export const scanUrl = (url: string) => post<ScanResult>("/scan", { url });
export const analyze = (scan_id: string) =>
  post<{ scan_id: string; analyses: FindingAnalysis[] }>("/analyze", { scan_id });
export const verify = (scan_id: string, patches: PatchOp[]) =>
  post<VerifyResult>("/verify", { scan_id, patches });

/** Screenshot paths come back as e.g. "scans\\abc.png" on Windows; serve them via /scans/<file>. */
export const shotUrl = (path?: string | null) =>
  path ? `${API}/scans/${path.split(/[\\/]/).pop()}` : "";
