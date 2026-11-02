import type { Finding, FindingAnalysis } from "../types";
import { CATEGORY_LABEL, SEV_STYLE } from "../ui";
import { shotUrl } from "../api";

const CONF: Record<string, string> = {
  high: "bg-emerald-500/15 text-emerald-300",
  medium: "bg-amber-500/15 text-amber-300",
  low: "bg-red-500/15 text-red-300",
};

export default function DetailPanel({
  finding,
  analysis,
  approved,
  onToggle,
  editValue,
  onEdit,
}: {
  finding: Finding | null;
  analysis?: FindingAnalysis;
  approved: boolean;
  onToggle: () => void;
  editValue?: string;
  onEdit: (v: string) => void;
}) {
  if (!finding) {
    return (
      <div className="rounded-xl border border-dashed border-slate-700 p-8 text-center text-slate-400">
        Select an issue from the list or the screenshot to see the explanation and proposed fix.
      </div>
    );
  }
  const patch = analysis?.patch;
  const e = analysis?.explanation;
  const editable = patch?.op === "set_attribute";
  const value = editValue ?? patch?.value ?? "";
  return (
    <section className="space-y-5 rounded-xl border border-slate-800 bg-slate-900/60 p-5" aria-label="Issue details">
      <header>
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-md px-2 py-0.5 text-xs ring-1 ${SEV_STYLE[finding.severity].badge}`}>{finding.severity}</span>
          <h2 className="text-lg font-semibold text-slate-100">{CATEGORY_LABEL[finding.category] ?? finding.category}</h2>
          {finding.wcag.map((w) => (
            <span key={w} className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
              WCAG {w}
            </span>
          ))}
        </div>
        <a href={finding.help_url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-xs text-cyan-300 hover:underline">
          axe rule: {finding.rule_id} ↗
        </a>
      </header>

      {finding.crop_path && (
        <div>
          <div className="mb-1 text-xs uppercase tracking-wide text-slate-400">The image in question</div>
          <img src={shotUrl(finding.crop_path)} alt="Cropped screenshot of the flagged image" className="max-h-28 rounded border border-slate-700 bg-white" />
        </div>
      )}

      {e ? (
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <Block t="What is wrong" v={e.what} />
          <Block t="Why it matters" v={e.why} />
          <Block t="Who is affected" v={e.who} />
          <Block t="How to fix it" v={e.how} />
        </dl>
      ) : (
        <p className="text-sm text-slate-400">AI explanation not available for this issue.</p>
      )}

      {analysis && (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full bg-slate-800 px-2.5 py-1 text-slate-300">
            {analysis.patch_source === "deterministic" ? "Fix computed by rule (not AI)" : analysis.patch_source === "llm" ? "Fix written by AI" : "No automatic fix"}
          </span>
          <span className={`rounded-full px-2.5 py-1 ${CONF[analysis.confidence]}`}>confidence: {analysis.confidence}</span>
          {analysis.needs_human_review && <span className="rounded-full bg-amber-500/15 px-2.5 py-1 text-amber-300">human review recommended</span>}
        </div>
      )}
      {analysis?.evidence && <p className="text-xs text-slate-400">Evidence used: {analysis.evidence}</p>}
      {analysis?.note && <p className="text-xs text-amber-300/90">Note: {analysis.note}</p>}

      <div className="grid gap-3 lg:grid-cols-2">
        <Code title="Original" code={analysis?.original_html ?? finding.html.replace(/\s*data-al-id="al\d+"/g, "")} tone="red" />
        <Code title="Proposed" code={analysis?.proposed_html ?? "No automatic fix was proposed for this issue."} tone="green" />
      </div>

      {editable && patch && (
        <div>
          <label htmlFor="edit" className="mb-1 block text-xs uppercase tracking-wide text-slate-400">
            Edit the <code className="text-cyan-300">{patch.name}</code> value before approving
            {patch.name === "alt" && " (leave empty to mark the image as decorative)"}
          </label>
          <input
            id="edit"
            value={value}
            onChange={(ev) => onEdit(ev.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-slate-100 focus:border-cyan-400"
          />
        </div>
      )}

      <button
        onClick={onToggle}
        disabled={!patch}
        className={`w-full rounded-lg px-4 py-3 font-semibold transition disabled:cursor-not-allowed disabled:opacity-40 ${
          approved ? "bg-slate-700 text-slate-100 hover:bg-slate-600" : "bg-cyan-400 text-slate-900 hover:bg-cyan-300"
        }`}
      >
        {!patch ? "No fix to approve" : approved ? "Approved ✓ (click to remove)" : "Approve this fix"}
      </button>
    </section>
  );
}

function Block({ t, v }: { t: string; v: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-400">{t}</dt>
      <dd className="mt-0.5 text-slate-200">{v}</dd>
    </div>
  );
}

function Code({ title, code, tone }: { title: string; code: string; tone: "red" | "green" }) {
  return (
    <div className={`rounded-lg border p-3 ${tone === "red" ? "border-red-500/30 bg-red-500/5" : "border-emerald-500/30 bg-emerald-500/5"}`}>
      <div className={`mb-1 text-xs font-semibold uppercase tracking-wide ${tone === "red" ? "text-red-300" : "text-emerald-300"}`}>{title}</div>
      <pre className="whitespace-pre-wrap break-all font-mono text-xs text-slate-200">{code}</pre>
    </div>
  );
}
