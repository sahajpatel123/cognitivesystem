from backend.app.chat_contract import ChatAction
from backend.app.reliability.engine import Step5Context, run_step5
from backend.app.quality.gate import clarifying_prompt
import asyncio


def test_quality_gate_placeholder_triggers_clarify(monkeypatch):
    ctx = Step5Context(
        request_id="q1",
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
        return "Providing a concise response based on limited details. Placeholder."

    result = asyncio.run(run_step5(ctx, invoke_attempt))
    assert result.action == ChatAction.ASK_CLARIFY
    assert result.failure_type is None
    assert result.rendered_text == clarifying_prompt()
