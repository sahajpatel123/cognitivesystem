"""
Phase 17 Step 3: Engine Budget and Timeout Tests

Tests for budget exhaustion, timeout, breaker, and validator 2-strikes.
"""

from backend.app.deepthink.engine import (
    run_engine,
    EngineInput,
    EngineContext,
    PassRunResult,
)
from backend.app.deepthink.router import Plan
from backend.app.deepthink.schema import PatchOp


def make_fake_runner(deltas_sequence):
    """Create a fake pass runner with predetermined deltas."""
    call_count = [0]
    
    def runner(pass_type, state, context):
        idx = call_count[0]
        call_count[0] += 1
        
        if idx < len(deltas_sequence):
            delta, cost, duration = deltas_sequence[idx]
            return PassRunResult(
                pass_type=pass_type,
                delta=delta,
                cost_units=cost,
                duration_ms=duration,
                error=None,
            )
        else:
            return PassRunResult(
                pass_type=pass_type,
                delta=None,
                cost_units=0,
                duration_ms=0,
                error="No more deltas",
            )
    
    return runner


def make_fake_clock(initial_ms=0, increment_ms=100):
    """Create a fake clock that increments deterministically."""
    time_ms = [initial_ms]
    
    def now_ms():
        current = time_ms[0]
        time_ms[0] += increment_ms
        return current
    
    return now_ms


class TestBudgetExhaustion:
    """Test budget exhaustion scenarios."""
    
    def test_budget_exhausted_before_pass_stops_execution(self):
        """Budget exhausted before a pass -> BUDGET_EXHAUSTED."""
        initial_state = {"decision": {}}
        plan = Plan(
            effective_pass_count=3,
            pass_plan=["REFINE", "COUNTERARG", "STRESS_TEST"],
            per_pass_budget=[100, 100, 100],
            per_pass_timeout_ms=[500, 500, 500],
            stop_reason=None,
            policy={},
        )
        
        # First pass consumes all budget
        deltas = [
            ([PatchOp(op="set", path="decision.action", value="ANSWER")], 150, 200),
            ([PatchOp(op="set", path="decision.answer", value="Text")], 50, 200),
        ]
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0, 100),
            budget_units_remaining=150,  # Only enough for first pass
        )
        
        engine_input = EngineInput(
            request_signature="test-sig",
            initial_state=initial_state,
            plan=plan,
            context=context,
            pass_runner=make_fake_runner(deltas),
        )
        
        output = run_engine(engine_input)
        
        # Should stop after first pass due to budget exhaustion
        assert output.meta.stop_reason == "BUDGET_EXHAUSTED"
        assert output.meta.downgraded
        assert output.meta.pass_count_executed == 1
    
    def test_budget_tracks_correctly_across_passes(self):
        """Budget decrements correctly across passes."""
        initial_state = {"decision": {}}
        plan = Plan(
            effective_pass_count=2,
            pass_plan=["REFINE", "STRESS_TEST"],
            per_pass_budget=[100, 100],
            per_pass_timeout_ms=[500, 500],
            stop_reason=None,
            policy={},
        )
        
        deltas = [
            ([PatchOp(op="set", path="decision.action", value="ANSWER")], 50, 200),
            ([PatchOp(op="set", path="decision.answer", value="Text")], 50, 200),
        ]
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0, 100),
            budget_units_remaining=100,  # Exactly enough for both passes
        )
        
        engine_input = EngineInput(
            request_signature="test-sig",
            initial_state=initial_state,
            plan=plan,
            context=context,
            pass_runner=make_fake_runner(deltas),
        )
        
        output = run_engine(engine_input)
        
        # Should complete both passes
        assert output.meta.stop_reason == "SUCCESS_COMPLETED"
        assert output.meta.pass_count_executed == 2


class TestTimeoutEnforcement:
    """Test timeout enforcement scenarios."""
    
    def test_timeout_exceeded_stops_execution(self):
        """Clock exceeds total timeout -> TIMEOUT."""
        initial_state = {"decision": {}}
        plan = Plan(
            effective_pass_count=3,
            pass_plan=["REFINE", "COUNTERARG", "STRESS_TEST"],
            per_pass_budget=[100, 100, 100],
            per_pass_timeout_ms=[500, 500, 500],  # Total 1500ms
            stop_reason=None,
            policy={},
        )
        
        deltas = [
            ([PatchOp(op="set", path="decision.action", value="ANSWER")], 50, 200),
            ([PatchOp(op="set", path="decision.answer", value="Text")], 50, 200),
        ]
        
        # Clock increments by 800ms per call, exceeding 1500ms total after 2 calls
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0, 800),
            budget_units_remaining=300,
        )
        
        engine_input = EngineInput(
            request_signature="test-sig",
            initial_state=initial_state,
            plan=plan,
            context=context,
            pass_runner=make_fake_runner(deltas),
        )
        
        output = run_engine(engine_input)
        
        # Should stop due to timeout
        assert output.meta.stop_reason == "TIMEOUT"
        assert output.meta.downgraded


