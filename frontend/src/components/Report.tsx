import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { FindingAnalysis, PatchOp, ScanResult, VerifyResult } from "../types";
import { CATEGORY_LABEL } from "../ui";
import { shotUrl } from "../api";

const ruleOf = (id: string) => id.split(":")[0];

export default function Report({
  scan,
  result,
  applied,
  analyses,
  onBack,
  onReset,
}: {
  scan: ScanResult;
  result: VerifyResult;
  applied: PatchOp[];
  analyses: Map<string, FindingAnalysis>;
  onBack: () => void;
  onReset: () => void;
}) {
  const ruleCat = new Map(scan.findings.map((f) => [f.rule_id, f.category]));
  const label = (id: string) => CATEGORY_LABEL[ruleCat.get(ruleOf(id)) ?? ""] ?? ruleOf(id);
  const before = [...result.resolved, ...result.remaining];
  const after = [...result.remaining, ...result.introduced];
  const cats = Array.from(new Set([...before, ...after].map(label)));
  const chart = cats.map((c) => ({
    category: c,
    Before: before.filter((id) => label(id) === c).length,
    After: after.filter((id) => label(id) === c).length,
  }));
  const reduction = result.before_count ? Math.round((result.resolved.length / result.before_count) * 100) : 0;

  const download = () => {
    const blob = new Blob(
      [JSON.stringify({ url: scan.url, scan_id: scan.scan_id, verification: result, applied_patches: applied }, null, 2)],
      { type: "application/json" }
    );
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `accesslens-report-${scan.scan_id}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-slate-100">Verification report</h2>
          <p className="text-sm text-slate-400">{scan.url}</p>
        </div>
        <div className="flex gap-2">
          <button onClick={onBack} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-400">
            ← Back to review
          </button>
          <button onClick={download} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-400">
            Download JSON
          </button>
          <button onClick={onReset} className="rounded-lg bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-cyan-300">
            Scan another page
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat label="Before" value={result.before_count} />
        <Stat label="After" value={result.after_count} />
        <Stat label="Resolved" value={result.resolved.length} tone="good" />
        <Stat label="Still failing" value={result.remaining.length} tone="warn" />
        <Stat label="Newly introduced" value={result.introduced.length} tone={result.introduced.length ? "bad" : "good"} />
      </div>
      <p className="text-slate-300">
        {result.resolved.length} of {result.before_count} detected issues ({reduction}%) no longer fail automated checks after the {applied.length} approved
        change{applied.length === 1 ? "" : "s"}.{" "}
        {result.introduced.length === 0 ? "No new violations were introduced." : `${result.introduced.length} new violation(s) appeared and need attention.`}
      </p>

      {result.failed_ops.length > 0 && (
        <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
          {result.failed_ops.length} change(s) could not be applied because their target element was not found.
        </p>
      )}

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">Issues by category</h3>
        <div style={{ width: "100%", height: 280 }}>
          <ResponsiveContainer>
            <BarChart data={chart} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="category" tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", color: "#e2e8f0" }} />
              <Legend />
              <Bar dataKey="Before" fill="#f97316" radius={[4, 4, 0, 0]} />
              <Bar dataKey="After" fill="#22d3ee" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Shot title="Before" src={shotUrl(result.before_screenshot)} />
        <Shot title="After (approved changes applied)" src={shotUrl(result.after_screenshot)} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <IdList title="Resolved" ids={result.resolved} tone="text-emerald-300" label={label} analyses={analyses} />
        <IdList title="Still failing" ids={result.remaining} tone="text-amber-300" label={label} analyses={analyses} />
        <IdList title="Newly introduced" ids={result.introduced} tone="text-red-300" label={label} analyses={analyses} />
      </div>

      <aside className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-400">
        <strong className="text-slate-200">What this verification means.</strong> Results come from re-running axe-core on an isolated, script-free copy of the
        page with your approved changes applied. This confirms the detected rule violations are gone — it does not prove WCAG compliance, and it cannot judge
        whether AI-written text (such as alt text) is actually good. Review wording yourself and test with real assistive technology. The live website was never
        modified.
      </aside>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: "good" | "warn" | "bad" }) {
  const c = tone === "good" ? "text-emerald-300" : tone === "warn" ? "text-amber-300" : tone === "bad" ? "text-red-300" : "text-slate-100";
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className={`mt-1 text-3xl font-semibold ${c}`}>{value}</div>
    </div>
  );
}

function Shot({ title, src }: { title: string; src: string }) {
  return (
    <figure className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
      <figcaption className="mb-2 text-xs uppercase tracking-wide text-slate-400">{title}</figcaption>
      <img src={src} alt={`${title} screenshot`} className="w-full rounded bg-white" />
    </figure>
  );
}

function IdList({
  title,
  ids,
  tone,
  label,
  analyses,
}: {
  title: string;
  ids: string[];
  tone: string;
  label: (id: string) => string;
  analyses: Map<string, FindingAnalysis>;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
      <h3 className={`mb-2 text-sm font-semibold ${tone}`}>
        {title} ({ids.length})
      </h3>
      {ids.length === 0 ? (
        <p className="text-sm text-slate-500">None</p>
      ) : (
        <ul className="max-h-60 space-y-1 overflow-auto text-sm text-slate-300">
          {ids.map((id) => {
            const p = analyses.get(id)?.patch;
            return (
              <li key={id} className="truncate" title={id}>
                {label(id)} <span className="font-mono text-xs text-slate-500">{id.split(":")[1]}</span>
                {p && p.op === "set_attribute" && p.value && <span className="text-slate-400"> — “{p.value}”</span>}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
