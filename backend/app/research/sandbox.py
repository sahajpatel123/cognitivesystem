"""
Phase 18 Step 2: Deterministic Sandbox Wrapper

Fail-closed sandbox that enforces strict caps on tool calls:
- max calls total (budget)
- max calls per minute (rate limit)
- per-call timeout
- total research timeout

Contract guarantees:
- Deterministic: same inputs + same time → same outputs
- Fail-closed: any error → STOP with contract stop reason
- Non-agentic: no retries, no planning, no escalation
- Caps cannot be overridden by requested_mode

Stop Priority Order (FIXED, first match wins):
1. total_timeout_ms exceeded BEFORE call → TIMEOUT
2. total calls budget exhausted BEFORE call → BUDGET_EXHAUSTED
3. rate limit exceeded BEFORE call → RATE_LIMITED
4. per-call timeout exceeded (call_duration_ms > per_call_timeout_ms) → TIMEOUT
5. tool_call raises exception → SANDBOX_VIOLATION
"""

from dataclasses import dataclass
from typing import Tuple, Callable, Any, Optional

from backend.app.research.ratelimit import (
    RateLimitConfig,
    RateLimiterState,
    check_and_consume,
    create_initial_state,
)


@dataclass(frozen=True)
class SandboxCaps:
    """
    Sandbox capability caps.
    
    These caps CANNOT be overridden by requested_mode.
    Policy decides; requested_mode is advisory only.
    
    Attributes:
        max_calls_total: Maximum total tool calls allowed
        max_calls_per_minute: Maximum calls per minute (rate limit)
        per_call_timeout_ms: Maximum duration per call in milliseconds
        total_timeout_ms: Maximum total research duration in milliseconds
    """
    max_calls_total: int
    max_calls_per_minute: int
    per_call_timeout_ms: int
    total_timeout_ms: int


@dataclass(frozen=True)
class SandboxState:
    """
    Sandbox state (immutable).
    
    Attributes:
        started_at_ms: When sandbox session started (milliseconds)
        calls_used_total: Total calls made so far
        rate_state: Rate limiter state
    """
    started_at_ms: int
    calls_used_total: int
    rate_state: RateLimiterState


@dataclass(frozen=True)
class SandboxResult:
    """
    Result of a sandboxed call attempt.
    
    Attributes:
        ok: True if call succeeded, False if stopped
        stop_reason: Contract stop reason string if stopped, None if ok
        value: Return value from tool_call if ok, None otherwise
        calls_used_total: Total calls used after this attempt
        elapsed_ms: Time elapsed since sandbox started
    """
    ok: bool
    stop_reason: Optional[str]
    value: Optional[Any]
    calls_used_total: int
    elapsed_ms: int


def create_sandbox_state(now_ms: int) -> SandboxState:
    """
    Create initial sandbox state.
    
    Args:
        now_ms: Current time in milliseconds
    
    Returns:
        Fresh sandbox state with zero calls used
    """
    return SandboxState(
        started_at_ms=now_ms,
        calls_used_total=0,
        rate_state=create_initial_state(now_ms),
    )


def run_sandboxed_call(
    *,
    caps: SandboxCaps,
    state: SandboxState,
    now_ms: int,
    tool_call: Callable[[], Any],
    call_duration_ms: Optional[int] = None,
) -> Tuple[SandboxState, SandboxResult]:
    """
    Execute a tool call within sandbox constraints.
    
    Deterministic, fail-closed execution with strict priority order:
    1. total_timeout_ms exceeded BEFORE call → TIMEOUT
    2. total calls budget exhausted BEFORE call → BUDGET_EXHAUSTED
    3. rate limit exceeded BEFORE call → RATE_LIMITED
    4. per-call timeout exceeded (call_duration_ms > per_call_timeout_ms) → TIMEOUT
    5. tool_call raises exception → SANDBOX_VIOLATION
    
    Args:
        caps: Sandbox capability caps (CANNOT be overridden)
        state: Current sandbox state
        now_ms: Current time in milliseconds (injected for determinism)
        tool_call: Callable to execute (no args, returns Any)
        call_duration_ms: Simulated call duration for deterministic testing
                         (None defaults to 0)
    
    Returns:
        Tuple of (new_state, result)
        - new_state: Updated sandbox state
        - result: SandboxResult with ok/stop_reason/value/calls_used_total/elapsed_ms
    
    Note: This function NEVER retries. One attempt max per invocation.
    """
    if call_duration_ms is None:
        call_duration_ms = 0
    
    elapsed_ms = now_ms - state.started_at_ms
    
    if elapsed_ms >= caps.total_timeout_ms:
        return (
            state,
            SandboxResult(
                ok=False,
                stop_reason="TIMEOUT",
                value=None,
                calls_used_total=state.calls_used_total,
                elapsed_ms=elapsed_ms,
            ),
        )
    
    if state.calls_used_total >= caps.max_calls_total:
        return (
            state,
            SandboxResult(
                ok=False,
                stop_reason="BUDGET_EXHAUSTED",
                value=None,
                calls_used_total=state.calls_used_total,
                elapsed_ms=elapsed_ms,
            ),
        )
    
    rate_config = RateLimitConfig(
        max_calls_per_minute=caps.max_calls_per_minute,
        window_seconds=60,
    )
    new_rate_state, rate_allowed = check_and_consume(
        state.rate_state,
        rate_config,
        now_ms,
    )
    
    if not rate_allowed:
        return (
            state,
            SandboxResult(
                ok=False,
                stop_reason="RATE_LIMITED",
                value=None,
                calls_used_total=state.calls_used_total,
                elapsed_ms=elapsed_ms,
            ),
        )
    
    new_calls_used = state.calls_used_total + 1
    
    if call_duration_ms > caps.per_call_timeout_ms:
        new_state = SandboxState(
            started_at_ms=state.started_at_ms,
            calls_used_total=new_calls_used,
            rate_state=new_rate_state,
        )
        return (
            new_state,
            SandboxResult(
                ok=False,
                stop_reason="TIMEOUT",
                value=None,
                calls_used_total=new_calls_used,
                elapsed_ms=elapsed_ms + call_duration_ms,
            ),
        )
    
    try:
        result_value = tool_call()
    except Exception:
        new_state = SandboxState(
            started_at_ms=state.started_at_ms,
            calls_used_total=new_calls_used,
            rate_state=new_rate_state,
        )
        return (
            new_state,
            SandboxResult(
                ok=False,
                stop_reason="SANDBOX_VIOLATION",
                value=None,
                calls_used_total=new_calls_used,
                elapsed_ms=elapsed_ms + call_duration_ms,
            ),
        )
    
    new_state = SandboxState(
        started_at_ms=state.started_at_ms,
        calls_used_total=new_calls_used,
        rate_state=new_rate_state,
    )
    
    return (
        new_state,
        SandboxResult(
            ok=True,
            stop_reason=None,
            value=result_value,
            calls_used_total=new_calls_used,
            elapsed_ms=elapsed_ms + call_duration_ms,
        ),
    )
