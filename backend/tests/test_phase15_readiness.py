import json
import os
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    data: Dict[str, Any] = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert isinstance(data.get("uptime_seconds"), int)


def test_ready_prod_missing_env_fails(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setenv("ENV", "production")
        m.delenv("BACKEND_PUBLIC_BASE_URL", raising=False)
        m.delenv("CORS_ORIGINS", raising=False)
        m.delenv("MODEL_PROVIDER_API_KEY", raising=False)
        resp = client.get("/ready")
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "not_ready"
    assert "missing_env" in data
    assert "BACKEND_PUBLIC_BASE_URL" in data["missing_env"]


def test_chat_internal_errors_are_sanitized(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # Force orchestrator call to raise to verify sanitized response
    with monkeypatch.context() as m:
        m.setattr("backend.app.main.render_governed_response", lambda *_args, **_kwargs: (_ for _ in ()).throw(Exception("boom")))  # type: ignore
        payload = {"user_text": "hi"}
        resp = client.post(
            "/api/chat",
            data=json.dumps(payload),
            headers={"content-type": "application/json", "content-length": str(len(json.dumps(payload)))},
        )
    assert resp.status_code == 500
    data = resp.json()
    assert data["failure_reason"] == "sanitized failure"
    # Ensure internal exception text does not leak
    assert "boom" not in json.dumps(data)
