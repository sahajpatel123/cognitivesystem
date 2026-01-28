"""
Phase 17 Step 9: Evaluation Gates

CI-grade tests that prove Phase 17 invariants and prevent regressions.
These gates must PASS for Phase 17 certification.
"""

import json
import copy
from typing import Dict, Any, List, Optional, Callable

from backend.app.deepthink.engine import (
    EngineInput,
    EngineOutput,
    EngineContext,
    PassRunResult,
    run_engine,
)
from backend.app.deepthink.router import Plan, StopReason
from backend.app.deepthink.schema import PatchOp, DecisionAction
from backend.app.deepthink.telemetry import (
    compute_decision_signature,
    build_telemetry_event,
    sanitize_summary_for_logging,
)


# Sentinel strings for leakage detection
USER_SENTINEL = "SENSITIVE_USER_TEXT_123"
ASSIST_SENTINEL = "SENSITIVE_ASSISTANT_TEXT_456"


def make_fake_clock(initial_ms=0):
    """Create deterministic fake clock."""
    time_ms = [initial_ms]
    
    def now_ms():
        return time_ms[0]
    
    def advance(delta_ms):
        time_ms[0] += delta_ms
    
    now_ms.advance = advance
    return now_ms


def make_deterministic_runner(deltas_sequence: List[List[PatchOp]]):
    """
    Create deterministic pass runner that returns fixed deltas.
    
    Args:
        deltas_sequence: List of delta lists, one per pass execution
    
    Returns:
        Runner function that returns PassRunResult with predetermined deltas
    """
    call_count = [0]
    
    def runner(pass_type: str, state: Dict[str, Any], context: EngineContext) -> PassRunResult:
        idx = call_count[0]
        call_count[0] += 1
        
        if idx < len(deltas_sequence):
            delta = deltas_sequence[idx]
        else:
            delta = []
        
        return PassRunResult(
            pass_type=pass_type,
            delta=delta,
            cost_units=50,
            duration_ms=100,
            error=None,
        )
    
    return runner


class TestDeterministicReplayGate:
    """
    Gate A: Deterministic Replay Gate
    
    Proves that identical inputs produce identical outputs across all components.
    """
    
    def test_replay_20_times_identical_outputs(self):
        """Run engine 20 times with identical inputs -> all outputs identical."""
        # Arrange: deterministic inputs
        initial_state = {
            "decision": {
                "action": "ANSWER",
                "answer": "Initial answer",
                "rationale": "Initial rationale",
            }
        }
        
        plan = Plan(
            effective_pass_count=2,
            pass_plan=["COUNTERARG", "STRESS_TEST"],
            per_pass_budget=[100, 100],
            per_pass_timeout_ms=[500, 500],
            stop_reason=None,
        )
        
        # Deterministic deltas
        deltas_sequence = [
            [PatchOp(op="set", path="decision.rationale", value="Refined rationale")],
            [PatchOp(op="set", path="decision.action", value="ASK_CLARIFY")],
        ]
        
        # Run 20 times
        outputs = []
        for _ in range(20):
            # Create fresh runner for each iteration
            runner = make_deterministic_runner(deltas_sequence)
            
            clock = make_fake_clock(1000000)
            context = EngineContext(
                request_signature="test-sig",
                now_ms=clock,
                budget_units_remaining=500,
                breaker_tripped=False,
                abuse_blocked=False,
            )
            
            engine_input = EngineInput(
                request_signature="test-sig",
                initial_state=copy.deepcopy(initial_state),
                plan=plan,
                context=context,
                pass_runner=runner,
            )
            
            output = run_engine(engine_input)
            outputs.append(output)
        
        # Assert all outputs identical
        first = outputs[0]
        for i, output in enumerate(outputs[1:], 1):
            assert output.final_state == first.final_state, f"Run {i}: final_state differs"
            assert output.meta.stop_reason == first.meta.stop_reason, f"Run {i}: stop_reason differs"
            assert output.meta.validator_failures == first.meta.validator_failures, f"Run {i}: validator_failures differs"
            assert output.meta.downgraded == first.meta.downgraded, f"Run {i}: downgraded differs"
            assert output.meta.decision_signature == first.meta.decision_signature, f"Run {i}: decision_signature differs"
            
            # Telemetry event must be identical (JSON serialization)
            first_telem_json = json.dumps(first.meta.telemetry_event, sort_keys=True)
            output_telem_json = json.dumps(output.meta.telemetry_event, sort_keys=True)
            assert output_telem_json == first_telem_json, f"Run {i}: telemetry_event differs"


