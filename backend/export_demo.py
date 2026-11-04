"""Record a real run for the static (no-backend) demo.

Usage (from backend/, venv active):   python export_demo.py [url]
Uses the saved analysis cache if present (no LLM call) and runs verification live, then writes
frontend/public/demo/*.json plus screenshots. Build the static site afterwards with:
    cd ../frontend ; npm run build:demo
Policy: applies only fixes NOT flagged for human review (same as 'Approve all recommended').
"""
import asyncio
import datetime
import json
import pathlib
import shutil
import sys

from app import cache
from app.llm import MODEL, PROVIDER, analyze
from app.scanner import scan
from app.verify import verify

OUT = pathlib.Path(__file__).resolve().parents[1] / "frontend" / "public" / "demo"
DEFAULT = "https://www.w3.org/WAI/demos/bad/before/home.html"
PATH_KEYS = ("screenshot_path", "crop_path", "before_screenshot", "after_screenshot")


def localize(obj, out: pathlib.Path):
    """Copy referenced screenshot files into `out` and rewrite their paths to bare file names."""
    if isinstance(obj, dict):
        res = {}
        for k, v in obj.items():
            if k in PATH_KEYS and isinstance(v, str) and v:
                src = pathlib.Path(v)
                if src.exists():
                    shutil.copy(src, out / src.name)
                res[k] = src.name
            else:
                res[k] = localize(v, out)
        return res
    if isinstance(obj, list):
        return [localize(x, out) for x in obj]
    return obj


async def main(url: str):
    s = await scan(url)
    res = await analyze(s)
    if not cache.is_complete(res):
        sys.exit("Analysis is incomplete (the AI service failed for some findings). Retry later; not recording a degraded demo.")
    approved = [a.patch for a in res.analyses if a.patch and not a.needs_human_review]
    r = await verify(s, approved)

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*"):
        old.unlink()
    files = {
        "scan.json": localize(s.model_dump(exclude={"html_snapshot"}), OUT),
        "analysis.json": localize(res.model_dump(), OUT),
        "verify.json": localize(r.model_dump(), OUT),
        "meta.json": {"url": url, "recorded_at": datetime.date.today().isoformat(), "provider": PROVIDER, "model": MODEL,
                      "analysis_source": res.source, "fixes_applied": len(approved),
                      "before": r.before_count, "after": r.after_count, "introduced": len(r.introduced)},
    }
    for name, data in files.items():
        (OUT / name).write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(f"Recorded {url}: {r.before_count} -> {r.after_count} issues, {len(r.introduced)} introduced. Files in {OUT}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT))
