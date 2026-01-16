from __future__ import annotations

"""Session-local hypothesis storage for MCI.

Enforces:
- Session-only scoping.
- TTL-bound semantics.
- Non-deleting hypotheses.
- Clamped per-turn updates.
"""

import time
from typing import Dict

from .models import HypothesisSet, Hypothesis


# In-memory store keyed strictly by session_id.
# Cognitive Contract: no cross-session keys, no identity.
_STORE: Dict[str, HypothesisSet] = {}


def _now() -> float:
    return time.time()


def _is_expired(hset: HypothesisSet, now: float) -> bool:
    # TTL-bound memory: discard after ttl_seconds.
    return (now - hset_created_at(hset)) > hset.ttl_seconds


def hset_created_at(hset: HypothesisSet) -> float:
    """Return the creation timestamp for a hypothesis set.

    MCI simplification: use a synthetic timestamp stored via a private attribute
    on the object itself. This avoids extra structures while keeping TTL logic.
    """
    # We store created_at on the instance dynamically; if missing, treat as now.
    return getattr(hset, "_created_at", _now())


def _with_created_at(hset: HypothesisSet, ts: float | None = None) -> HypothesisSet:
    if ts is None:
        ts = _now()
    setattr(hset, "_created_at", ts)
    return hset


def load_hypotheses(session_id: str) -> HypothesisSet:
    """Load session-local hypotheses for a session.

    Contract mapping:
    - Session-only: keyed strictly by session_id.
    - TTL-bound: expired sets are discarded.
    - No identity: no lookup by anything but session_id.
    """
    now = _now()
    existing = _STORE.get(session_id)
    if existing is None or _is_expired(existing, now):
        # Start a fresh, empty set when missing or expired.
        fresh = HypothesisSet(session_id=session_id)
        return _with_created_at(fresh, now)
    return existing


def save_hypotheses(hset: HypothesisSet) -> None:
    """Save hypotheses for a session.

    Contract mapping:
    - Non-deleting: this function never removes hypotheses.
    - Session-only: data is stored only under this session_id.
    """
    if not hasattr(hset, "_created_at"):
        _with_created_at(hset)
    _STORE[hset.session_id] = hset


def apply_clamped_update(
    current: HypothesisSet,
    proposed: HypothesisSet,
    max_delta: float = 0.2,
) -> HypothesisSet:
    """Apply non-deleting, clamped updates to hypotheses.

    Contract mapping:
    - Non-deleting: existing hypotheses remain; none are removed.
    - Clamped: per-turn updates are limited in magnitude.
    """
    now = _now()
    by_key: Dict[str, Hypothesis] = {h.key: h for h in current.hypotheses}

    for new_h in proposed.hypotheses:
        existing = by_key.get(new_h.key)
        if existing is not None:
            delta = new_h.value - existing.value
            if delta > max_delta:
                delta = max_delta
            elif delta < -max_delta:
                delta = -max_delta
            existing.value = existing.value + delta
        else:
            by_key[new_h.key] = Hypothesis(key=new_h.key, value=new_h.value)

    updated = HypothesisSet(
        session_id=current.session_id,
        hypotheses=list(by_key.values()),
        ttl_seconds=current.ttl_seconds,
    )
    return _with_created_at(updated, hset_created_at(current))