class TestTwoStrikesDowngradeGate:
    """
    Gate B: Two-Strikes Downgrade Gate (Exactness)
    
    Proves that validator downgrade triggers EXACTLY on second validation failure.
    """
    
    def test_first_invalid_delta_no_downgrade(self):
        """First invalid delta -> validator_failures=1, downgraded=False, continues."""
        initial_state = {
            "decision": {
                "action": "ANSWER",
                "answer": "Initial",
                "rationale": "Initial",
            }
        }
        
        plan = Plan(
            effective_pass_count=3,
            pass_plan=["PASS1", "PASS2", "PASS3"],
            per_pass_budget=[100, 100, 100],
            per_pass_timeout_ms=[500, 500, 500],
            stop_reason=None,
        )
        
        # First delta invalid (forbidden path), second and third valid
        deltas_sequence = [
            [PatchOp(op="set", path="decision.forbidden_field", value="hack")],  # Invalid
            [PatchOp(op="set", path="decision.rationale", value="Valid update")],  # Valid
            [PatchOp(op="set", path="decision.action", value="ASK_CLARIFY")],  # Valid
        ]
        
        runner = make_deterministic_runner(deltas_sequence)
        clock = make_fake_clock(1000000)
        context = EngineContext(
            request_signature="test-sig",
            now_ms=clock,
            budget_units_remaining=500,
        )
        
        engine_input = EngineInput(
            request_signature="test-sig",
            initial_state=initial_state,
            plan=plan,
            context=context,
            pass_runner=runner,
        )
        
        output = run_engine(engine_input)
        
        # After first invalid delta: should have 1 strike but continue
        # Engine should execute all 3 passes (first fails validation, second and third succeed)
        assert output.meta.validator_failures == 1, "Should have 1 validator failure"
        assert output.meta.downgraded == False, "Should not downgrade on first failure"
        assert output.meta.stop_reason == "SUCCESS_COMPLETED", "Should complete successfully"
    
    def test_second_invalid_delta_triggers_downgrade(self):
        """Second invalid delta -> validator_failures=2, downgraded=True, stop_reason=VALIDATION_FAIL."""
        initial_state = {
            "decision": {
                "action": "ANSWER",
                "answer": "Initial",
                "rationale": "Initial",
            }
        }
        
        plan = Plan(
            effective_pass_count=3,
            pass_plan=["PASS1", "PASS2", "PASS3"],
            per_pass_budget=[100, 100, 100],
            per_pass_timeout_ms=[500, 500, 500],
            stop_reason=None,
        )
        
        # First and second deltas invalid, third should not execute
        deltas_sequence = [
            [PatchOp(op="set", path="decision.forbidden1", value="hack1")],  # Invalid
            [PatchOp(op="set", path="decision.forbidden2", value="hack2")],  # Invalid
            [PatchOp(op="set", path="decision.action", value="ASK_CLARIFY")],  # Should not execute
        ]
        
        runner = make_deterministic_runner(deltas_sequence)
        clock = make_fake_clock(1000000)
        context = EngineContext(
            request_signature="test-sig",
            now_ms=clock,
            budget_units_remaining=500,
        )
        
        engine_input = EngineInput(
            request_signature="test-sig",
            initial_state=copy.deepcopy(initial_state),
            plan=plan,
            context=context,
            pass_runner=runner,
        )
        
        output = run_engine(engine_input)
        
        # After second invalid delta: should downgrade
        assert output.meta.validator_failures == 2, "Should have 2 validator failures"
        assert output.meta.downgraded == True, "Should downgrade on second failure"
        assert output.meta.stop_reason == "VALIDATION_FAIL", "Stop reason should be VALIDATION_FAIL"
        
        # Final state should be initial state (baseline)
        assert output.final_state == initial_state, "Should return baseline state on downgrade"
        
        # Should only execute 2 passes (third should not execute)
        assert output.meta.pass_count_executed == 2, "Should stop after second failure"


