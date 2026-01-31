"""
Phase 19 Step 7: Memory Telemetry Safety Tests

Self-check runner for memory telemetry system proving no text leakage,
deterministic behavior, bounded operation, and fail-closed safety.
"""

import json
import os
import sys
from dataclasses import asdict
from typing import Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.memory.telemetry import (
    MemoryTelemetryEvent,
    MemoryTelemetryInput,
    build_memory_telemetry_event,
    compute_memory_signature,
    sanitize_structure,
    canonical_json,
    assert_no_text_leakage,
    MEMORY_TELEMETRY_VERSION,
    FORBIDDEN_KEY_SUBSTRINGS,
    bucket_size,
    bucket_chars,
    sanitize_reason_code,
    sanitize_ttl_class,
)


# ============================================================================
# TEST SENTINELS
# ============================================================================

SENSITIVE_SENTINELS = [
    "SENSITIVE_USER_TEXT_123",
    "SENSITIVE_MEMORY_VALUE_456",
    "user said: i have diabetes",
    "> quoted text",
    "my secret password",
    "personal information",
    "confidential data",
]


# ============================================================================
# HELPERS
# ============================================================================

def create_clean_input() -> MemoryTelemetryInput:
    """Create a clean telemetry input for testing."""
    return MemoryTelemetryInput(
        writes_attempted=10,
        writes_accepted=8,
        writes_rejected=2,
        rejection_reason_codes=["FORBIDDEN_CATEGORY", "VALIDATION_FAIL"],
        ttl_classes=["TTL_1H", "TTL_1D"],
        reads_attempted=5,
        bundle_sizes=[3, 7, 12, 0],
        bundle_chars=[250, 600, 900, 1500],
        caps_snapshot={"max_facts": 100, "max_total_chars": 10000},
    )


def create_malicious_input() -> Dict:
    """Create input with forbidden content for testing sanitization."""
    return {
        "writes_attempted": 5,
        "writes_accepted": 3,
        "writes_rejected": 2,
        "rejection_reason_codes": ["FORBIDDEN_CATEGORY", "SENSITIVE_USER_TEXT_123"],
        "ttl_classes": ["TTL_1H", "SENSITIVE_MEMORY_VALUE_456"],
        "reads_attempted": 2,
        "bundle_sizes": [1, 2, 3],
        "bundle_chars": [100, 200, 300],
        "caps_snapshot": {
            "max_facts": 50,
            "value_str": "SENSITIVE_USER_TEXT_123",
            "user": "john_doe",
            "prompt": "user said: i have diabetes",
            "nested": {
                "key": "secret_value",
                "content": "> quoted text",
                "safe_field": 42,
            }
        },
        "forbidden_field": "SENSITIVE_MEMORY_VALUE_456",
        "text": "personal information",
    }


# ============================================================================
# TEST 1: No Sentinel Leakage
# ============================================================================

