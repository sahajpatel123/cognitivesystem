"""Regression test to ensure meta scaffolding never appears in user-facing responses."""

import asyncio
from backend.app.chat_contract import ChatAction
from backend.app.reliability.engine import Step5Context, run_step5


def test_no_meta_scaffolding_in_answer():
    """
    Regression test for bug where meta scaffolding appeared instead of real answers.
    
    The UI should NEVER show text like:
    - "Answer: Providing a concise response based on limited details."
    - "Confidence: Cautious."
    - "Unknown: Some factors are not yet known."
    - "Assumption: Proceeding with limited context only."
    
    This test ensures the backend returns real answers, not meta scaffolding.
    """
    ctx = Step5Context(
        request_id="regression_test",
        plan_value="free",
        breaker_open=False,
        budget_blocked=False,
        total_timeout_ms=5000,
        per_attempt_timeout_ms=2000,
        max_attempts=2,
        mode_requested=None,
        mode_effective="default",
        model_class_effective="balanced",
    )

    async def invoke_attempt(_: int) -> str:
        # Simulate a normal LLM response
        return "Bitcoin is a decentralized digital currency that operates without a central bank."

    result = asyncio.run(run_step5(ctx, invoke_attempt))
    
    # Should return ANSWER action
    assert result.action == ChatAction.ANSWER
    assert result.failure_type is None
    
    # Should contain the actual answer
    assert "Bitcoin" in result.rendered_text
    assert "decentralized digital currency" in result.rendered_text
    
    # Should NOT contain meta scaffolding
    forbidden_phrases = [
        "Providing a concise response based on limited details",
        "Confidence: Cautious",
        "Confidence: Guarded",
        "Unknown: Some factors",
        "Assumption: Proceeding with limited context",
    ]
    
    for phrase in forbidden_phrases:
        assert phrase not in result.rendered_text, f"Meta scaffolding found: {phrase}"


def test_fallback_is_helpful_not_meta():
    """
    Test that when LLM fails, fallback text is helpful, not meta scaffolding.
    """
    ctx = Step5Context(
        request_id="fallback_test",
        plan_value="free",
        breaker_open=False,
        budget_blocked=False,
        total_timeout_ms=5000,
        per_attempt_timeout_ms=2000,
        max_attempts=2,
        mode_requested=None,
        mode_effective="default",
        model_class_effective="balanced",
    )

    async def invoke_attempt(_: int) -> str:
        # Simulate LLM failure
        raise RuntimeError("LLM unavailable")

    result = asyncio.run(run_step5(ctx, invoke_attempt))
    
    # Should return FALLBACK action
    assert result.action == ChatAction.FALLBACK
    assert result.failure_type is not None
    
    # Fallback text should be helpful
    assert "Governed response unavailable" in result.rendered_text
    
    # Should NOT contain old meta scaffolding
    assert "Providing a concise response based on limited details" not in result.rendered_text
    assert "Confidence:" not in result.rendered_text
    assert "Unknown:" not in result.rendered_text
    assert "Assumption:" not in result.rendered_text
    
    # Should NOT contain the new fallback text meant for verification failures
    assert "limited mode" not in result.rendered_text.lower()
    assert "technical issue" not in result.rendered_text.lower()
