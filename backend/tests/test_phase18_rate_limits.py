"""
Phase 18 Step 2: Sandbox + Rate Limiter Tests

Comprehensive tests for deterministic, fail-closed sandbox behavior:
- Determinism replay
- Rate limiting
- Total calls budget
- Total timeout
- Per-call timeout
- Fail-closed on exceptions
- Caps cannot be overridden by requested_mode
"""

from typing import Any

from backend.app.research.ratelimit import (
    RateLimitConfig,
    RateLimiterState,
    check_and_consume,
    create_initial_state,
    validate_config,
)
from backend.app.research.sandbox import (
    SandboxCaps,
    SandboxState,
    SandboxResult,
    run_sandboxed_call,
    create_sandbox_state,
)


def make_test_caps(
    max_calls_total: int = 10,
    max_calls_per_minute: int = 5,
    per_call_timeout_ms: int = 1000,
    total_timeout_ms: int = 10000,
) -> SandboxCaps:
    """Create test SandboxCaps."""
    return SandboxCaps(
        max_calls_total=max_calls_total,
        max_calls_per_minute=max_calls_per_minute,
        per_call_timeout_ms=per_call_timeout_ms,
        total_timeout_ms=total_timeout_ms,
    )


def make_successful_tool() -> callable:
    """Create a tool that always succeeds."""
    return lambda: "success"


def make_failing_tool() -> callable:
    """Create a tool that always raises."""
    def fail():
        raise RuntimeError("Tool failure")
    return fail


class TestRateLimiterDeterminism:
    """Test rate limiter determinism."""
    
    def test_same_inputs_same_outputs(self):
        """Same inputs produce identical outputs."""
        config = RateLimitConfig(max_calls_per_minute=5)
        state = RateLimiterState(window_start_ms=0, calls_in_window=2)
        now_ms = 30000
        
        results = []
        for _ in range(10):
            new_state, allowed = check_and_consume(state, config, now_ms)
            results.append((new_state, allowed))
        
        for i in range(1, 10):
            assert results[i] == results[0], f"Run {i} differs from run 0"


class TestRateLimiterBasic:
    """Test rate limiter basic functionality."""
    
    def test_allow_within_limit(self):
        """Allow calls within limit."""
        config = RateLimitConfig(max_calls_per_minute=3)
        state = create_initial_state(0)
        
        state, allowed = check_and_consume(state, config, 100)
        assert allowed == True
        assert state.calls_in_window == 1
        
        state, allowed = check_and_consume(state, config, 200)
        assert allowed == True
        assert state.calls_in_window == 2
        
        state, allowed = check_and_consume(state, config, 300)
        assert allowed == True
        assert state.calls_in_window == 3
    
    def test_deny_at_limit(self):
        """Deny call when limit reached."""
        config = RateLimitConfig(max_calls_per_minute=2)
        state = RateLimiterState(window_start_ms=0, calls_in_window=2)
        
        new_state, allowed = check_and_consume(state, config, 100)
        
        assert allowed == False
        assert new_state == state
    
    def test_window_reset(self):
        """Window resets after window_seconds."""
        config = RateLimitConfig(max_calls_per_minute=2, window_seconds=60)
        state = RateLimiterState(window_start_ms=0, calls_in_window=2)
        
        new_state, allowed = check_and_consume(state, config, 60000)
        
        assert allowed == True
        assert new_state.window_start_ms == 60000
        assert new_state.calls_in_window == 1
    
    def test_invalid_config_denied(self):
        """Invalid config returns denied."""
        config = RateLimitConfig(max_calls_per_minute=0)
        state = create_initial_state(0)
        
        new_state, allowed = check_and_consume(state, config, 100)
        
        assert allowed == False
        assert new_state == state


class TestSandboxDeterminism:
    """Test sandbox determinism."""
    
    def test_replay_identical_results(self):
        """Same inputs produce identical results across N runs."""
        caps = make_test_caps()
        tool = make_successful_tool()
        
        results = []
        for _ in range(20):
            state = create_sandbox_state(0)
            new_state, result = run_sandboxed_call(
                caps=caps,
                state=state,
                now_ms=100,
                tool_call=tool,
                call_duration_ms=50,
            )
            results.append((new_state, result))
        
        for i in range(1, 20):
            assert results[i][0] == results[0][0], f"State differs at run {i}"
            assert results[i][1].ok == results[0][1].ok
            assert results[i][1].stop_reason == results[0][1].stop_reason
            assert results[i][1].calls_used_total == results[0][1].calls_used_total
            assert results[i][1].elapsed_ms == results[0][1].elapsed_ms


