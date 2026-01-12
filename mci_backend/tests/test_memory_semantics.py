import time

import pytest

from mci_backend.app import memory
from mci_backend.app.models import HypothesisSet, Hypothesis


def test_cross_session_memory_is_isolated():
    # Different session_ids must not share hypotheses.
    s1 = memory.load_hypotheses("s1")
    s2 = memory.load_hypotheses("s2")

    assert s1.session_id == "s1"
    assert s2.session_id == "s2"
    assert s1.session_id != s2.session_id


def test_ttl_expiry_resets_hypotheses(monkeypatch):
    # Simulate TTL expiry by monkeypatching memory._now.
    base = time.time()

    def fake_now() -> float:
        return base

    monkeypatch.setattr(memory, "_now", fake_now)

    hset = memory.load_hypotheses("s1")
    assert hset.session_id == "s1"

    # Advance time beyond TTL.
    def fake_now_late() -> float:
        return base + hset.ttl_seconds + 1

    monkeypatch.setattr(memory, "_now", fake_now_late)

    hset_late = memory.load_hypotheses("s1")
    # After expiry, we expect a fresh set (no reuse of previous hypotheses).
    assert hset_late is not hset


def test_non_deleting_update():
    before = HypothesisSet(
        session_id="s1",
        hypotheses=[Hypothesis(key="a", value=0.1), Hypothesis(key="b", value=0.2)],
        ttl_seconds=900,
    )
    proposed = HypothesisSet(
        session_id="s1",
        hypotheses=[Hypothesis(key="a", value=0.5)],  # omit "b" in proposed
        ttl_seconds=900,
    )

    after = memory.apply_clamped_update(before, proposed)
    # Non-deleting: after must not have fewer hypotheses than before.
    assert len(after.hypotheses) >= len(before.hypotheses)


def test_clamping_limits_delta():
    before = HypothesisSet(
        session_id="s1",
        hypotheses=[Hypothesis(key="a", value=0.0)],
        ttl_seconds=900,
    )
    proposed = HypothesisSet(
        session_id="s1",
        hypotheses=[Hypothesis(key="a", value=10.0)],
        ttl_seconds=900,
    )

    after = memory.apply_clamped_update(before, proposed, max_delta=0.2)
    # Value should not jump by more than max_delta from original.
    assert 0.0 <= after.hypotheses[0].value <= 0.2
