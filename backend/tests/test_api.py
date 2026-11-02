from fastapi.testclient import TestClient
import app.main as m

client = TestClient(m.app)


def test_health():
    assert client.get("/health").json() == {"ok": True}


def test_private_targets_rejected_before_any_browser_starts():
    m._hits.clear()
    for url in ("http://127.0.0.1:8000", "http://169.254.169.254/latest/meta-data", "file:///etc/passwd"):
        r = client.post("/scan", json={"url": url})
        assert r.status_code == 400, url


def test_rate_limit(monkeypatch):
    m._hits.clear()
    monkeypatch.setattr(m, "RATE_PER_HOUR", 2)
    codes = [client.post("/scan", json={"url": "http://127.0.0.1"}).status_code for _ in range(3)]
    assert codes == [400, 400, 429]
    m._hits.clear()


def test_unknown_scan_ids():
    assert client.post("/analyze", json={"scan_id": "nope"}).status_code == 404
    assert client.post("/verify", json={"scan_id": "nope", "patches": []}).status_code == 404