class Test1_NoSentinelLeakage:
    """Test that sensitive sentinels never leak into telemetry output."""
    
    def test_malicious_reason_codes_sanitized(self):
        """Malicious reason codes should be sanitized."""
        input_data = MemoryTelemetryInput(
            rejection_reason_codes=["FORBIDDEN_CATEGORY", "SENSITIVE_USER_TEXT_123", "user said: diabetes"]
        )
        
        event = build_memory_telemetry_event(input_data)
        
        # Check that sentinels are not in the event
        assert_no_text_leakage(event, SENSITIVE_SENTINELS)
        
        # Check that invalid reason codes are sanitized
        assert "SENSITIVE_USER_TEXT_123" not in event.rejection_reason_hist
        assert "user said: diabetes" not in event.rejection_reason_hist
        
        # Check that valid codes remain and invalid ones are either dropped or converted to INVALID_REASON
        assert "FORBIDDEN_CATEGORY" in event.rejection_reason_hist
        
        # The forbidden items should be dropped entirely during sanitization, not converted to INVALID_REASON
        # So we don't expect INVALID_REASON to appear unless there were other invalid codes
    
    def test_malicious_ttl_classes_sanitized(self):
        """Malicious TTL classes should be sanitized to UNKNOWN."""
        input_data = MemoryTelemetryInput(
            ttl_classes=["TTL_1H", "SENSITIVE_MEMORY_VALUE_456", "malicious_ttl"]
        )
        
        event = build_memory_telemetry_event(input_data)
        
        # Check that sentinels are not in the event
        assert_no_text_leakage(event, SENSITIVE_SENTINELS)
        
        # Check that invalid TTL classes are sanitized
        assert "SENSITIVE_MEMORY_VALUE_456" not in event.ttl_class_hist
        assert "malicious_ttl" not in event.ttl_class_hist
        assert "UNKNOWN" in event.ttl_class_hist
        assert event.ttl_class_hist["UNKNOWN"] == 2  # Two invalid classes
    
    def test_malicious_caps_snapshot_sanitized(self):
        """Malicious caps snapshot should have forbidden keys removed."""
        malicious_caps = {
            "max_facts": 100,
            "value_str": "SENSITIVE_USER_TEXT_123",
            "user": "john_doe", 
            "prompt": "user said: i have diabetes",
            "nested": {
                "key": "secret_value",
                "content": "> quoted text",
                "safe_count": 42,
            }
        }
        
        input_data = MemoryTelemetryInput(caps_snapshot=malicious_caps)
        event = build_memory_telemetry_event(input_data)
        
        # Check that sentinels are not in the event
        assert_no_text_leakage(event, SENSITIVE_SENTINELS)
        
        # Check that forbidden keys are removed
        caps_json = json.dumps(event.caps_snapshot)
        assert "value_str" not in caps_json, f"value_str found in caps: {caps_json}"
        assert "user" not in caps_json, f"user found in caps: {caps_json}"
        assert "prompt" not in caps_json, f"prompt found in caps: {caps_json}"
        assert "key" not in caps_json, f"key found in caps: {caps_json}"
        assert "content" not in caps_json, f"content found in caps: {caps_json}"
        
        # Check that safe fields remain
        assert event.caps_snapshot.get("max_facts") == 100, f"max_facts not preserved: {event.caps_snapshot}"
        
        # Check that forbidden keys were detected
        assert event.had_forbidden_keys == True, f"Expected had_forbidden_keys=True, got {event.had_forbidden_keys}"
        assert event.dropped_keys_count > 0, f"Expected dropped_keys_count>0, got {event.dropped_keys_count}"
    
    def test_direct_malicious_struct_sanitized(self):
        """Direct malicious structure should be sanitized."""
        malicious_struct = create_malicious_input()
        
        sanitized, had_forbidden, dropped_count = sanitize_structure(malicious_struct)
        
        # Check that sentinels are not in sanitized structure
        sanitized_json = canonical_json(sanitized)
        for sentinel in SENSITIVE_SENTINELS:
            assert sentinel not in sanitized_json, f"Sentinel '{sentinel}' found in sanitized JSON: {sanitized_json}"
        
        # Check that forbidden keys were detected and removed
        assert had_forbidden == True, f"Expected had_forbidden=True, got {had_forbidden}"
        assert dropped_count > 0, f"Expected dropped_count>0, got {dropped_count}"
        
        # Check that forbidden fields are not present
        assert "forbidden_field" not in sanitized, f"forbidden_field still present in {sanitized}"
        assert "text" not in sanitized, f"text still present in {sanitized}"
        if "caps_snapshot" in sanitized:
            caps = sanitized["caps_snapshot"]
            assert "value_str" not in caps, f"value_str still in caps: {caps}"
            assert "user" not in caps, f"user still in caps: {caps}"
            assert "prompt" not in caps, f"prompt still in caps: {caps}"
    
    def test_signature_no_sentinels(self):
        """Memory signature should not contain sentinels."""
        input_data = MemoryTelemetryInput(
            rejection_reason_codes=["SENSITIVE_USER_TEXT_123"],
            ttl_classes=["SENSITIVE_MEMORY_VALUE_456"],
            caps_snapshot={"prompt": "user said: i have diabetes"}
        )
        
        event = build_memory_telemetry_event(input_data)
        
        # Check that signature doesn't contain sentinels
        for sentinel in SENSITIVE_SENTINELS:
            assert sentinel not in event.memory_signature
        
        # Signature should be valid hex
        assert len(event.memory_signature) == 64
        assert all(c in "0123456789abcdef" for c in event.memory_signature)


# ============================================================================
# TEST 2: Structure-only Signature Invariance
# ============================================================================

