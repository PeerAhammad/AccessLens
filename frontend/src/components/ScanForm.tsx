import { useState } from "react";
import { DEMO, DEMO_URL } from "../api";

const EXAMPLES = [{ label: "W3C “Before” demo (inaccessible)", url: "https://www.w3.org/WAI/demos/bad/before/home.html" }];

export default function ScanForm({ onScan, busy }: { onScan: (url: string) => void; busy: boolean }) {
  const [url, setUrl] = useState("");
  if (DEMO) {
    return (
      <div className="w-full max-w-2xl rounded-xl border border-teal-200 bg-teal-50 dark:border-brand/30 dark:bg-brand/5 p-5 text-left">
        <p className="text-sm text-ink-2">
          This hosted page is a <strong className="text-ink">static demo</strong>: it replays a real recorded run so you can explore the full flow without
          a server. The live app (scan any URL) runs from the GitHub repo or Docker image.
        </p>
        <p className="mt-3 break-all font-mono text-xs text-ink-3">{DEMO_URL}</p>
        <button
          onClick={() => onScan(DEMO_URL)}
          disabled={busy}
          className="mt-4 rounded-lg bg-brand px-6 py-3 font-semibold text-brand-ink hover:bg-brand/90 disabled:opacity-50"
        >
          Run the recorded demo
        </button>
      </div>
    );
  }
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const u = url.trim();
    if (u) onScan(/^https?:\/\//i.test(u) ? u : `https://${u}`);
  };
  return (
    <form onSubmit={submit} className="w-full max-w-2xl">
      <label htmlFor="url" className="mb-2 block text-sm font-medium text-ink-2">
        Website URL
      </label>
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          id="url"
          type="text"
          inputMode="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com"
          disabled={busy}
          className="flex-1 rounded-lg border border-line-strong bg-surface px-4 py-3 text-ink placeholder-ink-3 focus:border-brand disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={busy || !url.trim()}
          className="rounded-lg bg-brand px-6 py-3 font-semibold text-brand-ink transition hover:bg-brand/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "Working…" : "Scan page"}
        </button>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-ink-3">
        <span>Try:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex.url}
            type="button"
            disabled={busy}
            onClick={() => setUrl(ex.url)}
            className="rounded-full border border-line-strong px-3 py-1 text-ink-2 hover:border-brand hover:text-brand-text"
          >
            {ex.label}
          </button>
        ))}
      </div>
    </form>
  );
}