class TestStopReasonContractGate:
    """
    Gate C: StopReason Contract Gate
    
    Proves that all StopReasons used in code are members of contract exhaustive set.
    """
    
    def test_contract_stop_reasons_exhaustive(self):
        """All StopReasons in contract are present in router enum."""
        # Contract StopReason codes from docs/PHASE17_DEEP_THINKING_CONTRACT.md §5.1
        contract_stop_reasons = {
            "SUCCESS_COMPLETED",
            "BUDGET_EXHAUSTED",
            "PASS_LIMIT_REACHED",
            "TIMEOUT",
            "BREAKER_TRIPPED",
            "ENTITLEMENT_CAP",
            "ABUSE",
            "VALIDATION_FAIL",
            "INTERNAL_INCONSISTENCY",
        }
        
        # Get StopReason enum values from router
        router_stop_reasons = {sr.value for sr in StopReason}
        
        # Assert contract codes are in router
        for code in contract_stop_reasons:
            assert code in router_stop_reasons, f"Contract code '{code}' not in router enum"
        
        # Assert no extra codes in router (no "OTHER")
        for code in router_stop_reasons:
            assert code in contract_stop_reasons, f"Router code '{code}' not in contract"
    
    def test_no_other_stop_reason_used(self):
        """Ensure no "OTHER" or unmapped StopReason is used."""
        router_stop_reasons = {sr.value for sr in StopReason}
        
        # Explicitly check for forbidden codes
        forbidden_codes = {"OTHER", "UNKNOWN", "UNMAPPED"}
        for code in forbidden_codes:
            assert code not in router_stop_reasons, f"Forbidden code '{code}' found in router"


class TestTelemetrySafetyGate:
    """
    Gate D: Telemetry & Summary Safety Gate (No Text Leakage)
    
    Proves that telemetry and logging never contain raw user text or assistant text.
    """
    
    def test_sentinel_strings_not_in_signature(self):
        """Sentinel strings in deltas must not appear in decision signature."""
        # Create deltas with sentinel strings
        deltas = [
            PatchOp(op="set", path="decision.answer", value=USER_SENTINEL),
            PatchOp(op="set", path="decision.rationale", value=ASSIST_SENTINEL),
        ]
        
        stable_inputs = {"budget_units_remaining": 200}
        pass_plan = ["COUNTERARG", "STRESS_TEST"]
        
        sig = compute_decision_signature(stable_inputs, pass_plan, deltas, None)
        
        # Signature should not contain sentinel strings
        assert USER_SENTINEL not in sig, "User sentinel leaked into signature"
        assert ASSIST_SENTINEL not in sig, "Assistant sentinel leaked into signature"
    
    def test_sentinel_strings_not_in_telemetry_event(self):
        """Sentinel strings must not appear in telemetry event JSON."""
        # Create deltas with sentinel strings
        deltas = [
            PatchOp(op="set", path="decision.answer", value=USER_SENTINEL),
            PatchOp(op="set", path="decision.clarify_question", value=ASSIST_SENTINEL),
        ]
        
        stable_inputs = {"budget_units_remaining": 200}
        pass_plan = ["COUNTERARG"]
        
        sig = compute_decision_signature(stable_inputs, pass_plan, deltas, None)
        
        event = build_telemetry_event(
            pass_count=1,
            stop_reason="SUCCESS_COMPLETED",
            validator_failures=0,
            downgraded=False,
            decision_signature=sig,
        )
        
        # Serialize event
        event_json = json.dumps(event)
        
        # Sentinels should not appear
        assert USER_SENTINEL not in event_json, "User sentinel leaked into telemetry event"
        assert ASSIST_SENTINEL not in event_json, "Assistant sentinel leaked into telemetry event"
    
    def test_forbidden_keys_removed_from_summary(self):
        """Forbidden text keys must be removed from sanitized summaries."""
        unsafe_summary = {
            "pass_count": 2,
            "stop_reason": "SUCCESS_COMPLETED",
            "user_text": USER_SENTINEL,
            "answer": ASSIST_SENTINEL,
            "rendered_text": "Some output",
            "prompt": "User prompt",
            "message": "User message",
            "decision_signature": "abc123",
        }
        
        safe_summary = sanitize_summary_for_logging(unsafe_summary)
        
        # Safe fields should be present
        assert "pass_count" in safe_summary
        assert "stop_reason" in safe_summary
        assert "decision_signature" in safe_summary
        
        # Forbidden fields should be removed
        forbidden_keys = ["user_text", "answer", "rendered_text", "prompt", "message"]
        for key in forbidden_keys:
            assert key not in safe_summary, f"Forbidden key '{key}' not removed"
        
        # Serialize and verify no sentinels
        safe_json = json.dumps(safe_summary)
        assert USER_SENTINEL not in safe_json, "User sentinel in sanitized summary"
        assert ASSIST_SENTINEL not in safe_json, "Assistant sentinel in sanitized summary"
    
    def test_engine_output_telemetry_no_text_leakage(self):
        """End-to-end: Engine output telemetry must not leak text."""
        initial_state = {
            "decision": {
                "action": "ANSWER",
                "answer": USER_SENTINEL,
                "rationale": ASSIST_SENTINEL,
            }
        }
        
        plan = Plan(
            effective_pass_count=1,
            pass_plan=["PASS1"],
            per_pass_budget=[100],
            per_pass_timeout_ms=[500],
            stop_reason=None,
        )
        
        # Delta with sentinel
        deltas_sequence = [
            [PatchOp(op="set", path="decision.clarify_question", value=USER_SENTINEL)],
        ]
        
        runner = make_deterministic_runner(deltas_sequence)
        clock = make_fake_clock(1000000)
        context = EngineContext(
            request_signature="test-sig",
            now_ms=clock,
            budget_units_remaining=500,
        )
        
        engine_input = EngineInput(
            request_signature="test-sig",
            initial_state=initial_state,
            plan=plan,
            context=context,
            pass_runner=runner,
        )
        
        output = run_engine(engine_input)
        
        # Check telemetry event
        telem_json = json.dumps(output.meta.telemetry_event)
        assert USER_SENTINEL not in telem_json, "User sentinel in engine telemetry"
        assert ASSIST_SENTINEL not in telem_json, "Assistant sentinel in engine telemetry"
        
        # Check decision signature
        assert USER_SENTINEL not in output.meta.decision_signature
        assert ASSIST_SENTINEL not in output.meta.decision_signature