class Test2_SignatureInvariance:
    """Test that signature only depends on structure, not text content."""
    
    def test_identical_structure_identical_signature(self):
        """Identical structure should produce identical signature."""
        input1 = create_clean_input()
        input2 = create_clean_input()
        
        event1 = build_memory_telemetry_event(input1)
        event2 = build_memory_telemetry_event(input2)
        
        assert event1.memory_signature == event2.memory_signature
    
    def test_text_injection_same_signature(self):
        """Text injection should be sanitized, leaving same signature."""
        clean_input = create_clean_input()
        
        # Create "dirty" input with same structure but injected text
        dirty_caps = clean_input.caps_snapshot.copy()
        dirty_caps["prompt"] = "SENSITIVE_USER_TEXT_123"
        dirty_caps["user"] = "john_doe"
        
        dirty_input = MemoryTelemetryInput(
            writes_attempted=clean_input.writes_attempted,
            writes_accepted=clean_input.writes_accepted,
            writes_rejected=clean_input.writes_rejected,
            rejection_reason_codes=clean_input.rejection_reason_codes,
            ttl_classes=clean_input.ttl_classes,
            reads_attempted=clean_input.reads_attempted,
            bundle_sizes=clean_input.bundle_sizes,
            bundle_chars=clean_input.bundle_chars,
            caps_snapshot=dirty_caps,
        )
        
        clean_event = build_memory_telemetry_event(clean_input)
        dirty_event = build_memory_telemetry_event(dirty_input)
        
        # Signatures should be the same after sanitization
        assert clean_event.memory_signature == dirty_event.memory_signature
        
        # But dirty event should show forbidden keys were detected
        assert dirty_event.had_forbidden_keys == True
        assert dirty_event.dropped_keys_count > 0


# ============================================================================
# TEST 3: Signature Changes on Structure Change
# ============================================================================

class Test3_SignatureChanges:
    """Test that signature changes when structure changes."""
    
    def test_writes_accepted_change_signature(self):
        """Changing writes_accepted should change signature."""
        input1 = create_clean_input()
        input2 = create_clean_input()
        input2.writes_accepted = input1.writes_accepted + 1
        
        event1 = build_memory_telemetry_event(input1)
        event2 = build_memory_telemetry_event(input2)
        
        assert event1.memory_signature != event2.memory_signature
    
    def test_bundle_sizes_change_signature(self):
        """Changing bundle sizes should change signature."""
        input1 = create_clean_input()
        input2 = create_clean_input()
        input2.bundle_sizes = [1, 2, 3]  # Different from input1
        
        event1 = build_memory_telemetry_event(input1)
        event2 = build_memory_telemetry_event(input2)
        
        assert event1.memory_signature != event2.memory_signature
    
    def test_caps_snapshot_change_signature(self):
        """Changing caps snapshot should change signature."""
        input1 = create_clean_input()
        input2 = create_clean_input()
        input2.caps_snapshot = {"max_facts": 200}  # Different from input1
        
        event1 = build_memory_telemetry_event(input1)
        event2 = build_memory_telemetry_event(input2)
        
        assert event1.memory_signature != event2.memory_signature


# ============================================================================
# TEST 4: Determinism Replay
# ============================================================================

class Test4_DeterminismReplay:
    """Test deterministic behavior across multiple runs."""
    
    def test_build_event_20_times_identical(self):
        """Building event 20 times should produce identical results."""
        input_data = create_clean_input()
        
        events = []
        for _ in range(20):
            event = build_memory_telemetry_event(input_data)
            events.append(canonical_json(asdict(event)))
        
        # All events should be identical
        first_event = events[0]
        for i, event in enumerate(events[1:], 1):
            assert event == first_event, f"Run {i}: event differs from first run"
    
    def test_signature_computation_deterministic(self):
        """Signature computation should be deterministic."""
        struct_pack = {
            "version": MEMORY_TELEMETRY_VERSION,
            "writes_attempted": 10,
            "rejection_reason_hist": {"FORBIDDEN_CATEGORY": 2, "VALIDATION_FAIL": 1},
            "bundle_size_hist": {"1-4": 2, "5-8": 1},
        }
        
        signatures = []
        for _ in range(20):
            sig = compute_memory_signature(struct_pack)
            signatures.append(sig)
        
        # All signatures should be identical
        first_sig = signatures[0]
        for i, sig in enumerate(signatures[1:], 1):
            assert sig == first_sig, f"Signature run {i}: differs from first run"


