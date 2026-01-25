from __future__ import annotations

import sys
import types

# Stub jose package (jwt + exceptions) to avoid external dependency during offline tests
jose_stub = types.ModuleType("jose")
jwt_stub = types.SimpleNamespace(encode=lambda *a, **k: "", decode=lambda *a, **k: {})
exceptions_stub = types.ModuleType("exceptions")
jose_stub.jwt = jwt_stub
jose_stub.exceptions = exceptions_stub
sys.modules.setdefault("jose", jose_stub)
sys.modules.setdefault("jose.jwt", jwt_stub)
sys.modules.setdefault("jose.exceptions", exceptions_stub)
setattr(exceptions_stub, "JWTError", type("JWTError", (Exception,), {}))

import backend.app.main as m


def _stub_request():
    state = types.SimpleNamespace(
        waf_meta={},
        plan_meta={},
        identity=types.SimpleNamespace(anon_id="anon-1"),
    )
    return types.SimpleNamespace(state=state, method="POST")


def _capture(monkeypatch):
    captured: list[dict] = []

    def fake_structured_log(evt):
        captured.append(evt)

    monkeypatch.setattr(m, "structured_log", fake_structured_log)
    monkeypatch.setattr(m, "record_invocation", lambda event: False)
    return captured


def test_success_summary_uses_sampling(monkeypatch):
    captured = _capture(monkeypatch)
    monkeypatch.setattr(m, "_should_sample", lambda rid, rate: True)

    req = _stub_request()
    m._log_chat_summary(
        request=req,
        request_id="req-success-1",
        status_code=200,
        latency_ms=42,
        plan_value="free",
        subject_type="anon",
        subject_id="anon-1",
        input_tokens=10,
        output_tokens_est=20,
        error_code=None,
        waf_limiter="db",
        budget_ms_total=1000,
        budget_ms_remaining_at_model_start=800,
        timeout_where=None,
        model_timeout_ms=15000,
        http_timeout_ms=15000,
        action="answer",
        failure_type=None,
        failure_reason=None,
        requested_mode="thinking",
        granted_mode="default",
        model_class="balanced",
        breaker_open=False,
        budget_block=False,
        ip_hash="iphash",
        budget_scope=None,
    )

    assert captured, "chat.summary should emit when sampling is forced true"
    summary = captured[-1]
    assert summary.get("event") == "chat.summary"
    assert summary.get("status_code") == 200
    assert summary.get("sampled") is True
    assert "user_text" not in summary and "rendered_text" not in summary
    assert summary.get("failure_type") is None
    assert summary.get("failure_reason") is None or len(summary.get("failure_reason")) <= 200


def test_error_always_emits_and_caps(monkeypatch):
    captured = _capture(monkeypatch)
    monkeypatch.setattr(m, "_should_sample", lambda rid, rate: False)

    req = _stub_request()
    long_reason = "y" * 500
    m._log_chat_summary(
        request=req,
        request_id="req-error-1",
        status_code=503,
        latency_ms=99,
        plan_value="pro",
        subject_type="user",
        subject_id="user-1",
        input_tokens=5,
        output_tokens_est=8,
        error_code="provider_unavailable",
        waf_limiter="db",
        budget_ms_total=2000,
        budget_ms_remaining_at_model_start=1500,
        timeout_where="provider",
        model_timeout_ms=12000,
        http_timeout_ms=12000,
        action="fallback",
        failure_type="provider_unavailable",
        failure_reason=long_reason,
        requested_mode="default",
        granted_mode="default",
        model_class="balanced",
        breaker_open=True,
        budget_block=True,
        ip_hash="iphash2",
        budget_scope="breaker",
    )

    assert captured, "chat.summary must emit on error regardless of sampling"
    summary = captured[-1]
    assert summary.get("status_code") == 503
    assert summary.get("failure_type") == "provider_unavailable"
    fr = summary.get("failure_reason")
    assert fr is None or len(fr) <= 200
    assert summary.get("sampled") is True
    assert "user_text" not in summary and "rendered_text" not in summary
