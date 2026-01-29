"""
Phase 18 Step 7: Research Telemetry Safety Tests

Self-check runner for telemetry safety:
- No user text leakage
- Structure-only signature
- Determinism across replays
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.research.telemetry import (
    build_research_telemetry_event,
    compute_research_signature,
    sanitize_event,
    assert_no_text_leakage,
    FORBIDDEN_KEYS,
)


SENSITIVE_INJECT_123 = "SENSITIVE_INJECT_123"
SENSITIVE_INJECT_456 = "SENSITIVE_INJECT_456"


def make_base_inputs():
    return {
        "env_mode": "DEV",
        "tool_calls_count": 3,
        "domains_used": ["Example.com", "www.Test.com", ""],
        "grade_histogram": {"A": 2, "B": 1},
        "citation_coverage": {
            "claims_total": 5,
            "claims_required": 4,
            "claims_required_covered": 3,
        },
        "stop_reason": "SUCCESS_COMPLETED",
        "validator_failures": 0,
        "downgrade_reason": None,
        "sandbox_caps": {
            "max_calls_total": 10,
            "max_calls_per_minute": 5,
            "per_call_timeout_ms": 5000,
            "total_timeout_ms": 20000,
        },
        "versions": {
            "credibility": "18.3.0",
            "injection": "18.5.0",
            "claim_binder": "18.4.0",
            "cache": "18.6.0",
        },
        "counters": {
            "cache_hits": 2,
            "cache_misses": 1,
            "dedup_dropped": 1,
            "injections_flagged": 0,
        },
    }


def collect_keys(event, keys):
    if isinstance(event, dict):
        for key, value in event.items():
            keys.add(key)
            collect_keys(value, keys)
    elif isinstance(event, list):
        for item in event:
            collect_keys(item, keys)


class TestNoUserTextLeakage:
    """Test that sentinels never leak to telemetry."""
    
    def test_no_user_text_leakage_with_sentinels(self):
        """Sentinels under forbidden keys are removed and never appear in telemetry."""
        base = make_base_inputs()
        
        unsafe_structure = {
            "tool_calls_count": base["tool_calls_count"],
            "domains_used": base["domains_used"],
            "grade_histogram": base["grade_histogram"],
            "citation_coverage": base["citation_coverage"],
            "stop_reason": base["stop_reason"],
            "validator_failures": base["validator_failures"],
            "downgrade_reason": base["downgrade_reason"],
            "snippet": SENSITIVE_INJECT_123,
            "nested": {
                "content": SENSITIVE_INJECT_456,
                "answer": SENSITIVE_INJECT_123,
                "claims": [SENSITIVE_INJECT_456],
            },
        }
        
        sanitized_pack = sanitize_event(unsafe_structure)
        signature = compute_research_signature(sanitized_pack)
        
        event = build_research_telemetry_event(**base)
        
        serialized_event = json.dumps(event, sort_keys=True)
        serialized_pack = json.dumps(sanitized_pack, sort_keys=True)
        
        assert SENSITIVE_INJECT_123 not in serialized_event
        assert SENSITIVE_INJECT_456 not in serialized_event
        assert SENSITIVE_INJECT_123 not in serialized_pack
        assert SENSITIVE_INJECT_456 not in serialized_pack
        assert SENSITIVE_INJECT_123 not in signature
        assert SENSITIVE_INJECT_456 not in signature
        
        assert_no_text_leakage(event, [SENSITIVE_INJECT_123, SENSITIVE_INJECT_456])


class TestStructureOnlySignature:
    """Test signature is structure-only."""
    
    def test_signature_structure_only_same_length_different_content(self):
        """Different forbidden text should not change signature."""
        base = make_base_inputs()
        
        pack1 = {
            "tool_calls_count": base["tool_calls_count"],
            "domains_used": base["domains_used"],
            "grade_histogram": base["grade_histogram"],
            "citation_coverage": base["citation_coverage"],
            "stop_reason": base["stop_reason"],
            "validator_failures": base["validator_failures"],
            "downgrade_reason": base["downgrade_reason"],
            "snippet": "TEXT_A",
        }
        pack2 = {
            "tool_calls_count": base["tool_calls_count"],
            "domains_used": base["domains_used"],
            "grade_histogram": base["grade_histogram"],
            "citation_coverage": base["citation_coverage"],
            "stop_reason": base["stop_reason"],
            "validator_failures": base["validator_failures"],
            "downgrade_reason": base["downgrade_reason"],
            "snippet": "TEXT_B",
        }
        
        sig1 = compute_research_signature(sanitize_event(pack1))
        sig2 = compute_research_signature(sanitize_event(pack2))
        
        assert sig1 == sig2
    
    def test_signature_changes_on_structure_change(self):
        """Signature changes with structural changes."""
        base = make_base_inputs()
        
        event1 = build_research_telemetry_event(**base)
        
        base_modified = make_base_inputs()
        base_modified["tool_calls_count"] = 4
        event2 = build_research_telemetry_event(**base_modified)
        
        assert event1["research_signature"] != event2["research_signature"]
        
        base_modified = make_base_inputs()
        base_modified["grade_histogram"] = {"A": 1, "B": 2}
        event3 = build_research_telemetry_event(**base_modified)
        assert event1["research_signature"] != event3["research_signature"]
        
        base_modified = make_base_inputs()
        base_modified["citation_coverage"] = {
            "claims_total": 5,
            "claims_required": 4,
            "claims_required_covered": 2,
        }
        event4 = build_research_telemetry_event(**base_modified)
        assert event1["research_signature"] != event4["research_signature"]
        
        base_modified = make_base_inputs()
        base_modified["domains_used"] = ["example.com", "newdomain.com"]
        event5 = build_research_telemetry_event(**base_modified)
        assert event1["research_signature"] != event5["research_signature"]


class TestRequiredFields:
    """Test required fields presence."""
    
    def test_required_fields_present(self):
        """Event contains all required fields."""
        event = build_research_telemetry_event(**make_base_inputs())
        
        required_fields = [
            "research_signature",
            "tool_calls_count",
            "domains_used",
            "grade_histogram",
            "citation_coverage",
            "stop_reason",
            "validator_failures",
            "downgrade_reason",
        ]
        
        for field in required_fields:
            assert field in event
        
        for key in ["A", "B", "C", "D", "E", "UNKNOWN"]:
            assert key in event["grade_histogram"]


class TestJsonSerializable:
    """Test event is JSON serializable."""
    
    def test_json_serializable(self):
        """json.dumps works on event."""
        event = build_research_telemetry_event(**make_base_inputs())
        json.dumps(event)


class TestForbiddenKeysRemoved:
    """Test forbidden keys are removed recursively."""
    
    def test_forbidden_keys_removed(self):
        """Forbidden keys removed at any depth."""
        event = {
            "safe": {
                "nested": {
                    "snippet": "bad",
                    "content": "bad",
                }
            },
            "claims": ["bad"],
            "title": "bad",
        }
        
        sanitized = sanitize_event(event)
        
        keys = set()
        collect_keys(sanitized, keys)
        
        for forbidden in FORBIDDEN_KEYS:
            assert forbidden not in keys


class TestDeterminism:
    """Test deterministic outputs."""
    
    def test_determinism_replay_20(self):
        """Same inputs -> identical event + signature across 20 runs."""
        base = make_base_inputs()
        events = []
        
        for _ in range(20):
            event = build_research_telemetry_event(**base)
            events.append(event)
        
        for i in range(1, 20):
            assert events[i] == events[0]


if __name__ == "__main__":
    print("Running Phase 18 Step 7 Telemetry Safety Tests...")
    print()
    
    print("Test Group: No User Text Leakage")
    test_no_text = TestNoUserTextLeakage()
    test_no_text.test_no_user_text_leakage_with_sentinels()
    print("✓ No user text leakage with sentinels")
    
    print("\nTest Group: Structure-Only Signature")
    test_signature = TestStructureOnlySignature()
    test_signature.test_signature_structure_only_same_length_different_content()
    print("✓ Signature structure-only (same structure, different text)")
    test_signature.test_signature_changes_on_structure_change()
    print("✓ Signature changes on structure change")
    
    print("\nTest Group: Required Fields")
    test_fields = TestRequiredFields()
    test_fields.test_required_fields_present()
    print("✓ Required fields present")
    
    print("\nTest Group: JSON Serializable")
    test_json = TestJsonSerializable()
    test_json.test_json_serializable()
    print("✓ JSON serializable")
    
    print("\nTest Group: Forbidden Keys Removed")
    test_forbidden = TestForbiddenKeysRemoved()
    test_forbidden.test_forbidden_keys_removed()
    print("✓ Forbidden keys removed recursively")
    
    print("\nTest Group: Determinism")
    test_det = TestDeterminism()
    test_det.test_determinism_replay_20()
    print("✓ Determinism replay 20 times")
    
    print("\n" + "="*60)
    print("ALL TELEMETRY SAFETY TESTS PASSED ✓")
    print("="*60)
