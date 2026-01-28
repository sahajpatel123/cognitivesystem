"""
Phase 17 Step 3: Engine Determinism Tests

Tests for deterministic multi-pass engine orchestration.
"""

from backend.app.deepthink.engine import (
    run_engine,
    EngineInput,
    EngineOutput,
    EngineContext,
    PassRunResult,
    STOP_PRIORITY_ORDER,
)
from backend.app.deepthink.router import Plan
from backend.app.deepthink.schema import PatchOp


def make_fake_runner(deltas_sequence):
    """
    Create a fake pass runner that returns predetermined deltas.
    
    Args:
        deltas_sequence: List of (delta, cost, duration) tuples
    
    Returns:
        Callable pass runner
    """
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
    """
    Create a fake clock that increments deterministically.
    """
    time_ms = [initial_ms]
    
    def now_ms():
        current = time_ms[0]
        time_ms[0] += increment_ms
        return current
    
    return now_ms


class TestDeterministicReplay:
    """Test that engine produces identical results on replay."""
    
    def test_identical_inputs_produce_identical_outputs_50_times(self):
        """Run engine 50 times with same inputs -> identical outputs."""
        # Setup
        initial_state = {"decision": {"action": "REFUSE"}}
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
            ([PatchOp(op="set", path="decision.answer", value="Refined answer")], 50, 200),
        ]
        
        # Run 50 times
        results = []
        for i in range(50):
            context = EngineContext(
                request_signature=f"test-sig-{i}",
                now_ms=make_fake_clock(0, 100),
                budget_units_remaining=200,
            )
            
            engine_input = EngineInput(
                request_signature=f"test-sig-{i}",
                initial_state=initial_state,
                plan=plan,
                context=context,
                pass_runner=make_fake_runner(deltas),
            )
            
            output = run_engine(engine_input)
            results.append(output)
        
        # Verify all results are identical (except request_signature in decision_signature)
        first = results[0]
        for result in results[1:]:
            assert result.final_state == first.final_state
            assert result.meta.pass_count_executed == first.meta.pass_count_executed
            assert result.meta.stop_reason == first.meta.stop_reason
            assert result.meta.downgraded == first.meta.downgraded
            assert result.meta.validator_failures == first.meta.validator_failures
            # decision_signature will differ due to request_signature, but structure is same
            assert len(result.meta.pass_summaries) == len(first.meta.pass_summaries)


class TestOrderingDeterminism:
    """Test that delta application ordering is deterministic."""
    
    def test_multiple_passes_yield_deterministic_final_state(self):
        """Multiple passes with deltas yield same final state."""
        initial_state = {"decision": {}}
        plan = Plan(
            effective_pass_count=3,
            pass_plan=["REFINE", "COUNTERARG", "STRESS_TEST"],
            per_pass_budget=[100, 100, 100],
            per_pass_timeout_ms=[500, 500, 500],
            stop_reason=None,
            policy={},
        )
        
        deltas = [
            ([PatchOp(op="set", path="decision.action", value="ANSWER")], 50, 200),
            ([PatchOp(op="set", path="decision.answer", value="Answer text")], 50, 200),
            ([PatchOp(op="set", path="decision.rationale", value="Rationale text")], 50, 200),
        ]
        
        # Run twice
        outputs = []
        for _ in range(2):
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
            outputs.append(output)
        
        # Verify identical
        assert outputs[0].final_state == outputs[1].final_state
        assert outputs[0].meta.decision_signature == outputs[1].meta.decision_signature