# ============================================================================
# TEST 5: Forbidden Keys Removed Recursively
# ============================================================================

class Test5_ForbiddenKeysRemoval:
    """Test recursive removal of forbidden keys."""
    
    def test_deeply_nested_forbidden_keys_removed(self):
        """Deeply nested forbidden keys should be removed."""
        nested_struct = {
            "safe_field": 42,
            "caps_snapshot": {
                "max_facts": 16,
                "value_str": "SENSITIVE_USER_TEXT_123",
                "nested_level2": {
                    "prompt": "user said: i have diabetes",
                    "safe_count": 10,
                    "nested_level3": {
                        "key": "secret_key",
                        "content": "> quoted text",
                        "tags": ["forbidden", "tag"],
                        "safe_flag": True,
                    }
                }
            },
            "forbidden_root": "should_be_removed",
        }
        
        sanitized, had_forbidden, dropped_count = sanitize_structure(nested_struct)
        
        # Check that forbidden keys were detected
        assert had_forbidden == True
        assert dropped_count > 0
        
        # Check that forbidden keys are removed at all levels
        sanitized_json = canonical_json(sanitized)
        
        forbidden_in_struct = [
            "value_str", "prompt", "key", "content", "tags", "forbidden_root"
        ]
        for forbidden_key in forbidden_in_struct:
            assert forbidden_key not in sanitized_json
        
        # Check that safe fields remain
        assert sanitized["safe_field"] == 42
        if "caps_snapshot" in sanitized:
            assert sanitized["caps_snapshot"].get("max_facts") == 16
    
    def test_forbidden_keys_in_lists(self):
        """Forbidden content in lists should be sanitized."""
        struct_with_lists = {
            "safe_list": [1, 2, 3],
            "mixed_list": [
                {"safe_item": 1},
                {"key": "forbidden_key", "safe_item": 2},
                {"prompt": "forbidden_prompt", "value": 3}
            ],
            "caps_snapshot": {
                "list_field": [
                    {"max_facts": 10},
                    {"user": "forbidden_user", "count": 5}
                ]
            }
        }
        
        sanitized, had_forbidden, dropped_count = sanitize_structure(struct_with_lists)
        
        # Check that forbidden keys were detected
        assert had_forbidden == True
        assert dropped_count > 0
        
        # Check that forbidden keys are removed from list items
        sanitized_json = canonical_json(sanitized)
        assert "key" not in sanitized_json
        assert "prompt" not in sanitized_json
        assert "user" not in sanitized_json


# ============================================================================
# TEST 6: Bounds Enforcement
# ============================================================================

class Test6_BoundsEnforcement:
    """Test that bounds are enforced deterministically."""
    
    def test_reason_codes_bounded_to_32(self):
        """Reason code histogram should be bounded to 32 keys."""
        # Generate 50 different reason codes
        many_codes = [f"REASON_CODE_{i:02d}" for i in range(50)]
        
        input_data = MemoryTelemetryInput(rejection_reason_codes=many_codes)
        event = build_memory_telemetry_event(input_data)
        
        # Should be bounded to 32 keys
        assert len(event.rejection_reason_hist) <= 32
        
        # Should be deterministic (same codes should be kept)
        event2 = build_memory_telemetry_event(input_data)
        assert event.rejection_reason_hist == event2.rejection_reason_hist
    
    def test_bundle_sizes_bounded_to_64(self):
        """Bundle sizes should be bounded to 64 items."""
        # Generate 100 bundle sizes
        many_sizes = list(range(100))
        
        input_data = MemoryTelemetryInput(bundle_sizes=many_sizes)
        event = build_memory_telemetry_event(input_data)
        
        # Should process only first 64 items
        total_buckets = sum(event.bundle_size_hist.values())
        assert total_buckets == 64
    
    def test_dict_keys_bounded_to_64(self):
        """Dictionary keys should be bounded to 64."""
        # Create caps snapshot with many keys
        many_caps = {f"field_{i:03d}": i for i in range(100)}
        
        input_data = MemoryTelemetryInput(caps_snapshot=many_caps)
        event = build_memory_telemetry_event(input_data)
        
        # Should be bounded to 64 keys
        assert len(event.caps_snapshot) <= 64
        
        # Should be deterministic (lexicographically first 64)
        event2 = build_memory_telemetry_event(input_data)
        assert event.caps_snapshot == event2.caps_snapshot
    
    def test_string_length_bounded(self):
        """Long strings should be truncated or replaced."""
        long_string = "A" * 200  # Longer than MAX_STRING_LENGTH
        
        struct = {"long_field": long_string, "safe_field": "OK"}
        sanitized, had_forbidden, dropped_count = sanitize_structure(struct)
        
        # Long string should be sanitized
        assert had_forbidden == True
        assert dropped_count > 0
        
        # Should not contain the long string
        sanitized_json = canonical_json(sanitized)
        assert long_string not in sanitized_json


