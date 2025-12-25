from fastapi.testclient import TestClient

from model_service.config import Settings
from model_service.service.http import create_app


def _client() -> TestClient:
    settings = Settings(default_timeout_s=2.0, adapter="stub")
    app = create_app(settings)
    return TestClient(app)


def test_health_and_readiness_endpoints():
    client = _client()

    res_health = client.get("/healthz")
    assert res_health.status_code == 200
    assert res_health.json() == {"ok": True}

    res_ready = client.get("/readyz")
    assert res_ready.status_code == 200
    assert res_ready.json() == {"ok": True}


def test_predict_endpoint_with_stub_adapter():
    client = _client()
    payload = {"text": "hello"}

    res = client.post("/v1/predict", json=payload)
    assert res.status_code == 200
    body = res.json()

    assert body["ok"] is True
    assert body["output_text"] == "olleh"
    assert body["model_version"] == "stub-1"
    assert body["score"] == 0.05
    assert isinstance(body.get("latency_ms"), float)
