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
                done ? "bg-cyan-400 text-slate-900" : active ? "bg-cyan-500/20 text-cyan-300 ring-1 ring-cyan-400" : "bg-slate-800 text-slate-500"
              }`}
            >
              {done ? "✓" : i + 1}
            </span>
            <span className={active ? "text-slate-100" : done ? "text-slate-300" : "text-slate-500"}>{label}</span>
            {i < STEPS.length - 1 && <span className="mx-1 text-slate-700">—</span>}
          </li>
        );
      })}
    </ol>
  );
}
