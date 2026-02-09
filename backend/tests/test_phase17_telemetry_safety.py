"""
Phase 17 Step 8: Telemetry Safety Tests

Tests for safe telemetry with NO user text leakage. Ensures decision signature
is deterministic and based only on structural metadata.
"""

import json
from backend.app.deepthink.telemetry import (
    compute_decision_signature,
    build_telemetry_event,
    sanitize_summary_for_logging,
    FORBIDDEN_TEXT_KEYS,
)
from backend.app.deepthink.schema import PatchOp
from backend.app.deepthink.engine import EngineContext, PassSummary


def make_fake_clock(initial_ms=0):
    """Create a fake clock for testing."""
    time_ms = [initial_ms]
    
    def now_ms():
        return time_ms[0]
    
    return now_ms


# Sentinel strings to detect leakage
SENSITIVE_USER_TEXT = "SENSITIVE_USER_TEXT_123"
SENSITIVE_ASSISTANT_TEXT = "SENSITIVE_ASSISTANT_TEXT_456"


class TestDecisionSignatureDeterminism:
    """Test that decision signature is deterministic."""
    
    def test_identical_inputs_produce_identical_signature_30_times(self):
        """Same inputs -> same signature (30 iterations)."""
        stable_inputs = {
            "env_mode": "prod",
            "entitlement_tier": "PRO",
            "budget_units_remaining": 200,
            "breaker_tripped": False,
        }
        pass_plan = ["REFINE", "COUNTERARG", "STRESS_TEST"]
        deltas = [
            PatchOp(op="set", path="decision.action", value="ANSWER"),
            PatchOp(op="set", path="decision.answer", value="Some answer text"),
        ]
        meta = {"validator_failures": 0, "stop_reason": "SUCCESS_COMPLETED"}
        
        signatures = []
        for _ in range(30):
            sig = compute_decision_signature(stable_inputs, pass_plan, deltas, meta)
            signatures.append(sig)
        
        # All signatures should be identical
        first = signatures[0]
        for sig in signatures[1:]:
            assert sig == first, "Signature not deterministic"
    
    def test_signature_changes_when_plan_changes(self):
        """Signature changes when pass plan changes."""
        stable_inputs = {"budget_units_remaining": 200}
        pass_plan_1 = ["REFINE", "COUNTERARG"]
        pass_plan_2 = ["REFINE", "STRESS_TEST"]
        deltas = [PatchOp(op="set", path="decision.action", value="ANSWER")]
        
        sig1 = compute_decision_signature(stable_inputs, pass_plan_1, deltas, None)
        sig2 = compute_decision_signature(stable_inputs, pass_plan_2, deltas, None)
        
        assert sig1 != sig2, "Signature should change when plan changes"
    
    def test_signature_changes_when_delta_structure_changes(self):
        """Signature changes when delta structure (path/op/length) changes."""
        stable_inputs = {"budget_units_remaining": 200}
        pass_plan = ["REFINE"]
        
        # Different paths
        deltas1 = [PatchOp(op="set", path="decision.action", value="ANSWER")]
        deltas2 = [PatchOp(op="set", path="decision.rationale", value="text")]
        
        sig1 = compute_decision_signature(stable_inputs, pass_plan, deltas1, None)
        sig2 = compute_decision_signature(stable_inputs, pass_plan, deltas2, None)
        
        assert sig1 != sig2, "Signature should change when delta path changes"
    
    def test_signature_changes_when_text_length_changes(self):
        """Signature changes when text length changes (structure change)."""
        stable_inputs = {"budget_units_remaining": 200}
        pass_plan = ["REFINE"]
        
        # Same path, different lengths
        deltas1 = [PatchOp(op="set", path="decision.answer", value="short")]
        deltas2 = [PatchOp(op="set", path="decision.answer", value="much longer answer text")]
        
        sig1 = compute_decision_signature(stable_inputs, pass_plan, deltas1, None)
        sig2 = compute_decision_signature(stable_inputs, pass_plan, deltas2, None)
        
        assert sig1 != sig2, "Signature should change when text length changes"
    
    def test_signature_same_when_only_content_changes_same_length(self):
        """Signature stays same when only content changes but same length."""
        stable_inputs = {"budget_units_remaining": 200}
        pass_plan = ["REFINE"]
        
        # Same path, same length, different content
        deltas1 = [PatchOp(op="set", path="decision.answer", value="aaaaa")]
        deltas2 = [PatchOp(op="set", path="decision.answer", value="bbbbb")]
        
        sig1 = compute_decision_signature(stable_inputs, pass_plan, deltas1, None)
        sig2 = compute_decision_signature(stable_inputs, pass_plan, deltas2, None)
        
        # Should be same because we only encode length, not content
        assert sig1 == sig2, "Signature should be same for same length different content"


