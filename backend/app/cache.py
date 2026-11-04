"""On-disk cache of COMPLETE AI analyses, keyed by page URL + the exact set of findings.
Lets a known page (e.g. the demo) load instantly with no LLM call, and survives API outages.
Only fully successful analyses are saved. The UI labels cached results as saved analyses."""
import datetime
import hashlib
import os
import pathlib
import re
from typing import Optional

from .schemas import AnalyzeResult, ScanResult

CACHE_DIR = pathlib.Path(os.environ.get("ACCESSLENS_CACHE_DIR", "analysis_cache"))
_INCOMPLETE = re.compile(r"^(LLM unavailable|Model omitted|No LLM result|Skipped)")


def key(scan: ScanResult) -> str:
    parts = sorted(f"{f.id}:{hashlib.sha1(f.html.encode()).hexdigest()[:10]}" for f in scan.findings)
    return hashlib.sha256((scan.url + "|" + "|".join(parts)).encode()).hexdigest()[:24]


def is_complete(res: AnalyzeResult) -> bool:
    return bool(res.analyses) and not any(_INCOMPLETE.match(a.note) for a in res.analyses)


def load(scan: ScanResult) -> Optional[AnalyzeResult]:
    p = CACHE_DIR / f"{key(scan)}.json"
    if not p.exists():
        return None
    try:
        res = AnalyzeResult.model_validate_json(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    res.scan_id = scan.scan_id
    res.source = "cache"
    return res


def save(scan: ScanResult, res: AnalyzeResult) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data = res.model_copy(update={"source": "live", "cached_at": datetime.date.today().isoformat()})
        (CACHE_DIR / f"{key(scan)}.json").write_text(data.model_dump_json(indent=1), encoding="utf-8")
    except Exception:
        pass   # caching is best-effort
