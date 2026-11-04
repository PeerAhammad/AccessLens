import asyncio
import json
import pytest
import app.cache as cache
import app.llm as m
from tests.test_llm import SCAN, fake_llm, reply


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    monkeypatch.delenv("ACCESSLENS_NO_CACHE", raising=False)


def patch_gemini(monkeypatch, calls):
    inner = fake_llm({"alt_text": reply("Cart"), "form_label": reply("Email"), "language": reply("en")})

    async def fake_gemini(system, user, images=None, model=None):
        calls.append(1)
        return await inner(system, user, images)
    monkeypatch.setattr(m, "PROVIDER", "gemini")
    monkeypatch.setattr(m, "gemini_call", fake_gemini)


def test_second_analysis_is_served_from_cache(monkeypatch):
    calls = []
    patch_gemini(monkeypatch, calls)
    first = asyncio.run(m.analyze(SCAN))
    n = len(calls)
    assert first.source == "live" and n >= 1
    second = asyncio.run(m.analyze(SCAN))
    assert second.source == "cache" and len(calls) == n and second.cached_at
    assert {a.finding_id: a.patch for a in first.analyses} == {a.finding_id: a.patch for a in second.analyses}


def test_incomplete_analysis_is_not_cached(monkeypatch):
    async def boom(system, user, images=None, model=None):
        raise RuntimeError("400 INVALID_ARGUMENT")
    monkeypatch.setattr(m, "PROVIDER", "gemini")
    monkeypatch.setattr(m, "gemini_call", boom)
    res = asyncio.run(m.analyze(SCAN))
    assert not cache.is_complete(res) and cache.load(SCAN) is None


def test_custom_llm_bypasses_cache():
    res = asyncio.run(m.analyze(SCAN, fake_llm({})))
    assert res.source == "live" and cache.load(SCAN) is None