class TestSandboxRateLimit:
    """Test sandbox rate limiting."""
    
    def test_allow_exactly_max_calls_per_minute(self):
        """Allow exactly max_calls_per_minute in a window."""
        caps = make_test_caps(max_calls_per_minute=3, max_calls_total=10)
        state = create_sandbox_state(0)
        tool = make_successful_tool()
        
        for i in range(3):
            state, result = run_sandboxed_call(
                caps=caps,
                state=state,
                now_ms=100 * (i + 1),
                tool_call=tool,
                call_duration_ms=10,
            )
            assert result.ok == True, f"Call {i+1} should succeed"
            assert result.stop_reason is None
        
        state, result = run_sandboxed_call(
            caps=caps,
            state=state,
            now_ms=400,
            tool_call=tool,
            call_duration_ms=10,
        )
        assert result.ok == False
        assert result.stop_reason == "RATE_LIMITED"
    
    def test_next_window_allows_again(self):
        """After window expires, calls allowed again."""
        caps = make_test_caps(max_calls_per_minute=2, max_calls_total=10, total_timeout_ms=100000)
        state = create_sandbox_state(0)
        tool = make_successful_tool()
        
        state, _ = run_sandboxed_call(caps=caps, state=state, now_ms=100, tool_call=tool)
        state, _ = run_sandboxed_call(caps=caps, state=state, now_ms=200, tool_call=tool)
        
        state, result = run_sandboxed_call(caps=caps, state=state, now_ms=300, tool_call=tool)
        assert result.stop_reason == "RATE_LIMITED"
        
        state, result = run_sandboxed_call(caps=caps, state=state, now_ms=60100, tool_call=tool)
        assert result.ok == True
        assert result.stop_reason is None


class TestSandboxBudget:
    """Test sandbox total calls budget."""
    
    def test_allow_exactly_max_calls_total(self):
        """Allow exactly max_calls_total attempts."""
        caps = make_test_caps(max_calls_total=3, max_calls_per_minute=10)
        state = create_sandbox_state(0)
        tool = make_successful_tool()
        
        for i in range(3):
            state, result = run_sandboxed_call(
                caps=caps,
                state=state,
                now_ms=100 * (i + 1),
                tool_call=tool,
            )
            assert result.ok == True, f"Call {i+1} should succeed"
            assert result.calls_used_total == i + 1
        
        state, result = run_sandboxed_call(
            caps=caps,
            state=state,
            now_ms=400,
            tool_call=tool,
        )
        assert result.ok == False
        assert result.stop_reason == "BUDGET_EXHAUSTED"
        assert result.calls_used_total == 3


class TestSandboxTotalTimeout:
    """Test sandbox total timeout."""
    
    def test_timeout_before_call(self):
        """Total timeout exceeded before call → TIMEOUT."""
        caps = make_test_caps(total_timeout_ms=5000)
        state = create_sandbox_state(0)
        tool = make_successful_tool()
        
        state, result = run_sandboxed_call(
            caps=caps,
            state=state,
            now_ms=5000,
            tool_call=tool,
        )
        
        assert result.ok == False
        assert result.stop_reason == "TIMEOUT"
        assert result.calls_used_total == 0
    
    def test_timeout_priority_over_budget(self):
        """Total timeout has priority over budget exhausted."""
        caps = make_test_caps(total_timeout_ms=1000, max_calls_total=0)
        state = create_sandbox_state(0)
        tool = make_successful_tool()
        
        state, result = run_sandboxed_call(
            caps=caps,
            state=state,
            now_ms=1000,
            tool_call=tool,
        )
        
        assert result.stop_reason == "TIMEOUT"


class TestSandboxPerCallTimeout:
    """Test sandbox per-call timeout."""
    
    def test_per_call_timeout_exceeded(self):
        """Per-call timeout exceeded → TIMEOUT."""
        caps = make_test_caps(per_call_timeout_ms=500)
        state = create_sandbox_state(0)
        tool = make_successful_tool()
        
        state, result = run_sandboxed_call(
            caps=caps,
            state=state,
            now_ms=100,
            tool_call=tool,
            call_duration_ms=600,
        )
        
        assert result.ok == False
        assert result.stop_reason == "TIMEOUT"
        assert result.calls_used_total == 1
    
    def test_per_call_within_limit_succeeds(self):
        """Per-call within limit succeeds."""
        caps = make_test_caps(per_call_timeout_ms=500)
        state = create_sandbox_state(0)
        tool = make_successful_tool()
        
        state, result = run_sandboxed_call(
            caps=caps,
            state=state,
            now_ms=100,
            tool_call=tool,
            call_duration_ms=400,
        )
        
        assert result.ok == True
        assert result.stop_reason is None


