from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class AbuseContext:
    path: str
    request_id: str
    ip_hash: str | None
    actor_key: str | None
    subject_type: str | None
    subject_id: str | None
    waf_limiter: str | None
    user_agent: str | None
    accept: str | None
    content_type: str | None
    method: str
    has_auth: bool
    is_sensitive_path: bool
    request_scheme: str
    is_non_local: bool


@dataclass
class AbuseDecision:
    allowed: bool
    action: str
    score: int
    reason: str
    retry_after_s: Optional[int]


_SUSPICIOUS_UA_MARKERS = {"curl", "python-requests", "wget"}
_WAF_LIMIT_STRINGS = {"limited", "blocked", "rate", "waf"}


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def _build_reason(triggers: list[str]) -> str:
    if not triggers:
        return "OK"
    joined = "+".join(triggers[:2])
    return joined[:120]


def decide_abuse(ctx: AbuseContext) -> AbuseDecision:
    score = 0
    triggers: list[str] = []

    ua = _normalize(ctx.user_agent)
    accept = _normalize(ctx.accept)
    content_type = _normalize(ctx.content_type)
    method = _normalize(ctx.method)
    scheme = _normalize(ctx.request_scheme)
    path = ctx.path or ""

    if not ua:
        score += 30
        triggers.append("missing_ua")
    else:
        for marker in _SUSPICIOUS_UA_MARKERS:
            if marker in ua:
                score += 10
                triggers.append("ua_marker")
                break

    if not accept:
        score += 15
        triggers.append("missing_accept")

    if path == "/api/chat" and method == "post" and not content_type:
        score += 15
        triggers.append("missing_ct")

    if path and method not in {"post", "get", "options"}:
        score += 10
        triggers.append("odd_method")

    if ctx.is_sensitive_path and not ctx.has_auth:
        score += 15
        triggers.append("anon_sensitive")

    if ctx.waf_limiter:
        lowered = _normalize(ctx.waf_limiter)
        if any(marker in lowered for marker in _WAF_LIMIT_STRINGS):
            score += 10
            triggers.append("waf_signal")

    if scheme != "https" and ctx.is_non_local:
        score += 10
        triggers.append("non_https")

    score = max(0, min(score, 100))

    action = "ALLOW"
    retry_after = None
    if score >= 90:
        action = "BLOCK"
        retry_after = 600
    elif 70 <= score < 90:
        action = "RATE_LIMIT"
        retry_after = 60

    allowed = action == "ALLOW"
    reason = _build_reason(triggers[:2])

    return AbuseDecision(
        allowed=allowed,
        action=action,
        score=score,
        reason=reason,
        retry_after_s=retry_after,
    )


__all__ = ["AbuseContext", "AbuseDecision", "decide_abuse"]