class TestStopPriorityDeterminism:
    """Test that stop priority order is deterministic."""
    
    def test_multiple_stop_conditions_selects_highest_priority(self):
        """When multiple stop conditions trigger, highest priority wins."""
        initial_state = {"decision": {}}
        plan = Plan(
            effective_pass_count=2,
            pass_plan=["REFINE", "STRESS_TEST"],
            per_pass_budget=[100, 100],
            per_pass_timeout_ms=[500, 500],
            stop_reason=None,
            policy={},
        )
        
        # Setup context with multiple stop conditions
        # ABUSE has higher priority than BREAKER_TRIPPED
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0, 100),
            budget_units_remaining=0,  # BUDGET_EXHAUSTED
            breaker_tripped=True,  # BREAKER_TRIPPED
            abuse_blocked=True,  # ABUSE
        )
        
        deltas = [
            ([PatchOp(op="set", path="decision.action", value="ANSWER")], 50, 200),
        ]
        
        engine_input = EngineInput(
            request_signature="test-sig",
            initial_state=initial_state,
            plan=plan,
            context=context,
            pass_runner=make_fake_runner(deltas),
        )
        
        output = run_engine(engine_input)
        
        # Should select ABUSE (highest priority among triggered conditions)
        assert output.meta.stop_reason == "ABUSE"
        assert output.meta.downgraded
    
    def test_stop_priority_order_is_stable(self):
        """Stop priority order constant is stable."""
        # Verify STOP_PRIORITY_ORDER is as expected
        expected_order = [
            "INTERNAL_INCONSISTENCY",
            "ABUSE",
            "ENTITLEMENT_CAP",
            "BREAKER_TRIPPED",
            "BUDGET_EXHAUSTED",
            "TIMEOUT",
            "VALIDATION_FAIL",
            "PASS_LIMIT_REACHED",
            "SUCCESS_COMPLETED",
        ]
        assert STOP_PRIORITY_ORDER == expected_order


class TestSuccessCompletion:
    """Test successful completion path."""
    
    def test_all_passes_complete_successfully(self):
        """All passes complete -> SUCCESS_COMPLETED."""
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
            ([PatchOp(op="set", path="decision.answer", value="Final answer")], 50, 200),
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
        
        assert output.meta.stop_reason == "SUCCESS_COMPLETED"
        assert not output.meta.downgraded
        assert output.meta.pass_count_executed == 2
        assert output.final_state["decision"]["action"] == "ANSWER"
        assert output.final_state["decision"]["answer"] == "Final answer"


class TestRouterDisabledPlan:
    """Test that router-disabled plans are handled correctly."""
    
    def test_router_disabled_plan_returns_baseline(self):
        """Plan with stop_reason set -> immediate downgrade."""
        initial_state = {"decision": {"action": "REFUSE"}}
        plan = Plan(
            effective_pass_count=0,
            pass_plan=[],
            per_pass_budget=[],
            per_pass_timeout_ms=[],
            stop_reason="ENTITLEMENT_CAP",
            policy={},
        )
        
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
            pass_runner=make_fake_runner([]),
        )
        
        output = run_engine(engine_input)
        
        assert output.meta.stop_reason == "ENTITLEMENT_CAP"
        assert output.meta.downgraded
        assert output.final_state == initial_state


# Self-check runner for local verification
if __name__ == "__main__":
    print("Running Phase 17 Engine Determinism self-checks...")
    
    # Test 1: Deterministic replay
    initial_state = {"decision": {"action": "REFUSE"}}
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
        ([PatchOp(op="set", path="decision.answer", value="Refined")], 50, 200),
    ]
    
    results = []
    for i in range(10):
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
        results.append(output)
    
    # Verify all identical
    first = results[0]
    for result in results[1:]:
        assert result.final_state == first.final_state
        assert result.meta.stop_reason == first.meta.stop_reason
    print("✓ Deterministic replay (10 runs)")
    
    # Test 2: Stop priority
    context = EngineContext(
        request_signature="test-sig",
        now_ms=make_fake_clock(0, 100),
        budget_units_remaining=0,
        breaker_tripped=True,
        abuse_blocked=True,
    )
    
    engine_input = EngineInput(
        request_signature="test-sig",
        initial_state=initial_state,
        plan=plan,
        context=context,
        pass_runner=make_fake_runner(deltas),
    )
    
    output = run_engine(engine_input)
    assert output.meta.stop_reason == "ABUSE", "Should select highest priority stop reason"
    print("✓ Stop priority determinism")
    
    # Test 3: Success completion
    context = EngineContext(
        request_signature="test-sig",
        now_ms=make_fake_clock(0, 100),
        budget_units_remaining=200,
    )
    
    engine_input = EngineInput(
        request_signature="test-sig",
        initial_state={"decision": {}},
        plan=plan,
        context=context,
        pass_runner=make_fake_runner(deltas),
    )
    
    output = run_engine(engine_input)
    assert output.meta.stop_reason == "SUCCESS_COMPLETED"
    assert not output.meta.downgraded
    assert output.meta.pass_count_executed == 2
    print("✓ Success completion")
    
    print("\nAll self-checks PASSED ✓")