class TestTelemetryEventFields:
    """Test that telemetry event contains required fields."""
    
    def test_telemetry_event_has_required_fields(self):
        """Telemetry event must have all required fields."""
        event = build_telemetry_event(
            pass_count=3,
            stop_reason="SUCCESS_COMPLETED",
            validator_failures=0,
            downgraded=False,
            decision_signature="abc123",
        )
        
        # Check required fields
        assert "pass_count" in event
        assert "stop_reason" in event
        assert "validator_failures" in event
        assert "downgraded" in event
        assert "decision_signature" in event
        
        # Verify values
        assert event["pass_count"] == 3
        assert event["stop_reason"] == "SUCCESS_COMPLETED"
        assert event["validator_failures"] == 0
        assert event["downgraded"] is False
        assert event["decision_signature"] == "abc123"
    
    def test_telemetry_event_is_json_serializable(self):
        """Telemetry event must be JSON-serializable."""
        event = build_telemetry_event(
            pass_count=2,
            stop_reason="VALIDATION_FAIL",
            validator_failures=2,
            downgraded=True,
            decision_signature="def456",
            final_action="ANSWER",
        )
        
        # Should not raise exception
        json_str = json.dumps(event)
        assert len(json_str) > 0
        
        # Should round-trip
        parsed = json.loads(json_str)
        assert parsed["pass_count"] == 2
        assert parsed["stop_reason"] == "VALIDATION_FAIL"


class TestNoUserTextLeakage:
    """Test that telemetry never contains user text."""
    
    def test_telemetry_event_does_not_contain_user_text_sentinel(self):
        """Telemetry event must not contain user text sentinel."""
        # Create deltas with sentinel strings
        deltas = [
            PatchOp(op="set", path="decision.answer", value=SENSITIVE_USER_TEXT),
            PatchOp(op="set", path="decision.rationale", value=SENSITIVE_ASSISTANT_TEXT),
        ]
        
        stable_inputs = {"budget_units_remaining": 200}
        pass_plan = ["REFINE"]
        
        sig = compute_decision_signature(stable_inputs, pass_plan, deltas, None)
        
        # Signature should not contain sentinel strings
        assert SENSITIVE_USER_TEXT not in sig
        assert SENSITIVE_ASSISTANT_TEXT not in sig
        
        # Build telemetry event
        event = build_telemetry_event(
            pass_count=1,
            stop_reason="SUCCESS_COMPLETED",
            validator_failures=0,
            downgraded=False,
            decision_signature=sig,
        )
        
        # Serialize event
        event_json = json.dumps(event)
        
        # Event should not contain sentinel strings
        assert SENSITIVE_USER_TEXT not in event_json
        assert SENSITIVE_ASSISTANT_TEXT not in event_json
    
    def test_pass_summaries_sanitized_no_text_leakage(self):
        """Pass summaries in telemetry must not leak text."""
        # Create pass summary with error containing sensitive text
        pass_summary = PassSummary(
            pass_type="REFINE",
            executed=True,
            validation_ok=False,
            patch_applied=False,
            cost_units=50,
            duration_ms=200,
            strikes_added=1,
            error=f"Error: {SENSITIVE_USER_TEXT}",
        )
        
        event = build_telemetry_event(
            pass_count=1,
            stop_reason="VALIDATION_FAIL",
            validator_failures=1,
            downgraded=False,
            decision_signature="sig123",
            pass_summaries=[pass_summary],
        )
        
        # Serialize event
        event_json = json.dumps(event)
        
        # Event should not contain sentinel (error field should be excluded)
        assert SENSITIVE_USER_TEXT not in event_json


