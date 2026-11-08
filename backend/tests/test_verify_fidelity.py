"""Regression: the isolated copy must render like the live page (e.g. crossorigin stylesheets must load).
Skipped automatically when Chromium is not installed."""
import asyncio
import functools
import http.server
import json
import os
import threading

import pytest

pytest.importorskip("playwright.async_api")

HTML = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>T</title>'
        '<link rel="stylesheet" crossorigin href="/style.css"></head><body><h1>Dashboard</h1>'
        '<p><span class="stage">01 / STAGE</span></p></body></html>')
CSS = "body{background:#0f172a;color:#e2e8f0}.stage{color:#475569;font-size:12px}"   # low contrast on dark


@pytest.fixture
def site(tmp_path):
    (tmp_path / "index.html").write_text(HTML)
    (tmp_path / "style.css").write_text(CSS)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)   # sends no CORS headers
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    srv.shutdown()


def test_isolated_copy_renders_with_crossorigin_css(site, monkeypatch):
    import app.scanner as sc
    import app.verify as vf
    from app.fixes import contrast_patch
    monkeypatch.setattr(sc, "validate_url", lambda u: u)   # allow localhost for this test only
    monkeypatch.setattr(vf, "validate_url", lambda u: u)
    cfg = os.environ.get("ACCESSLENS_TEST_CHROME_JSON")     # optional: custom browser binary (CI/sandbox)
    if cfg:
        import playwright.async_api as pa
        c = json.load(open(cfg)); orig = pa.BrowserType.launch
        async def launch(self, *a, **k):
            k["executable_path"] = c["path"]; k["args"] = list(c["args"]) + k.get("args", [])
            return await orig(self, *a, **k)
        monkeypatch.setattr(pa.BrowserType, "launch", launch)

    async def run():
        s = await sc.scan(site)
        patches = [p for p in (contrast_patch(f) for f in s.findings if f.category == "contrast") if p]
        return s, patches, await vf.verify(s, patches)
    try:
        s, patches, r = asyncio.run(run())
    except Exception as e:
        if "Executable doesn't exist" in str(e) or "playwright install" in str(e):
            pytest.skip("Chromium not installed")
        raise
    assert any(f.category == "contrast" for f in s.findings)
    assert r.before_count == len(s.findings)                # snapshot reproduces the live scan
    assert r.live_only == [] and r.snapshot_only == []
    assert r.introduced == [] and r.resolved == [f.id for f in s.findings if f.category == "contrast"]
