from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "env" in body
    assert "version" in body


def test_metrics_exposed() -> None:
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "vcapp_requests_total" in r.text
