import type { Finding, FindingAnalysis } from "../types";
import { CATEGORY_LABEL, SEV_ORDER, SEV_STYLE, stripAl } from "../ui";

export default function FindingList({
  findings,
  analyses,
  selectedId,
  approved,
  onSelect,
}: {
  findings: Finding[];
  analyses: Map<string, FindingAnalysis>;
  selectedId: string | null;
  approved: Set<string>;
  onSelect: (id: string) => void;
}) {
  const sorted = [...findings].sort((a, b) => SEV_ORDER.indexOf(a.severity) - SEV_ORDER.indexOf(b.severity));
  return (
    <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
      {sorted.map((f) => {
        const a = analyses.get(f.id);
        const isApproved = approved.has(f.id);
        const status = isApproved
          ? { t: "Approved", c: "bg-brand text-brand-ink" }
          : a?.patch && !a.needs_human_review
          ? { t: "Fix ready", c: "bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300" }
          : a?.patch
          ? { t: "Review fix", c: "bg-amber-100 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300" }
          : { t: "No auto-fix", c: "bg-surface-2 text-ink-2" };
        return (
          <li key={f.id}>
            <button
              onClick={() => onSelect(f.id)}
              aria-current={f.id === selectedId}
              className={`flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-surface-2 ${
                f.id === selectedId ? "bg-surface-2" : ""
              }`}
            >
              <span className={`mt-0.5 rounded-md px-2 py-0.5 text-xs ring-1 ${SEV_STYLE[f.severity].badge}`}>{f.severity}</span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium text-ink">{CATEGORY_LABEL[f.category] ?? f.category}</span>
                <span className="block truncate font-mono text-xs text-ink-3">{stripAl(f.html)}</span>
              </span>
              <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs ${status.c}`}>{status.t}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
