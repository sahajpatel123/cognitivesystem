import asyncio

from backend.app.chat_contract import ChatAction, FailureType
from backend.app.reliability.engine import Step5Context, run_step5


def test_breaker_short_circuit():
    ctx = Step5Context(
        request_id="r1",
        plan_value="pro",
        breaker_open=True,
        budget_blocked=False,
        total_timeout_ms=1000,
        per_attempt_timeout_ms=500,
        max_attempts=2,
        mode_requested=None,
        mode_effective="default",
        model_class_effective="balanced",
    )

    async def invoke_attempt(_: int) -> str:
        return "should not be called"

    result = asyncio.run(run_step5(ctx, invoke_attempt))
    assert result.action == ChatAction.FALLBACK
    assert result.failure_type == FailureType.PROVIDER_UNAVAILABLE
    assert result.attempts == 0


def test_budget_short_circuit():
    ctx = Step5Context(
        request_id="r2",
        plan_value="pro",
        breaker_open=False,
        budget_blocked=True,
        total_timeout_ms=1000,
        per_attempt_timeout_ms=500,
        max_attempts=2,
        mode_requested=None,
        mode_effective="default",
        model_class_effective="balanced",
    )

    async def invoke_attempt(_: int) -> str:
        return "should not be called"

    result = asyncio.run(run_step5(ctx, invoke_attempt))
    assert result.action == ChatAction.FALLBACK
    assert result.failure_type == FailureType.BUDGET_EXCEEDED
    assert result.attempts == 0


def test_forced_provider_timeout(monkeypatch):
    monkeypatch.setenv("FORCE_PROVIDER_TIMEOUT", "1")
    ctx = Step5Context(
        request_id="r3",
        plan_value="pro",
        breaker_open=False,
        budget_blocked=False,
        total_timeout_ms=200,
        per_attempt_timeout_ms=100,
        max_attempts=1,
        mode_requested=None,
        mode_effective="default",
        model_class_effective="balanced",
    )

    async def invoke_attempt(_: int) -> str:
        await asyncio.sleep(0)
        return "should not be reached"

    result = asyncio.run(run_step5(ctx, invoke_attempt))
    assert result.failure_type == FailureType.TIMEOUT
    assert result.action == ChatAction.FALLBACK
    assert result.timeout_where == "provider"
    assert result.attempts == 1