# Self-check runner for local verification
if __name__ == "__main__":
    print("Running Phase 17 Evaluation Gates...")
    print()
    
    # Gate A: Deterministic Replay
    print("Gate A: Deterministic Replay Gate")
    test_a = TestDeterministicReplayGate()
    test_a.test_replay_20_times_identical_outputs()
    print("✓ Replay 20 times -> identical outputs")
    
    # Gate B: Two-Strikes Downgrade
    print("\nGate B: Two-Strikes Downgrade Gate")
    test_b = TestTwoStrikesDowngradeGate()
    test_b.test_first_invalid_delta_no_downgrade()
    print("✓ First invalid delta -> no downgrade")
    test_b.test_second_invalid_delta_triggers_downgrade()
    print("✓ Second invalid delta -> downgrade exactly")
    
    # Gate C: StopReason Contract
    print("\nGate C: StopReason Contract Gate")
    test_c = TestStopReasonContractGate()
    test_c.test_contract_stop_reasons_exhaustive()
    print("✓ Contract StopReasons exhaustive")
    test_c.test_no_other_stop_reason_used()
    print("✓ No 'OTHER' StopReason used")
    
    # Gate D: Telemetry Safety
    print("\nGate D: Telemetry & Summary Safety Gate")
    test_d = TestTelemetrySafetyGate()
    test_d.test_sentinel_strings_not_in_signature()
    print("✓ Sentinels not in signature")
    test_d.test_sentinel_strings_not_in_telemetry_event()
    print("✓ Sentinels not in telemetry event")
    test_d.test_forbidden_keys_removed_from_summary()
    print("✓ Forbidden keys removed from summary")
    test_d.test_engine_output_telemetry_no_text_leakage()
    print("✓ Engine output telemetry has no text leakage")
    
    print("\n" + "="*60)
    print("ALL EVALUATION GATES PASSED ✓")
    print("="*60)
