from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict

try:
    from backend.app.observability.logging import structured_log, safe_redact
except Exception:  # pragma: no cover - fallback when imports unavailable
    structured_log = None  # type: ignore[assignment]
    safe_redact = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def _safe_structured(payload: Dict[str, Any]) -> None:
    try:
        if structured_log:
            structured_log(payload)  # type: ignore[misc]
            return
    except Exception:
        # fall through to plain logger
        pass
    try:
        cleaned = safe_redact(payload) if callable(safe_redact) else payload
        logger.info(json.dumps(cleaned, separators=(",", ":")))
    except Exception:
        return


def counter(name: str, value: int = 1, labels: dict[str, str] | None = None) -> None:
    payload = {"type": "metric", "metric_type": "counter", "name": name, "value": int(value), "labels": labels or {}}
    _safe_structured(payload)


def histogram(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    payload = {"type": "metric", "metric_type": "histogram", "name": name, "value": float(value), "labels": labels or {}}
    _safe_structured(payload)


def gauge(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    payload = {"type": "metric", "metric_type": "gauge", "name": name, "value": float(value), "labels": labels or {}}
    _safe_structured(payload)


def event(name: str, fields: Dict[str, Any]) -> None:
    payload = {"type": "event", "name": name, "fields": safe_redact(fields) if callable(safe_redact) else fields}
    _safe_structured(payload)


def should_sample(request_id: str, rate: float) -> bool:
    clamped = max(0.0, min(1.0, float(rate)))
    if clamped <= 0:
        return False
    if clamped >= 1:
        return True
    h = hashlib.sha256(request_id.encode("utf-8")).digest()
    val = int.from_bytes(h, "big") / float(1 << 256)
    return val < clamped


def _cap_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    return reason[:200]


def build_chat_summary_fields(
    *,
    request_id: str,
    status_code: int,
    latency_ms: float,
    plan: str,
    requested_mode: str | None,
    granted_mode: str,
    model_class: str | None,
    action: str,
    failure_type: str | None,
    failure_reason: str | None,
    input_tokens_est: int | None,
    output_tokens_cap: int | None,
    breaker_open: bool | None,
    budget_block: bool | None,
    timeout_where: str | None,
    sampled: bool,
    subject_type: str | None,
    subject_id_hash: str | None,
    ip_hash: str | None,
) -> Dict[str, Any]:
    return {
        "request_id": request_id,
        "endpoint": "/api/chat",
        "status_code": int(status_code),
        "latency_ms": int(latency_ms),
        "plan": plan,
        "requested_mode": requested_mode or "none",
        "granted_mode": granted_mode,
        "model_class": model_class or "unknown",
        "action": action,
        "failure_type": failure_type,
        "failure_reason": _cap_reason(failure_reason),
        "input_tokens_est": input_tokens_est,
        "output_tokens_cap": output_tokens_cap,
        "breaker_open": bool(breaker_open) if breaker_open is not None else False,
        "budget_block": bool(budget_block) if budget_block is not None else False,
        "timeout_where": timeout_where,
        "sampled": sampled,
        "subject_type": subject_type or "unknown",
        "subject_id_hash": subject_id_hash,
        "ip_hash": ip_hash,
    }


__all__ = [
    "counter",
    "histogram",
    "gauge",
    "event",
    "should_sample",
    "build_chat_summary_fields",
]
