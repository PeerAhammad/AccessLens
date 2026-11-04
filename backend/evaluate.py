"""Run the full pipeline (scan -> AI analysis -> approve -> verify) over a list of URLs and
write benchmark/results.csv and benchmark/results.md.

Usage (from backend/, venv active, key in .env):   python evaluate.py [path-to-sites.txt]

Approval policy: only fixes NOT flagged for human review are applied, which is exactly what the
UI's "Approve all recommended" button does. Nothing is edited by hand; numbers come from the run.
"""
import os

os.environ.setdefault("ACCESSLENS_DEBUG", "1")   # print LLM timing lines (must be set before importing app.llm)

import asyncio
import csv
import datetime
import pathlib
import sys
import time

from app.llm import MODEL, PROVIDER, analyze
from app.scanner import scan
from app.verify import verify

ROOT = pathlib.Path(__file__).resolve().parents[1] / "benchmark"
FIELDS = ["url", "analysis_source", "findings", "proposed", "approved", "resolved", "approved_resolved", "remaining",
          "introduced", "failed_ops", "scan_s", "analyze_s", "verify_s", "error"]


async def run_site(url: str) -> dict:
    row = {"url": url, "error": ""}
    try:
        t = time.perf_counter()
        s = await scan(url)
        row["scan_s"] = round(time.perf_counter() - t, 1)
        row["findings"] = len(s.findings)

        t = time.perf_counter()
        res = await analyze(s)
        row["analyze_s"] = round(time.perf_counter() - t, 1)
        row["analysis_source"] = res.source
        row["proposed"] = sum(1 for a in res.analyses if a.patch)
        approved = [a for a in res.analyses if a.patch and not a.needs_human_review]
        row["approved"] = len(approved)

        t = time.perf_counter()
        r = await verify(s, [a.patch for a in approved])
        row["verify_s"] = round(time.perf_counter() - t, 1)
        resolved = set(r.resolved)
        row["resolved"] = len(r.resolved)
        row["approved_resolved"] = sum(1 for a in approved if a.finding_id in resolved)
        row["remaining"] = len(r.remaining)
        row["introduced"] = len(r.introduced)
        row["failed_ops"] = len(r.failed_ops)
    except Exception as e:
        row["error"] = repr(e)[:150]
    return row


def summarize(rows: list[dict]) -> dict:
    ok = [r for r in rows if not r["error"]]
    tot = lambda k: sum(r[k] for r in ok)
    findings, approved = tot("findings"), tot("approved")
    return {
        "sites_ok": len(ok), "sites_failed": len(rows) - len(ok),
        "findings": findings, "proposed": tot("proposed"), "approved": approved,
        "resolved": tot("resolved"), "introduced": tot("introduced"),
        "resolved_pct": round(100 * tot("resolved") / findings, 1) if findings else None,
        "approved_fix_success_pct": round(100 * tot("approved_resolved") / approved, 1) if approved else None,
        "avg_total_s": round(sum(r["scan_s"] + r["analyze_s"] + r["verify_s"] for r in ok) / len(ok), 1) if ok else None,
    }


def to_markdown(rows: list[dict], summ: dict, meta: str) -> str:
    head = "| Page | AI analysis | Issues found | Fixes proposed | Fixes applied | Resolved | Still failing | New issues | Time (s) |\n|---|---|---|---|---|---|---|---|---|\n"
    lines = []
    for r in rows:
        if r["error"]:
            lines.append(f"| {r['url']} | | scan failed: {r['error'][:60]} | | | | | | |")
        else:
            lines.append(f"| {r['url']} | {r.get('analysis_source', 'live')} | {r['findings']} | {r['proposed']} | {r['approved']} | {r['resolved']} | "
                         f"{r['remaining']} | {r['introduced']} | {round(r['scan_s'] + r['analyze_s'] + r['verify_s'], 1)} |")
    s = summ
    tail = (f"\n**Totals ({s['sites_ok']} pages scanned, {s['sites_failed']} failed):** {s['findings']} issues found; "
            f"{s['approved']} fixes applied (only those not flagged for human review); {s['resolved']} issues no longer fail axe-core "
            f"({s['resolved_pct']}% of all findings); {s['approved_fix_success_pct']}% of applied fixes resolved their issue; "
            f"{s['introduced']} new violations introduced; average {s['avg_total_s']} s per page.\n\n{meta}\n")
    return head + "\n".join(lines) + tail


async def main():
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "sites.txt"
    urls = [l.strip() for l in path.read_text().splitlines() if l.strip() and not l.startswith("#")]
    rows = []
    for u in urls:
        print("->", u, flush=True)
        row = await run_site(u)
        print("  ", row, flush=True)
        rows.append(row)
    ROOT.mkdir(exist_ok=True)
    with open(ROOT / "results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    meta = (f"_Run on {datetime.date.today()} with {PROVIDER}/{MODEL}. Single run per page; AI output varies between runs. Rows marked 'cache' reuse a saved AI analysis, so their time excludes the LLM (set ACCESSLENS_NO_CACHE=1 to force live runs). "
            f"Verification = axe-core re-run on an isolated copy; it does not assess the quality of AI-written text._")
    summ = summarize(rows)
    (ROOT / "results.md").write_text(to_markdown(rows, summ, meta), encoding="utf-8")
    print("\nWrote benchmark/results.csv and benchmark/results.md\n", summ)


if __name__ == "__main__":
    asyncio.run(main())
