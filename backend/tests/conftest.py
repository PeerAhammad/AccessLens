import pytest
import app.llm as llm


@pytest.fixture(autouse=True)
def _no_retry_pause(monkeypatch):
    monkeypatch.setattr(llm, "RETRY_PAUSE", 0)