# ============================================================================
# TEST 7: JSON Serializable + Field Types
# ============================================================================

class Test7_JsonSerializable:
    """Test JSON serialization and field types."""
    
    def test_event_json_serializable(self):
        """Event should be JSON serializable."""
        input_data = create_clean_input()
        event = build_memory_telemetry_event(input_data)
        
        # Should serialize to JSON without errors
        event_dict = asdict(event)
        json_str = json.dumps(event_dict)
        
        # Should deserialize back
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
    
    def test_field_types_correct(self):
        """All fields should have correct types."""
        input_data = create_clean_input()
        event = build_memory_telemetry_event(input_data)
        
        # Check field types
        assert isinstance(event.version, str)
        assert isinstance(event.writes_attempted, int)
        assert isinstance(event.writes_accepted, int)
        assert isinstance(event.writes_rejected, int)
        assert isinstance(event.rejection_reason_hist, dict)
        assert isinstance(event.ttl_class_hist, dict)
        assert isinstance(event.reads_attempted, int)
        assert isinstance(event.bundle_size_hist, dict)
        assert isinstance(event.bundle_chars_hist, dict)
        assert isinstance(event.caps_snapshot, dict)
        assert isinstance(event.memory_signature, str)
        assert isinstance(event.had_forbidden_keys, bool)
        assert isinstance(event.dropped_keys_count, int)
        
        # Check histogram value types
        for hist in [event.rejection_reason_hist, event.ttl_class_hist, 
                    event.bundle_size_hist, event.bundle_chars_hist]:
            for key, value in hist.items():
                assert isinstance(key, str)
                assert isinstance(value, int)
                assert value >= 0
    
    def test_no_raw_text_lists(self):
        """No lists of raw text should appear in event."""
        input_data = create_clean_input()
        event = build_memory_telemetry_event(input_data)
        
        event_json = canonical_json(asdict(event))
        
        # Should not contain obvious text list patterns
        forbidden_patterns = [
            '"user said"', '"i have"', '"my secret"', '"personal"',
            '"SENSITIVE_USER_TEXT"', '"SENSITIVE_MEMORY_VALUE"'
        ]
        
        for pattern in forbidden_patterns:
            assert pattern not in event_json


# ============================================================================
# TEST 8: Bucket Logic
# ============================================================================

class Test8_BucketLogic:
    """Test bucket logic for sizes and chars."""
    
    def test_size_buckets_correct(self):
        """Size bucket logic should be correct."""
        assert bucket_size(0) == "0"
        assert bucket_size(1) == "1-4"
        assert bucket_size(4) == "1-4"
        assert bucket_size(5) == "5-8"
        assert bucket_size(8) == "5-8"
        assert bucket_size(9) == "9-16"
        assert bucket_size(16) == "9-16"
        assert bucket_size(17) == "17+"
        assert bucket_size(1000) == "17+"
    
    def test_chars_buckets_correct(self):
        """Chars bucket logic should be correct."""
        assert bucket_chars(0) == "0"
        assert bucket_chars(1) == "1-400"
        assert bucket_chars(400) == "1-400"
        assert bucket_chars(401) == "401-800"
        assert bucket_chars(800) == "401-800"
        assert bucket_chars(801) == "801-1200"
        assert bucket_chars(1200) == "801-1200"
        assert bucket_chars(1201) == "1201+"
        assert bucket_chars(10000) == "1201+"
    
    def test_reason_code_sanitization(self):
        """Reason code sanitization should work correctly."""
        assert sanitize_reason_code("FORBIDDEN_CATEGORY") == "FORBIDDEN_CATEGORY"
        assert sanitize_reason_code("VALIDATION_FAIL") == "VALIDATION_FAIL"
        assert sanitize_reason_code("invalid reason") == "INVALID_REASON"
        assert sanitize_reason_code("user said: diabetes") == "INVALID_REASON"
        assert sanitize_reason_code("") == "INVALID_REASON"
        assert sanitize_reason_code("A" * 50) == "INVALID_REASON"  # Too long
    
    def test_ttl_class_sanitization(self):
        """TTL class sanitization should work correctly."""
        assert sanitize_ttl_class("TTL_1H") == "TTL_1H"
        assert sanitize_ttl_class("TTL_1D") == "TTL_1D"
        assert sanitize_ttl_class("TTL_10D") == "TTL_10D"
        assert sanitize_ttl_class("invalid_ttl") == "UNKNOWN"
        assert sanitize_ttl_class("SENSITIVE_TEXT") == "UNKNOWN"
        assert sanitize_ttl_class("") == "UNKNOWN"


