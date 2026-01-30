"""
Phase 19 Legacy Compatibility Layer

Re-exports the original memory.py functions for backwards compatibility.
These functions are used by backend/app/service.py and other modules.

This module imports from the original memory.py file (now at parent level)
to maintain backwards compatibility without duplicating code.
"""

from __future__ import annotations

import json
from typing import Optional

import redis

from backend.app.config import settings
from backend.app.schemas import CognitiveStyle, Hypothesis, SessionSummary


_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def _session_key(session_id: str, suffix: str) -> str:
    """Build session key for Redis."""
    return f"session:{session_id}:{suffix}"


def load_cognitive_style(session_id: str) -> Optional[CognitiveStyle]:
    """Load cognitive style from session storage."""
    r = get_redis()
    raw = r.get(_session_key(session_id, "style"))
    if not raw:
        return None
    data = json.loads(raw)
    return CognitiveStyle(**data)


def save_cognitive_style(session_id: str, style: CognitiveStyle) -> None:
    """Save cognitive style to session storage."""
    r = get_redis()
    key = _session_key(session_id, "style")
    r.set(key, style.model_dump_json(), ex=settings.session_ttl_seconds)


def load_hypotheses(session_id: str) -> list[Hypothesis]:
    """Load hypotheses from session storage."""
    r = get_redis()
    raw = r.get(_session_key(session_id, "hypotheses"))
    if not raw:
        return []
    items = json.loads(raw)
    return [Hypothesis(**item) for item in items]


def save_hypotheses(session_id: str, hypotheses: list[Hypothesis]) -> None:
    """Save hypotheses to session storage."""
    r = get_redis()
    key = _session_key(session_id, "hypotheses")
    payload = [h.model_dump() for h in hypotheses]
    r.set(key, json.dumps(payload), ex=settings.session_ttl_seconds)


def load_session_summary(session_id: str) -> SessionSummary:
    """Load session summary from storage."""
    r = get_redis()
    raw = r.get(_session_key(session_id, "summary"))
    if not raw:
        return SessionSummary()
    data = json.loads(raw)
    return SessionSummary(**data)


def save_session_summary(session_id: str, summary: SessionSummary) -> None:
    """Save session summary to storage."""
    r = get_redis()
    key = _session_key(session_id, "summary")
    r.set(key, summary.model_dump_json(), ex=settings.session_ttl_seconds)
