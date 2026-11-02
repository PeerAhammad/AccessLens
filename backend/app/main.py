import asyncio
import logging
import os
import pathlib
import time
from collections import Counter, OrderedDict, defaultdict, deque

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .llm import analyze
from .patches import PatchOp
from .scanner import OUT, scan
from .schemas import AnalyzeResult, ScanRequest, ScanResult, VerifyResult
from .verify import verify

log = logging.getLogger("uvicorn.error")
app = FastAPI(title="AccessLens")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/scans", StaticFiles(directory=str(OUT)), name="scans")

MAX_SCANS = 50                                    # keep memory bounded
SCANS: "OrderedDict[str, ScanResult]" = OrderedDict()
RATE_PER_HOUR = int(os.environ.get("ACCESSLENS_RATE_PER_HOUR", "30"))
_hits: dict[str, deque] = defaultdict(deque)
_browser_slots = asyncio.Semaphore(int(os.environ.get("ACCESSLENS_MAX_BROWSERS", "2")))


def rate_limit(request: Request) -> None:
    """Simple in-memory per-IP limit (protects LLM spend and server memory)."""
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "?")
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= RATE_PER_HOUR:
        raise HTTPException(429, "Rate limit reached for this demo. Please try again later.")
    q.append(now)


class VerifyRequest(BaseModel):
    scan_id: str
    patches: list[PatchOp]


class AnalyzeRequest(BaseModel):
    scan_id: str


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/scan", response_model=ScanResult, dependencies=[Depends(rate_limit)])
async def do_scan(req: ScanRequest):
    try:
        async with _browser_slots:
            result = await scan(req.url)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"Could not scan page: {type(e).__name__}")
    SCANS[result.scan_id] = result
    while len(SCANS) > MAX_SCANS:
        SCANS.popitem(last=False)
    return result


@app.get("/scan/{scan_id}", response_model=ScanResult)
async def get_scan(scan_id: str):
    if scan_id not in SCANS:
        raise HTTPException(404, "Unknown scan")
    return SCANS[scan_id]


@app.post("/analyze", response_model=AnalyzeResult, dependencies=[Depends(rate_limit)])
async def do_analyze(req: AnalyzeRequest):
    scan_obj = SCANS.get(req.scan_id)
    if not scan_obj:
        raise HTTPException(404, "Unknown scan (the server may have restarted). Please scan again.")
    res = await analyze(scan_obj)
    log.warning("analyze outcome: %s", dict(Counter((a.note[:100] or "ok") for a in res.analyses)))
    return res


@app.post("/verify", response_model=VerifyResult)
async def do_verify(req: VerifyRequest):
    scan_obj = SCANS.get(req.scan_id)
    if not scan_obj:
        raise HTTPException(404, "Unknown scan (the server may have restarted). Please scan again.")
    valid = {f.al_id for f in scan_obj.findings}
    bad = [p.al_id for p in req.patches if p.al_id not in valid]
    if bad:
        raise HTTPException(400, f"Patch targets unknown elements: {bad}")
    try:
        async with _browser_slots:
            return await verify(scan_obj, req.patches)
    except Exception as e:
        raise HTTPException(502, f"Verification failed: {type(e).__name__}")


# Built React app (present in the Docker image). Mounted last so API routes win.
STATIC = pathlib.Path(os.environ.get("ACCESSLENS_STATIC", "static"))
if STATIC.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="web")