# ============================================================================
# TEST 9: Fail-Closed Behavior
# ============================================================================

class Test9_FailClosed:
    """Test fail-closed behavior on errors."""
    
    def test_invalid_input_types_handled(self):
        """Invalid input types should be handled gracefully."""
        # Create input with invalid types
        input_data = MemoryTelemetryInput(
            writes_attempted="invalid",  # Should be int
            bundle_sizes=["not", "numbers"],  # Should be ints
            caps_snapshot="not_a_dict",  # Should be dict
        )
        
        # Should not crash, should return safe event
        event = build_memory_telemetry_event(input_data)
        
        # Should be valid event
        assert isinstance(event, MemoryTelemetryEvent)
        assert event.version == MEMORY_TELEMETRY_VERSION
        assert isinstance(event.memory_signature, str)
        assert len(event.memory_signature) == 64
    
    def test_none_input_handled(self):
        """None input should be handled gracefully."""
        input_data = MemoryTelemetryInput(
            rejection_reason_codes=None,
            ttl_classes=None,
            bundle_sizes=None,
            bundle_chars=None,
            caps_snapshot=None,
        )
        
        # Should not crash
        event = build_memory_telemetry_event(input_data)
        
        # Should be valid event with empty histograms
        assert isinstance(event, MemoryTelemetryEvent)
        assert event.rejection_reason_hist == {}
        assert event.ttl_class_hist == {}
        assert event.bundle_size_hist == {}
        assert event.bundle_chars_hist == {}
        assert event.caps_snapshot == {}


# ============================================================================
# RUNNER
# ============================================================================

def run_all():
    """Run all tests."""
    print("=" * 60)
    print("Phase 19 Step 7: Memory Telemetry Safety Tests")
    print("=" * 60)
    
    test_classes = [
        ("Test 1: No Sentinel Leakage", Test1_NoSentinelLeakage),
        ("Test 2: Structure-only Signature Invariance", Test2_SignatureInvariance),
        ("Test 3: Signature Changes on Structure Change", Test3_SignatureChanges),
        ("Test 4: Determinism Replay", Test4_DeterminismReplay),
        ("Test 5: Forbidden Keys Removed Recursively", Test5_ForbiddenKeysRemoval),
        ("Test 6: Bounds Enforcement", Test6_BoundsEnforcement),
        ("Test 7: JSON Serializable + Field Types", Test7_JsonSerializable),
        ("Test 8: Bucket Logic", Test8_BucketLogic),
        ("Test 9: Fail-Closed Behavior", Test9_FailClosed),
    ]
    
    failed = False
    for label, test_class in test_classes:
        print(f"\n{label}")
        instance = test_class()
        for method_name in sorted(dir(instance)):
            if method_name.startswith("test_"):
                try:
                    getattr(instance, method_name)()
                    print(f"  ✓ {method_name}")
                except AssertionError as e:
                    print(f"  ✗ {method_name}: {e}")
                    failed = True
                except Exception as e:
                    print(f"  ✗ {method_name}: EXCEPTION: {e}")
                    failed = True
    
    print("\n" + "=" * 60)
    if failed:
        print("SOME TESTS FAILED ✗")
        sys.exit(1)
    else:
        print("ALL PHASE 19 MEMORY TELEMETRY TESTS PASSED ✓")
        print("=" * 60)


if __name__ == "__main__":
    run_all()