class TestBreakerTrip:
    """Test breaker trip scenarios."""
    
    def test_breaker_tripped_stops_execution(self):
        """Breaker tripped -> BREAKER_TRIPPED."""
        initial_state = {"decision": {}}
        plan = Plan(
            effective_pass_count=2,
            pass_plan=["REFINE", "STRESS_TEST"],
            per_pass_budget=[100, 100],
            per_pass_timeout_ms=[500, 500],
            stop_reason=None,
            policy={},
        )
        
        deltas = [
            ([PatchOp(op="set", path="decision.action", value="ANSWER")], 50, 200),
        ]
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0, 100),
            budget_units_remaining=200,
            breaker_tripped=True,  # Breaker tripped
        )
        
        engine_input = EngineInput(
            request_signature="test-sig",
            initial_state=initial_state,
            plan=plan,
            context=context,
            pass_runner=make_fake_runner(deltas),
        )
        
        output = run_engine(engine_input)
        
        assert output.meta.stop_reason == "BREAKER_TRIPPED"
        assert output.meta.downgraded
        assert output.meta.pass_count_executed == 0


class TestValidatorTwoStrikes:
    """Test validator 2-strikes rule."""
    
    def test_two_invalid_deltas_trigger_validation_fail(self):
        """Two invalid deltas -> VALIDATION_FAIL, downgraded."""
        initial_state = {"decision": {}}
        plan = Plan(
            effective_pass_count=3,
            pass_plan=["REFINE", "COUNTERARG", "STRESS_TEST"],
            per_pass_budget=[100, 100, 100],
            per_pass_timeout_ms=[500, 500, 500],
            stop_reason=None,
            policy={},
        )
        
        # First delta invalid, second delta invalid -> 2 strikes
        deltas = [
            ([PatchOp(op="set", path="unknown.path", value="test")], 50, 200),  # Invalid
            ([PatchOp(op="set", path="another.unknown", value="test")], 50, 200),  # Invalid
        ]
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0, 100),
            budget_units_remaining=300,
        )
        
        engine_input = EngineInput(
            request_signature="test-sig",
            initial_state=initial_state,
            plan=plan,
            context=context,
            pass_runner=make_fake_runner(deltas),
        )
        
        output = run_engine(engine_input)
        
        # Should stop after second invalid delta
        assert output.meta.stop_reason == "VALIDATION_FAIL"
        assert output.meta.downgraded
        assert output.meta.validator_failures == 2
        assert output.meta.pass_count_executed == 2
    
    def test_one_invalid_delta_continues_execution(self):
        """One invalid delta -> continues with 1 strike."""
        initial_state = {"decision": {}}
        plan = Plan(
            effective_pass_count=2,
            pass_plan=["REFINE", "STRESS_TEST"],
            per_pass_budget=[100, 100],
            per_pass_timeout_ms=[500, 500],
            stop_reason=None,
            policy={},
        )
        
        # First delta invalid, second delta valid
        deltas = [
            ([PatchOp(op="set", path="unknown.path", value="test")], 50, 200),  # Invalid
            ([PatchOp(op="set", path="decision.action", value="ANSWER")], 50, 200),  # Valid
        ]
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0, 100),
            budget_units_remaining=200,
        )
        
        engine_input = EngineInput(
            request_signature="test-sig",
            initial_state=initial_state,
            plan=plan,
            context=context,
            pass_runner=make_fake_runner(deltas),
        )
        
        output = run_engine(engine_input)
        
        # Should complete with 1 validator failure
        assert output.meta.stop_reason == "SUCCESS_COMPLETED"
        assert not output.meta.downgraded
        assert output.meta.validator_failures == 1
        assert output.meta.pass_count_executed == 2
    
    def test_exactly_two_failures_triggers_downgrade(self):
        """Exactly 2 failures trigger downgrade, not 1 or 3."""
        initial_state = {"decision": {}}
        plan = Plan(
            effective_pass_count=3,
            pass_plan=["REFINE", "COUNTERARG", "STRESS_TEST"],
            per_pass_budget=[100, 100, 100],
            per_pass_timeout_ms=[500, 500, 500],
            stop_reason=None,
            policy={},
        )
        
        # Invalid, invalid -> should stop at 2
        deltas = [
            ([PatchOp(op="set", path="unknown.path1", value="test")], 50, 200),
            ([PatchOp(op="set", path="unknown.path2", value="test")], 50, 200),
            ([PatchOp(op="set", path="decision.action", value="ANSWER")], 50, 200),
        ]
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0, 100),
            budget_units_remaining=300,
        )
        
        engine_input = EngineInput(
            request_signature="test-sig",
            initial_state=initial_state,
            plan=plan,
            context=context,
            pass_runner=make_fake_runner(deltas),
        )
        
        output = run_engine(engine_input)
        
        # Should stop exactly at 2 failures
        assert output.meta.stop_reason == "VALIDATION_FAIL"
        assert output.meta.validator_failures == 2
        assert output.meta.pass_count_executed == 2  # Stopped before 3rd pass