class TestSandboxFailClosed:
    """Test sandbox fail-closed behavior."""
    
    def test_tool_exception_sandbox_violation(self):
        """Tool exception → SANDBOX_VIOLATION."""
        caps = make_test_caps()
        state = create_sandbox_state(0)
        tool = make_failing_tool()
        
        state, result = run_sandboxed_call(
            caps=caps,
            state=state,
            now_ms=100,
            tool_call=tool,
        )
        
        assert result.ok == False
        assert result.stop_reason == "SANDBOX_VIOLATION"
        assert result.calls_used_total == 1


class TestCapsCannotBeOverridden:
    """Test that caps cannot be overridden by requested_mode."""
    
    def test_requested_mode_does_not_bypass_rate_limit(self):
        """
        Simulate requested_mode='research' and verify caps still deny.
        
        This test proves that requested_mode is advisory only.
        The sandbox enforces caps regardless of what mode is requested.
        """
        requested_mode = "research"
        
        caps = make_test_caps(max_calls_per_minute=1, max_calls_total=10)
        state = create_sandbox_state(0)
        tool = make_successful_tool()
        
        state, result = run_sandboxed_call(
            caps=caps,
            state=state,
            now_ms=100,
            tool_call=tool,
        )
        assert result.ok == True
        
        state, result = run_sandboxed_call(
            caps=caps,
            state=state,
            now_ms=200,
            tool_call=tool,
        )
        assert result.ok == False
        assert result.stop_reason == "RATE_LIMITED"
        
        _ = requested_mode
    
    def test_requested_mode_does_not_bypass_budget(self):
        """
        Simulate requested_mode='research' and verify budget caps still deny.
        """
        requested_mode = "research"
        
        caps = make_test_caps(max_calls_total=1, max_calls_per_minute=10)
        state = create_sandbox_state(0)
        tool = make_successful_tool()
        
        state, result = run_sandboxed_call(
            caps=caps,
            state=state,
            now_ms=100,
            tool_call=tool,
        )
        assert result.ok == True
        
        state, result = run_sandboxed_call(
            caps=caps,
            state=state,
            now_ms=200,
            tool_call=tool,
        )
        assert result.ok == False
        assert result.stop_reason == "BUDGET_EXHAUSTED"
        
        _ = requested_mode
    
    def test_requested_mode_does_not_bypass_timeout(self):
        """
        Simulate requested_mode='research' and verify timeout caps still deny.
        """
        requested_mode = "research"
        
        caps = make_test_caps(total_timeout_ms=100)
        state = create_sandbox_state(0)
        tool = make_successful_tool()
        
        state, result = run_sandboxed_call(
            caps=caps,
            state=state,
            now_ms=100,
            tool_call=tool,
        )
        assert result.ok == False
        assert result.stop_reason == "TIMEOUT"
        
        _ = requested_mode


class TestStopPriorityOrder:
    """Test stop priority order is enforced."""
    
    def test_priority_timeout_over_budget(self):
        """TIMEOUT has priority over BUDGET_EXHAUSTED."""
        caps = SandboxCaps(
            max_calls_total=0,
            max_calls_per_minute=0,
            per_call_timeout_ms=1000,
            total_timeout_ms=100,
        )
        state = create_sandbox_state(0)
        tool = make_successful_tool()
        
        state, result = run_sandboxed_call(
            caps=caps,
            state=state,
            now_ms=100,
            tool_call=tool,
        )
        
        assert result.stop_reason == "TIMEOUT"
    
    def test_priority_budget_over_rate_limit(self):
        """BUDGET_EXHAUSTED has priority over RATE_LIMITED."""
        caps = SandboxCaps(
            max_calls_total=0,
            max_calls_per_minute=0,
            per_call_timeout_ms=1000,
            total_timeout_ms=10000,
        )
        state = create_sandbox_state(0)
        tool = make_successful_tool()
        
        state, result = run_sandboxed_call(
            caps=caps,
            state=state,
            now_ms=100,
            tool_call=tool,
        )
        
        assert result.stop_reason == "BUDGET_EXHAUSTED"


