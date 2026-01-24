from backend.app.chat_contract import ChatAction, FailureType
from backend.app.reliability.engine import Step5Context, run_step5
import asyncio


def test_safety_block_on_keyword():
    ctx = Step5Context(
        request_id="s1",
        plan_value="pro",
        breaker_open=False,
        budget_blocked=False,
        total_timeout_ms=500,
        per_attempt_timeout_ms=200,
        max_attempts=1,
        mode_requested=None,
        mode_effective="default",
        model_class_effective="balanced",
    )

    async def invoke_attempt(_: int) -> str:
        return "Please commit suicide now."

    result = asyncio.run(run_step5(ctx, invoke_attempt))
    assert result.action == ChatAction.FALLBACK
    assert result.failure_type == FailureType.SAFETY_BLOCKED
    assert result.failure_reason is not None
    assert result.attempts == 1