class TestPassLimitReached:
    """Test pass limit enforcement."""
    
    def test_pass_limit_5_enforced(self):
        """Pass count > 5 -> PASS_LIMIT_REACHED."""
        initial_state = {"decision": {}}
        plan = Plan(
            effective_pass_count=6,  # Exceeds max
            pass_plan=["REFINE", "COUNTERARG", "STRESS_TEST", "ALTERNATIVES", "REGRET", "EXTRA"],
            per_pass_budget=[100] * 6,
            per_pass_timeout_ms=[500] * 6,
            stop_reason=None,
            policy={},
        )
        
        deltas = [
            ([PatchOp(op="set", path="decision.action", value="ANSWER")], 50, 200),
        ] * 6
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0, 100),
            budget_units_remaining=600,
        )
        
        engine_input = EngineInput(
            request_signature="test-sig",
            initial_state=initial_state,
            plan=plan,
            context=context,
            pass_runner=make_fake_runner(deltas),
        )
        
        output = run_engine(engine_input)
        
        # Should reject plan with > 5 passes
        assert output.meta.stop_reason == "PASS_LIMIT_REACHED"
        assert output.meta.downgraded


# Self-check runner for local verification
if __name__ == "__main__":
    print("Running Phase 17 Engine Budget/Timeout self-checks...")
    
    # Test 1: Budget exhaustion
    initial_state = {"decision": {}}
    plan = Plan(
        effective_pass_count=2,
        pass_plan=["REFINE", "STRESS_TEST"],
        per_pass_budget=[100, 100],
        per_pass_timeout_ms=[500, 500],
        stop_reason=None,
        policy={},
    )
    
    deltas = [
        ([PatchOp(op="set", path="decision.action", value="ANSWER")], 150, 200),
    ]
    
    context = EngineContext(
        request_signature="test-sig",
        now_ms=make_fake_clock(0, 100),
        budget_units_remaining=150,
    )
    
    engine_input = EngineInput(
        request_signature="test-sig",
        initial_state=initial_state,
        plan=plan,
        context=context,
        pass_runner=make_fake_runner(deltas),
    )
    
    output = run_engine(engine_input)
    assert output.meta.stop_reason == "BUDGET_EXHAUSTED"
    print("✓ Budget exhaustion")
    
    # Test 2: Timeout
    plan = Plan(
        effective_pass_count=2,
        pass_plan=["REFINE", "STRESS_TEST"],
        per_pass_budget=[100, 100],
        per_pass_timeout_ms=[500, 500],
        stop_reason=None,
        policy={},
    )
    
    context = EngineContext(
        request_signature="test-sig",
        now_ms=make_fake_clock(0, 800),
        budget_units_remaining=300,
    )
    
    engine_input = EngineInput(
        request_signature="test-sig",
        initial_state=initial_state,
        plan=plan,
        context=context,
        pass_runner=make_fake_runner(deltas),
    )
    
    output = run_engine(engine_input)
    assert output.meta.stop_reason == "TIMEOUT"
    print("✓ Timeout enforcement")
    
    # Test 3: Breaker trip
    context = EngineContext(
        request_signature="test-sig",
        now_ms=make_fake_clock(0, 100),
        budget_units_remaining=300,
        breaker_tripped=True,
    )
    
    engine_input = EngineInput(
        request_signature="test-sig",
        initial_state=initial_state,
        plan=plan,
        context=context,
        pass_runner=make_fake_runner(deltas),
    )
    
    output = run_engine(engine_input)
    assert output.meta.stop_reason == "BREAKER_TRIPPED"
    print("✓ Breaker trip")
    
    # Test 4: 2-strikes validation
    plan = Plan(
        effective_pass_count=3,
        pass_plan=["REFINE", "COUNTERARG", "STRESS_TEST"],
        per_pass_budget=[100, 100, 100],
        per_pass_timeout_ms=[500, 500, 500],
        stop_reason=None,
        policy={},
    )
    
    invalid_deltas = [
        ([PatchOp(op="set", path="unknown.path1", value="test")], 50, 200),
        ([PatchOp(op="set", path="unknown.path2", value="test")], 50, 200),
    ]
    
    context = EngineContext(
        request_signature="test-sig",
        now_ms=make_fake_clock(0, 100),
        budget_units_remaining=300,
    )
    
    engine_input = EngineInput(
        request_signature="test-sig",
        initial_state=initial_state,
        plan=plan,
        context=context,
        pass_runner=make_fake_runner(invalid_deltas),
    )
    
    output = run_engine(engine_input)
    assert output.meta.stop_reason == "VALIDATION_FAIL"
    assert output.meta.validator_failures == 2
    print("✓ 2-strikes validation")
    
    print("\nAll self-checks PASSED ✓")