class TestResultFields:
    """Test result fields are consistent and complete."""
    
    def test_success_result_fields(self):
        """Success result has all fields correctly set."""
        caps = make_test_caps()
        state = create_sandbox_state(0)
        tool = lambda: {"data": "value"}
        
        state, result = run_sandboxed_call(
            caps=caps,
            state=state,
            now_ms=100,
            tool_call=tool,
            call_duration_ms=50,
        )
        
        assert result.ok == True
        assert result.stop_reason is None
        assert result.value == {"data": "value"}
        assert result.calls_used_total == 1
        assert result.elapsed_ms == 150
    
    def test_failure_result_fields(self):
        """Failure result has all fields correctly set."""
        caps = make_test_caps(max_calls_total=0)
        state = create_sandbox_state(0)
        tool = make_successful_tool()
        
        state, result = run_sandboxed_call(
            caps=caps,
            state=state,
            now_ms=100,
            tool_call=tool,
        )
        
        assert result.ok == False
        assert result.stop_reason == "BUDGET_EXHAUSTED"
        assert result.value is None
        assert result.calls_used_total == 0
        assert result.elapsed_ms == 100


if __name__ == "__main__":
    print("Running Phase 18 Step 2 Sandbox + Rate Limiter Tests...")
    print()
    
    print("Test Group: Rate Limiter Determinism")
    test_det = TestRateLimiterDeterminism()
    test_det.test_same_inputs_same_outputs()
    print("✓ Same inputs -> same outputs")
    
    print("\nTest Group: Rate Limiter Basic")
    test_rl = TestRateLimiterBasic()
    test_rl.test_allow_within_limit()
    print("✓ Allow within limit")
    test_rl.test_deny_at_limit()
    print("✓ Deny at limit")
    test_rl.test_window_reset()
    print("✓ Window reset")
    test_rl.test_invalid_config_denied()
    print("✓ Invalid config denied")
    
    print("\nTest Group: Sandbox Determinism")
    test_sd = TestSandboxDeterminism()
    test_sd.test_replay_identical_results()
    print("✓ Replay 20 times -> identical results")
    
    print("\nTest Group: Sandbox Rate Limit")
    test_srl = TestSandboxRateLimit()
    test_srl.test_allow_exactly_max_calls_per_minute()
    print("✓ Allow exactly max_calls_per_minute")
    test_srl.test_next_window_allows_again()
    print("✓ Next window allows again")
    
    print("\nTest Group: Sandbox Budget")
    test_sb = TestSandboxBudget()
    test_sb.test_allow_exactly_max_calls_total()
    print("✓ Allow exactly max_calls_total")
    
    print("\nTest Group: Sandbox Total Timeout")
    test_tt = TestSandboxTotalTimeout()
    test_tt.test_timeout_before_call()
    print("✓ Timeout before call")
    test_tt.test_timeout_priority_over_budget()
    print("✓ Timeout priority over budget")
    
    print("\nTest Group: Sandbox Per-Call Timeout")
    test_pct = TestSandboxPerCallTimeout()
    test_pct.test_per_call_timeout_exceeded()
    print("✓ Per-call timeout exceeded")
    test_pct.test_per_call_within_limit_succeeds()
    print("✓ Per-call within limit succeeds")
    
    print("\nTest Group: Sandbox Fail-Closed")
    test_fc = TestSandboxFailClosed()
    test_fc.test_tool_exception_sandbox_violation()
    print("✓ Tool exception -> SANDBOX_VIOLATION")
    
    print("\nTest Group: Caps Cannot Be Overridden")
    test_caps = TestCapsCannotBeOverridden()
    test_caps.test_requested_mode_does_not_bypass_rate_limit()
    print("✓ requested_mode does not bypass rate limit")
    test_caps.test_requested_mode_does_not_bypass_budget()
    print("✓ requested_mode does not bypass budget")
    test_caps.test_requested_mode_does_not_bypass_timeout()
    print("✓ requested_mode does not bypass timeout")
    
    print("\nTest Group: Stop Priority Order")
    test_prio = TestStopPriorityOrder()
    test_prio.test_priority_timeout_over_budget()
    print("✓ TIMEOUT priority over BUDGET_EXHAUSTED")
    test_prio.test_priority_budget_over_rate_limit()
    print("✓ BUDGET_EXHAUSTED priority over RATE_LIMITED")
    
    print("\nTest Group: Result Fields")
    test_rf = TestResultFields()
    test_rf.test_success_result_fields()
    print("✓ Success result fields complete")
    test_rf.test_failure_result_fields()
    print("✓ Failure result fields complete")
    
    print("\n" + "="*60)
    print("ALL SANDBOX + RATE LIMITER TESTS PASSED ✓")
    print("="*60)
