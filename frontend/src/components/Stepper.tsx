const STEPS = ["Scan", "Analyze", "Review & approve", "Verify"] as const;

export type Phase = "idle" | "scanning" | "analyzing" | "review" | "verifying" | "report";

const ACTIVE: Record<Phase, number> = { idle: -1, scanning: 0, analyzing: 1, review: 2, verifying: 3, report: 4 };

export default function Stepper({ phase }: { phase: Phase }) {
  const cur = ACTIVE[phase];
  return (
    <ol className="flex flex-wrap items-center gap-2 text-sm" aria-label="Progress">
      {STEPS.map((label, i) => {
        const done = i < cur;
        const active = i === cur;
        return (
          <li key={label} className="flex items-center gap-2" aria-current={active ? "step" : undefined}>
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${
                done ? "bg-brand text-brand-ink" : active ? "bg-brand/15 text-brand-text ring-1 ring-brand" : "bg-surface-2 text-ink-3"
              }`}
            >
              {done ? "✓" : i + 1}
            </span>
            <span className={active ? "text-ink" : done ? "text-ink-2" : "text-ink-3"}>{label}</span>
            {i < STEPS.length - 1 && <span className="mx-1 text-line-strong">—</span>}
          </li>
        );
      })}
    </ol>
  );
}
