import { useMemo, useState } from "react";
import { analyze, scanUrl, verify } from "./api";
import type { FindingAnalysis, PatchOp, ScanResult, VerifyResult } from "./types";
import Stepper, { type Phase } from "./components/Stepper";
import ScanForm from "./components/ScanForm";
import Summary from "./components/Summary";
import ScreenshotOverlay from "./components/ScreenshotOverlay";
import FindingList from "./components/FindingList";
import DetailPanel from "./components/DetailPanel";
import Report from "./components/Report";

export default function App() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [scan, setScan] = useState<ScanResult | null>(null);
  const [analyses, setAnalyses] = useState<Map<string, FindingAnalysis>>(new Map());
  const [aiNote, setAiNote] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [approved, setApproved] = useState<Set<string>>(new Set());
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [applied, setApplied] = useState<PatchOp[]>([]);

  const busy = phase === "scanning" || phase === "analyzing" || phase === "verifying";
  const selectedFinding = scan?.findings.find((f) => f.id === selected) ?? null;

  const recommended = useMemo(
    () => [...analyses.values()].filter((a) => a.patch && !a.needs_human_review).map((a) => a.finding_id),
    [analyses]
  );

  const reset = () => {
    setPhase("idle"); setError(null); setScan(null); setAnalyses(new Map()); setAiNote(null);
    setSelected(null); setApproved(new Set()); setEdits({}); setResult(null); setApplied([]);
  };

  const handleScan = async (url: string) => {
    reset();
    try {
      setPhase("scanning");
      const s = await scanUrl(url);
      setScan(s);
      if (s.findings.length === 0) { setPhase("review"); return; }
      setPhase("analyzing");
      try {
        const a = await analyze(s.scan_id);
        setAnalyses(new Map(a.analyses.map((x) => [x.finding_id, x])));
      } catch (e) {
        setAiNote(`AI analysis was unavailable (${(e as Error).message}). Showing raw findings only.`);
      }
      setPhase("review");
    } catch (e) {
      setError((e as Error).message);
      setPhase("idle");
    }
  };

  const toggle = (id: string) =>
    setApproved((prev) => {
      const n = new Set(prev);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });

  const aiFailed = useMemo(
    () => [...analyses.values()].filter((a) => /^(LLM unavailable|Model omitted|No LLM result)/.test(a.note)).length,
    [analyses]
  );

  const retryAnalysis = async () => {
    if (!scan) return;
    try {
      setError(null);
      setPhase("analyzing");
      const a = await analyze(scan.scan_id);
      const next = new Map(a.analyses.map((x) => [x.finding_id, x]));
      setAnalyses(next);
      setApproved((prev) => new Set([...prev].filter((id) => next.get(id)?.patch)));
      setAiNote(null);
    } catch (e) {
      setError((e as Error).message);
    }
    setPhase("review");
  };

  const handleVerify = async () => {
    if (!scan) return;
    const patches: PatchOp[] = [...approved].flatMap((id) => {
      const p = analyses.get(id)?.patch;
      if (!p) return [];
      return [p.op === "set_attribute" && edits[id] !== undefined ? { ...p, value: edits[id] } : p];
    });
    try {
      setError(null);
      setPhase("verifying");
      const r = await verify(scan.scan_id, patches);
      setApplied(patches);
      setResult(r);
      setPhase("report");
    } catch (e) {
      setError((e as Error).message);
      setPhase("review");
    }
  };

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-800 bg-slate-950/60 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <button onClick={reset} className="flex items-center gap-2 text-left">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-400 font-bold text-slate-900">A</span>
            <span className="text-lg font-semibold text-slate-100">AccessLens</span>
          </button>
          {phase !== "idle" && <Stepper phase={phase} />}
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        {error && (
          <div role="alert" className="mb-6 rounded-lg border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">
            {error}
          </div>
        )}

        {phase === "idle" && (
          <section className="mx-auto flex max-w-3xl flex-col items-center py-16 text-center">
            <h1 className="text-4xl font-bold tracking-tight text-slate-100 sm:text-5xl">Make the web accessible. Automatically.</h1>
            <p className="mt-4 max-w-2xl text-lg text-slate-300">
              Scan a page, understand every accessibility barrier, review AI-generated fixes, and verify they actually work — before and after.
            </p>
            <div className="mt-10 w-full">
              <div className="flex justify-center">
                <ScanForm onScan={handleScan} busy={busy} />
              </div>
            </div>
            <ul className="mt-14 grid w-full gap-4 text-left sm:grid-cols-3">
              {[
                ["Detect", "Playwright + axe-core find real violations, with exact elements and WCAG criteria."],
                ["Explain & fix", "AI explains each issue in plain language and proposes a minimal, validated code change."],
                ["Verify", "Approved fixes are applied to an isolated copy and re-tested. Nothing live is ever modified."],
              ].map(([t, d]) => (
                <li key={t} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                  <div className="font-semibold text-cyan-300">{t}</div>
                  <p className="mt-1 text-sm text-slate-400">{d}</p>
                </li>
              ))}
            </ul>
          </section>
        )}

        {(phase === "scanning" || phase === "analyzing" || phase === "verifying") && (
          <div role="status" className="mx-auto max-w-md py-24 text-center">
            <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-slate-700 border-t-cyan-400" />
            <p className="mt-6 text-lg text-slate-100">
              {phase === "scanning" && "Loading the page and running accessibility checks…"}
              {phase === "analyzing" && "AI is explaining issues and drafting fixes…"}
              {phase === "verifying" && "Applying approved fixes to an isolated copy and re-testing…"}
            </p>
            <p className="mt-2 text-sm text-slate-400">
              {phase === "analyzing" ? "This can take up to a minute on large pages." : "This usually takes a few seconds."}
            </p>
          </div>
        )}

        {phase === "review" && scan && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-2xl font-semibold text-slate-100">Scan results</h2>
                <p className="text-sm text-slate-400">{scan.url}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={() => setApproved(new Set(recommended))}
                  disabled={recommended.length === 0}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-400 disabled:opacity-40"
                >
                  Approve all recommended ({recommended.length})
                </button>
                <button
                  onClick={handleVerify}
                  disabled={approved.size === 0}
                  className="rounded-lg bg-cyan-400 px-5 py-2 text-sm font-semibold text-slate-900 hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Apply &amp; verify ({approved.size})
                </button>
              </div>
            </div>

            {aiNote && <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">{aiNote}</p>}
            {aiFailed > 0 && (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
                <span>
                  The AI service did not return results for {aiFailed} issue{aiFailed === 1 ? "" : "s"} (usually temporary overload). Those show no proposed fix.
                </span>
                <button onClick={retryAnalysis} className="rounded-lg bg-amber-400 px-4 py-1.5 font-semibold text-slate-900 hover:bg-amber-300">
                  Retry AI analysis
                </button>
              </div>
            )}

            {scan.findings.length === 0 ? (
              <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-6 text-emerald-200">
                No violations were detected for the six checked categories. This does not guarantee the page is fully accessible — automated tools find only a
                portion of real-world barriers.
              </p>
            ) : (
              <>
                <Summary findings={scan.findings} analyses={analyses} />
                <div className="grid gap-6 lg:grid-cols-5">
                  <div className="space-y-6 lg:col-span-2">
                    <FindingList findings={scan.findings} analyses={analyses} selectedId={selected} approved={approved} onSelect={setSelected} />
                  </div>
                  <div className="space-y-6 lg:col-span-3">
                    <ScreenshotOverlay scan={scan} selectedId={selected} onSelect={setSelected} />
                    <DetailPanel
                      finding={selectedFinding}
                      analysis={selected ? analyses.get(selected) : undefined}
                      approved={selected ? approved.has(selected) : false}
                      onToggle={() => selected && toggle(selected)}
                      editValue={selected ? edits[selected] : undefined}
                      onEdit={(v) => selected && setEdits((p) => ({ ...p, [selected]: v }))}
                    />
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {phase === "report" && scan && result && (
          <Report scan={scan} result={result} applied={applied} analyses={analyses} onBack={() => setPhase("review")} onReset={reset} />
        )}
      </main>

      <footer className="mx-auto max-w-7xl px-6 pb-10 text-xs text-slate-500">
        AccessLens uses automated testing (axe-core) and AI assistance. It cannot guarantee WCAG compliance — always review fixes and test with assistive technology.
      </footer>
    </div>
  );
}
