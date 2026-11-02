import { useState } from "react";

const EXAMPLES = [{ label: "W3C “Before” demo (inaccessible)", url: "https://www.w3.org/WAI/demos/bad/before/home.html" }];

export default function ScanForm({ onScan, busy }: { onScan: (url: string) => void; busy: boolean }) {
  const [url, setUrl] = useState("");
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const u = url.trim();
    if (u) onScan(/^https?:\/\//i.test(u) ? u : `https://${u}`);
  };
  return (
    <form onSubmit={submit} className="w-full max-w-2xl">
      <label htmlFor="url" className="mb-2 block text-sm font-medium text-slate-300">
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
          className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-slate-100 placeholder-slate-500 focus:border-cyan-400 disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={busy || !url.trim()}
          className="rounded-lg bg-cyan-400 px-6 py-3 font-semibold text-slate-900 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "Working…" : "Scan page"}
        </button>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-slate-400">
        <span>Try:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex.url}
            type="button"
            disabled={busy}
            onClick={() => setUrl(ex.url)}
            className="rounded-full border border-slate-700 px-3 py-1 text-slate-300 hover:border-cyan-400 hover:text-cyan-300"
          >
            {ex.label}
          </button>
        ))}
      </div>
    </form>
  );
}