class TestSummarySanitization:
    """Test that summary sanitization removes user text."""
    
    def test_sanitize_summary_removes_forbidden_keys(self):
        """Sanitize summary must remove forbidden text keys."""
        unsafe_summary = {
            "pass_count": 2,
            "stop_reason": "SUCCESS_COMPLETED",
            "user_text": SENSITIVE_USER_TEXT,
            "answer": SENSITIVE_ASSISTANT_TEXT,
            "rendered_text": "Some output",
            "decision_signature": "abc123",
        }
        
        safe_summary = sanitize_summary_for_logging(unsafe_summary)
        
        # Safe fields should be present
        assert "pass_count" in safe_summary
        assert "stop_reason" in safe_summary
        assert "decision_signature" in safe_summary
        
        # Forbidden fields should be removed
        assert "user_text" not in safe_summary
        assert "answer" not in safe_summary
        assert "rendered_text" not in safe_summary
        
        # Serialize and check
        safe_json = json.dumps(safe_summary)
        assert SENSITIVE_USER_TEXT not in safe_json
        assert SENSITIVE_ASSISTANT_TEXT not in safe_json
    
    def test_sanitize_summary_preserves_safe_primitives(self):
        """Sanitize summary preserves safe primitives."""
        summary = {
            "pass_count": 3,
            "validator_failures": 1,
            "downgraded": False,
            "stop_reason": "VALIDATION_FAIL",
        }
        
        safe_summary = sanitize_summary_for_logging(summary)
        
        assert safe_summary["pass_count"] == 3
        assert safe_summary["validator_failures"] == 1
        assert safe_summary["downgraded"] is False
        assert safe_summary["stop_reason"] == "VALIDATION_FAIL"


class TestForbiddenKeysConstant:
    """Test that forbidden keys constant is comprehensive."""
    
    def test_forbidden_keys_includes_common_text_fields(self):
        """Forbidden keys must include common text field names."""
        expected_keys = {
            "user_text",
            "answer",
            "rationale",
            "clarify_question",
            "rendered_text",
            "prompt",
            "message",
        }
        
        for key in expected_keys:
            assert key in FORBIDDEN_TEXT_KEYS, f"Missing forbidden key: {key}"


# Self-check runner for local verification
if __name__ == "__main__":
    print("Running Phase 17 Telemetry Safety self-checks...")
    
    # Test 1: Determinism
    stable_inputs = {"budget_units_remaining": 200}
    pass_plan = ["REFINE", "COUNTERARG"]
    deltas = [PatchOp(op="set", path="decision.action", value="ANSWER")]
    
    signatures = []
    for _ in range(10):
        sig = compute_decision_signature(stable_inputs, pass_plan, deltas, None)
        signatures.append(sig)
    
    first = signatures[0]
    for sig in signatures[1:]:
        assert sig == first, "Determinism failed"
    print("✓ Determinism (10 runs)")
    
    # Test 2: Signature changes with plan
    pass_plan_2 = ["REFINE", "STRESS_TEST"]
    sig2 = compute_decision_signature(stable_inputs, pass_plan_2, deltas, None)
    assert first != sig2, "Signature should change with plan"
    print("✓ Signature changes when plan changes")
    
    # Test 3: No user text leakage
    deltas_with_text = [
        PatchOp(op="set", path="decision.answer", value=SENSITIVE_USER_TEXT),
    ]
    sig = compute_decision_signature(stable_inputs, pass_plan, deltas_with_text, None)
    assert SENSITIVE_USER_TEXT not in sig
    print("✓ No user text in signature")
    
    # Test 4: Telemetry event has required fields
    event = build_telemetry_event(
        pass_count=2,
        stop_reason="SUCCESS_COMPLETED",
        validator_failures=0,
        downgraded=False,
        decision_signature="abc123",
    )
    assert "pass_count" in event
    assert "stop_reason" in event
    assert "decision_signature" in event
    print("✓ Telemetry event has required fields")
    
    # Test 5: Event is JSON-serializable
    event_json = json.dumps(event)
    assert len(event_json) > 0
    print("✓ Telemetry event is JSON-serializable")
    
    # Test 6: No text leakage in serialized event
    assert SENSITIVE_USER_TEXT not in event_json
    print("✓ No user text in serialized event")
    
    # Test 7: Summary sanitization
    unsafe_summary = {
        "pass_count": 2,
        "user_text": SENSITIVE_USER_TEXT,
        "answer": SENSITIVE_ASSISTANT_TEXT,
    }
    safe_summary = sanitize_summary_for_logging(unsafe_summary)
    assert "user_text" not in safe_summary
    assert "answer" not in safe_summary
    assert "pass_count" in safe_summary
    print("✓ Summary sanitization removes forbidden keys")
    
    # Test 8: Same length different content -> same signature
    deltas1 = [PatchOp(op="set", path="decision.answer", value="aaaaa")]
    deltas2 = [PatchOp(op="set", path="decision.answer", value="bbbbb")]
    sig1 = compute_decision_signature(stable_inputs, pass_plan, deltas1, None)
    sig2 = compute_decision_signature(stable_inputs, pass_plan, deltas2, None)
    assert sig1 == sig2, "Same length should produce same signature"
    print("✓ Same length different content -> same signature")
    
    print("\nAll self-checks PASSED ✓")
