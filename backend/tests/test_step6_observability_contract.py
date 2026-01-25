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


def test_helpers_present():
    assert hasattr(m, "_should_sample") and callable(m._should_sample)
    assert hasattr(m, "_emit_chat_summary") and callable(m._emit_chat_summary)
    assert hasattr(m, "_log_chat_summary") and callable(m._log_chat_summary)


def test_sampling_deterministic():
    rid = "req-deterministic-123"
    first = m._should_sample(rid, 0.02)
    second = m._should_sample(rid, 0.02)
    assert first == second


def test_chat_summary_safe_and_capped(monkeypatch):
    captured: list[dict] = []

    def fake_structured_log(evt):
        captured.append(evt)

    monkeypatch.setattr(m, "structured_log", fake_structured_log)
    monkeypatch.setattr(m, "record_invocation", lambda event: False)

    req = _stub_request()
    long_reason = "x" * 500

    m._log_chat_summary(
        request=req,
        request_id="req-safe-1",
        status_code=500,
        latency_ms=123.4,
        plan_value="free",
        subject_type="anon",
        subject_id="anon-1",
        input_tokens=None,
        output_tokens_est=None,
        error_code="timeout",
        waf_limiter="db",
        budget_ms_total=1000,
        budget_ms_remaining_at_model_start=None,
        timeout_where="total",
        model_timeout_ms=None,
        http_timeout_ms=15000,
        action="fallback",
        failure_type="timeout",
        failure_reason=long_reason,
        requested_mode=None,
        granted_mode="default",
        model_class="balanced",
        breaker_open=False,
        budget_block=False,
        ip_hash="iphash",
        budget_scope="total_timeout",
    )

    assert captured, "structured_log should be called"
    summary = captured[-1]
    assert summary.get("event") == "chat.summary"
    assert "user_text" not in summary
    assert "rendered_text" not in summary
    assert summary.get("failure_type") == "timeout"
    fr = summary.get("failure_reason")
    assert fr is None or len(fr) <= 200
    assert summary.get("sampled") is True
    assert summary.get("subject_id_hash")
    assert summary.get("request_id") == "req-safe-1"
