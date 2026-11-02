import asyncio
import pytest
from app.llm import call_with_fallback


def run(coro):
    return asyncio.run(coro)


def test_retries_then_succeeds():
    calls = []
    async def call(m):
        calls.append(m)
        if len(calls) == 1:
            raise RuntimeError("503 UNAVAILABLE high demand")
        return "ok"
    assert run(call_with_fallback(call, ["a", "b"], delay=0)) == "ok"
    assert calls == ["a", "a"]


def test_falls_back_to_next_model_after_repeated_overload():
    async def call(m):
        if m == "a":
            raise RuntimeError("503 UNAVAILABLE")
        return "from-" + m
    assert run(call_with_fallback(call, ["a", "b"], delay=0)) == "from-b"


def test_404_skips_model_immediately():
    seen = []
    async def call(m):
        seen.append(m)
        if m == "a":
            raise RuntimeError("404 NOT_FOUND")
        return "ok"
    assert run(call_with_fallback(call, ["a", "b"], delay=0)) == "ok"
    assert seen == ["a", "b"]


def test_bad_key_fails_fast():
    seen = []
    async def call(m):
        seen.append(m)
        raise RuntimeError("400 INVALID_ARGUMENT API_KEY_INVALID")
    with pytest.raises(RuntimeError):
        run(call_with_fallback(call, ["a", "b"], delay=0))
    assert seen == ["a"]


def test_504_is_retried():
    calls = []
    async def call(m):
        calls.append(m)
        if len(calls) < 3:
            raise RuntimeError("504 DEADLINE_EXCEEDED")
        return "ok"
    assert run(call_with_fallback(call, ["a"], delay=0)) == "ok"
