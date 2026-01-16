import pytest

from backend.mci_backend.app import expression, main, memory, observability, reasoning
from backend.mci_backend.app.models import AssistantReply, ExpressionPlan, Hypothesis, HypothesisSet, UserMessage


def clear_records():
    # Test-only helper: clear internal observability records.
    observability._RECORDS.clear()  # type: ignore[attr-defined]


# A. Request Boundary Violations

@pytest.mark.parametrize(
    "payload, expected_error_substr",
    [
        ({"text": "hello"}, "session_id is required"),
        ({"session_id": "" , "text": "hello"}, "session_id is required"),
        ({"session_id": "s1"}, "text is required"),
        ({"session_id": "s1", "text": ""}, "text is required"),
    ],
)
def test_request_boundary_violations(payload, expected_error_substr):
    clear_records()
    with pytest.raises(ValueError) as exc:
        main.handle_request(payload)
    assert expected_error_substr in str(exc.value)
    # For these failures, no request record is created because request_id is
    # generated only after boundary validation in the current MCI.
    assert observability.get_records() == []


# B. Reasoning Violations

def test_reasoning_empty_output_triggers_failure_and_record(monkeypatch):
    clear_records()

    def fake_model(prompt: str) -> str:
        return ""  # empty -> contract violation

    monkeypatch.setattr(reasoning, "call_reasoning_model", fake_model)

    with pytest.raises(RuntimeError):
        main.handle_request({"session_id": "s1", "text": "hello"})

    records = observability.get_records()
    assert len(records) == 1
    rec = records[0]
    assert rec.hard_failure_reason is not None
    # At least one reasoning-related invariant should have failed.
    assert any(
        r.invariant_id.startswith("reasoning.") and not r.passed
        for r in rec.invariants
    )


def test_reasoning_none_output_triggers_failure_and_record(monkeypatch):
    clear_records()

    def fake_model(prompt: str):  # type: ignore[no-untyped-def]
        return None  # will cause interpret_reasoning_output to see empty

    monkeypatch.setattr(reasoning, "call_reasoning_model", fake_model)

    with pytest.raises(RuntimeError):
        main.handle_request({"session_id": "s1", "text": "hello"})

    records = observability.get_records()
    assert len(records) == 1
    rec = records[0]
    assert rec.hard_failure_reason is not None
    assert any(
        r.invariant_id.startswith("reasoning.") and not r.passed
        for r in rec.invariants
    )


# C. Expression Violations

def test_expression_empty_plan_segments_fail(monkeypatch):
    clear_records()

    def fake_run_reasoning(user, current_h):  # type: ignore[no-untyped-def]
        # Build a ReasoningOutput with an empty ExpressionPlan
        from backend.mci_backend.app.models import ExpressionPlan, HypothesisSet, ReasoningOutput

        return ReasoningOutput(
            internal_trace="ok",
            proposed_hypotheses=current_h,
            plan=ExpressionPlan(segments=[]),
        )

    monkeypatch.setattr(reasoning, "run_reasoning", fake_run_reasoning)

    with pytest.raises(RuntimeError):
        main.handle_request({"session_id": "s1", "text": "hello"})

    records = observability.get_records()
    assert len(records) == 1
    rec = records[0]
    # Stage isolation invariant should fail or reasoning invariants should flag issue.
    assert any(not r.passed for r in rec.invariants)


def test_expression_returns_empty_text_fail(monkeypatch):
    clear_records()

    def fake_expression_model(plan: ExpressionPlan) -> str:  # type: ignore[no-untyped-def]
        return ""  # empty text

    monkeypatch.setattr(expression, "call_expression_model", fake_expression_model)

    with pytest.raises(RuntimeError):
        main.handle_request({"session_id": "s1", "text": "hello"})

    records = observability.get_records()
    assert len(records) == 1
    rec = records[0]
    assert any(
        r.invariant_id.startswith("expression.") and not r.passed
        for r in rec.invariants
    )


# D. Forbidden Silence

def test_forbidden_silence_no_error_means_failed_test(monkeypatch):
    clear_records()

    def fake_model(prompt: str) -> str:
        # Non-empty but we treat empty as violation; this should succeed and
        # therefore not be a violation.
        return "some reasoning"

    monkeypatch.setattr(reasoning, "call_reasoning_model", fake_model)

    # This call should not raise; if it did not record a failure, that is fine.
    # The test exists to document that any future silent contract violation
    # must be treated as a test failure when detected.
    result = main.handle_request({"session_id": "s1", "text": "hello"})
    assert "reply" in result
