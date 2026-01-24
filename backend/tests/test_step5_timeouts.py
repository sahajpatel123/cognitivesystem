import asyncio

from backend.app.chat_contract import ChatAction, FailureType
from backend.app.reliability.engine import Step5Context, run_step5


def test_per_attempt_timeout_triggers_timeout_where_provider():
    ctx = Step5Context(
        request_id="t1",
        plan_value="pro",
        breaker_open=False,
        budget_blocked=False,
        total_timeout_ms=200,
        per_attempt_timeout_ms=50,
        max_attempts=1,
        mode_requested=None,
        mode_effective="default",
        model_class_effective="balanced",
    )

    async def invoke_attempt(_: int) -> str:
        await asyncio.sleep(0.1)
        return "slow response"

    result = asyncio.run(run_step5(ctx, invoke_attempt))
    assert result.failure_type == FailureType.TIMEOUT
    assert result.action == ChatAction.FALLBACK
    assert result.timeout_where == "provider"
    assert result.attempts == 1
