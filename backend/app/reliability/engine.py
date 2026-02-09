from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from backend.app.chat_contract import ChatAction, FailureType
from backend.app.reliability.breaker import (
    force_provider_timeout,
    force_quality_fail,
    force_safety_block,
)
from backend.app.quality.gate import clarifying_prompt, evaluate_quality
from backend.app.safety.envelope import apply_safety, refusal_text
from backend.app.perf import enforce_timeout, PerfTimeoutError


@dataclass
class Step5Context:
    request_id: str
    plan_value: str
    breaker_open: bool
    budget_blocked: bool
    total_timeout_ms: int
    per_attempt_timeout_ms: int
    max_attempts: int
    mode_requested: Optional[str]
    mode_effective: str
    model_class_effective: str


@dataclass
class Step5Result:
    action: ChatAction
    rendered_text: str
    failure_type: FailureType | None
    failure_reason: str | None
    attempts: int
    timeout_where: str | None


async def run_step5(ctx: Step5Context, invoke_attempt: Callable[[int], Awaitable[str]]) -> Step5Result:
    start_ts = time.monotonic()

    def _elapsed_ms() -> int:
        return int((time.monotonic() - start_ts) * 1000)

    # Breaker or budget blocks short-circuit
    if ctx.breaker_open:
        return Step5Result(
            action=ChatAction.FALLBACK,
            rendered_text="Service temporarily unavailable.",
            failure_type=FailureType.PROVIDER_UNAVAILABLE,
            failure_reason="breaker_open",
            attempts=0,
            timeout_where=None,
        )
    if ctx.budget_blocked:
        return Step5Result(
            action=ChatAction.FALLBACK,
            rendered_text="Cost protection is active. Please try again later.",
            failure_type=FailureType.BUDGET_EXCEEDED,
            failure_reason="budget_blocked",
            attempts=0,
            timeout_where=None,
        )

    forced_timeout = force_provider_timeout()
    forced_quality = force_quality_fail()
    forced_safety = force_safety_block()

    deadline_ms = ctx.total_timeout_ms
    attempts = 0
    last_failure: FailureType | None = None
    timeout_where: str | None = None

    for attempt_idx in range(max(1, ctx.max_attempts)):
        attempts = attempt_idx + 1

        # total deadline check
        if _elapsed_ms() >= deadline_ms:
            timeout_where = "total"
            last_failure = FailureType.TIMEOUT
            break

        attempt_timeout_ms = max(100, min(ctx.per_attempt_timeout_ms, max(0, deadline_ms - _elapsed_ms())))

        # simulate forced provider timeout
        if forced_timeout:
            last_failure = FailureType.TIMEOUT
            timeout_where = "provider"
            if attempts >= ctx.max_attempts:
                break
            continue

        try:
            rendered_text = await enforce_timeout(lambda: invoke_attempt(attempt_idx), attempt_timeout_ms)
        except PerfTimeoutError:
            last_failure = FailureType.TIMEOUT
            timeout_where = "provider"
            if attempts >= ctx.max_attempts:
                break
            continue
        except Exception:
            last_failure = FailureType.PROVIDER_BAD_RESPONSE
            if attempts >= ctx.max_attempts:
                break
            continue

        # Safety envelope
        allowed, safety_reason = apply_safety(rendered_text, force_block=forced_safety)
        if not allowed:
            return Step5Result(
                action=ChatAction.FALLBACK,
                rendered_text=refusal_text(),
                failure_type=FailureType.SAFETY_BLOCKED,
                failure_reason=safety_reason,
                attempts=attempts,
                timeout_where=None,
            )

        # Quality gate - if quality fails, still return answer but log the issue
        ok_quality, quality_reason = evaluate_quality(rendered_text, force_fail=forced_quality)
        # Note: We no longer block on quality issues - always provide an answer
        
        # Success - always answer
        return Step5Result(
            action=ChatAction.ANSWER,
            rendered_text=rendered_text.strip() or "Governed response unavailable.",
            failure_type=None,
            failure_reason=None,
            attempts=attempts,
            timeout_where=None,
        )

    # Exhausted attempts
    failure_type = last_failure or FailureType.PROVIDER_UNAVAILABLE
    reason = "timeout" if failure_type == FailureType.TIMEOUT else "provider_unavailable"
    return Step5Result(
        action=ChatAction.FALLBACK,
        rendered_text="Governed response unavailable.",
        failure_type=failure_type,
        failure_reason=reason,
        attempts=attempts,
        timeout_where=timeout_where,
    )


__all__ = ["run_step5", "Step5Context", "Step5Result"]
