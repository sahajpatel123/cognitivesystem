from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.chat_contract import MAX_PAYLOAD_BYTES
import mci_backend.model_contract as mc


client = TestClient(app)


def _stub_output_plan(action: str = "ANSWER"):
    return SimpleNamespace(action=SimpleNamespace(value=action))


def _stub_result(text: str = "hello") -> mc.ModelInvocationResult:
    return mc.ModelInvocationResult(
        request_id="req",
        ok=True,
        output_text=text,
        output_json=None,
        failure=None,
    )


def test_request_rejects_extra_fields(monkeypatch):
    monkeypatch.setattr("app.main.assemble_decision_state", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.main.assemble_control_plan", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.main.assemble_output_plan", lambda *args, **kwargs: _stub_output_plan())
    monkeypatch.setattr("app.main.render_governed_response", lambda *args, **kwargs: _stub_result())

    payload = {"user_text": "hi", "extra": "nope"}
    res = client.post("/api/chat", json=payload)
    assert res.status_code == 400
    body = res.json()
    assert body["failure_type"] == "REQUEST_SCHEMA_INVALID"
    assert body["action"] == "REFUSE"
    assert "decision_state" not in json.dumps(body)


def test_request_rejects_empty(monkeypatch):
    res = client.post("/api/chat", json={"user_text": "   "})
    assert res.status_code == 400
    body = res.json()
    assert body["failure_type"] == "EMPTY_INPUT"
    assert body["action"] == "REFUSE"


def test_request_rejects_over_max_length(monkeypatch):
    over = "x" * 2001
    res = client.post("/api/chat", json={"user_text": over})
    assert res.status_code == 400
    body = res.json()
    assert body["failure_type"] == "REQUEST_SCHEMA_INVALID"
    assert body["action"] == "REFUSE"


def test_content_length_guard(monkeypatch):
    headers = {"content-length": str(MAX_PAYLOAD_BYTES + 1)}
    res = client.post("/api/chat", data="{}", headers=headers)
    assert res.status_code == 413
    body = res.json()
    assert body["failure_type"] == "REQUEST_TOO_LARGE"
    assert body["action"] == "REFUSE"


def test_valid_request_returns_bounded_response(monkeypatch):
    monkeypatch.setattr("app.main.assemble_decision_state", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.main.assemble_control_plan", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.main.assemble_output_plan", lambda *args, **kwargs: _stub_output_plan("ANSWER"))
    monkeypatch.setattr("app.main.render_governed_response", lambda *args, **kwargs: _stub_result("rendered"))

    res = client.post("/api/chat", json={"user_text": "hello"})
    assert res.status_code == 200
    body = res.json()
    assert body["action"] == "ANSWER"
    assert body["rendered_text"] == "rendered"
    assert body["failure_type"] is None
    assert body["failure_reason"] is None
    assert set(body.keys()) == {"action", "rendered_text", "failure_type", "failure_reason"}


def test_pipeline_error_sanitized(monkeypatch):
    monkeypatch.setattr("app.main.assemble_decision_state", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.main.assemble_control_plan", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.main.assemble_output_plan", lambda *args, **kwargs: _stub_output_plan("ANSWER"))

    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.main.render_governed_response", _raise)

    res = client.post("/api/chat", json={"user_text": "hello"})
    assert res.status_code == 500
    body = res.json()
    assert body["failure_type"] == "INTERNAL_ERROR_SANITIZED"
    assert body["action"] == "FALLBACK"
    dumped = json.dumps(body)
    assert "trace" not in dumped
    assert "error" not in dumped
