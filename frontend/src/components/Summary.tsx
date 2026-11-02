import type { Finding, FindingAnalysis } from "../types";
import { SEV_ORDER, SEV_STYLE } from "../ui";

export default function Summary({ findings, analyses }: { findings: Finding[]; analyses: Map<string, FindingAnalysis> }) {
  const fixable = findings.filter((f) => analyses.get(f.id)?.patch).length;
  const counts = SEV_ORDER.map((s) => ({ s, n: findings.filter((f) => f.severity === s).length }));
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      <Card label="Issues found" value={findings.length} />
      {counts.map(({ s, n }) => (
        <Card key={s} label={s} value={n} dot={SEV_STYLE[s].dot} />
      ))}
      <Card label="Fix proposed" value={fixable} accent />
    </div>
  );
}

function Card({ label, value, dot, accent }: { label: string; value: number; dot?: string; accent?: boolean }) {
  return (
    <div className={`rounded-xl border p-4 ${accent ? "border-cyan-500/40 bg-cyan-500/5" : "border-slate-800 bg-slate-900/60"}`}>
      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-400">
        {dot && <span className={`h-2 w-2 rounded-full ${dot}`} />}
        {label}
      </div>
      <div className="mt-1 text-3xl font-semibold text-slate-100">{value}</div>
    </div>
  );
}
