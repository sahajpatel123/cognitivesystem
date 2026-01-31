#!/usr/bin/env python3
"""
Phase 20 Step 3: Audit Log Safety Tests

Self-contained test runner for audit log with structure-only, append-only, signed behavior.
No pytest dependency - uses built-in assertions and comprehensive safety testing.
"""

import sys
import os
import json
from typing import Dict, Any, List

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.app.governance.audit import (
    AuditEvent, AuditLog, AuditOperationType, AuditDecision, AuditReasonCode,
    record_audit_event, AUDIT_MODEL_VERSION, sanitize_to_struct_meta,
    compute_tenant_ref, canonical_json
)


# ============================================================================
# TEST CONSTANTS
# ============================================================================

# Sentinel strings for leakage testing
SENSITIVE_USER_TEXT_123 = "SENSITIVE_USER_TEXT_123"
SENSITIVE_USER_TEXT_456 = "SENSITIVE_USER_TEXT_456"

SENTINEL_STRINGS = [SENSITIVE_USER_TEXT_123, SENSITIVE_USER_TEXT_456]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def assert_equal(actual, expected, msg=""):
    """Assert equality with descriptive error."""
    if actual != expected:
        raise AssertionError(f"Expected {expected}, got {actual}. {msg}")


def assert_true(condition, msg=""):
    """Assert condition is true."""
    if not condition:
        raise AssertionError(f"Expected True, got False. {msg}")


def assert_false(condition, msg=""):
    """Assert condition is false."""
    if condition:
        raise AssertionError(f"Expected False, got True. {msg}")


def assert_in(item, container, msg=""):
    """Assert item is in container."""
    if item not in container:
        raise AssertionError(f"Expected {item} in {container}. {msg}")


def assert_not_in(item, container, msg=""):
    """Assert item is not in container."""
    if item in container:
        raise AssertionError(f"Expected {item} not in {container}. {msg}")


def serialize_event(event: AuditEvent) -> str:
    """Serialize event to deterministic JSON string."""
    return json.dumps(event.as_dict(), sort_keys=True, separators=(',', ':'))


def check_no_sentinel_leakage(data: Any, context: str = ""):
    """Check that no sentinel strings appear in serialized data."""
    serialized = json.dumps(data) if not isinstance(data, str) else data
    for sentinel in SENTINEL_STRINGS:
        if sentinel in serialized:
            raise AssertionError(f"Sentinel string '{sentinel}' found in {context}: {serialized}")


# ============================================================================
# TEST GROUPS
# ============================================================================

def test_sentinel_leakage_guard():
    """Test 1: Sentinel leakage guard - ensure sensitive data never appears in audit."""
    print("Test 1: Sentinel leakage guard")
    
    log = AuditLog()
    
    # Test sentinel in tenant_id
    event1 = record_audit_event(
        tenant_id=SENSITIVE_USER_TEXT_123,
        operation=AuditOperationType.TOOL_CALL,
        decision=AuditDecision.ALLOW,
        reason=AuditReasonCode.POLICY_DISABLED,
        payload=None,
        now_ms=1000000,
        log=log
    )
    
    # Check event serialization doesn't contain sentinel
    serialized = serialize_event(event1)
    check_no_sentinel_leakage(serialized, "event with sentinel tenant_id")
    
    # Check tenant_ref is hashed, not raw
    assert_not_in(SENSITIVE_USER_TEXT_123, event1.tenant_ref, "tenant_ref should not contain raw tenant_id")
    assert_equal(len(event1.tenant_ref), 64, "tenant_ref should be SHA256 hex (64 chars)")
    
    # Test sentinel in payload keys and values
    payload_with_sentinels = {
        SENSITIVE_USER_TEXT_456: "some value",  # Sentinel in key
        "normal_key": SENSITIVE_USER_TEXT_123,  # Sentinel in value
        "nested": {
            "user_text": "this should be dropped",  # Forbidden key
            SENSITIVE_USER_TEXT_456: "nested sentinel"  # Nested sentinel key
        }
    }
    
    event2 = record_audit_event(
        tenant_id="safe-tenant",
        operation=AuditOperationType.MEMORY_WRITE,
        decision=AuditDecision.DENY,
        reason=AuditReasonCode.FORBIDDEN_CONTENT_DETECTED,
        payload=payload_with_sentinels,
        now_ms=2000000,
        log=log
    )
    
    # Check event doesn't contain sentinels
    serialized2 = serialize_event(event2)
    check_no_sentinel_leakage(serialized2, "event with sentinel payload")
    
    # Check signature doesn't contain sentinels
    check_no_sentinel_leakage(event2.signature, "event signature")
    check_no_sentinel_leakage(event2.event_id, "event ID")
    
    # Check audit log stored events don't contain sentinels
    stored_events = log.list_events()
    for i, stored_event in enumerate(stored_events):
        stored_serialized = serialize_event(stored_event)
        check_no_sentinel_leakage(stored_serialized, f"stored event {i}")
    
    print("✓ Test 1: Sentinel leakage guard")


def test_determinism():
    """Test 2: Deterministic behavior - same inputs produce identical results."""
    print("Test 2: Deterministic behavior")
    
    # Test same inputs 20 times
    results = []
    for i in range(20):
        log = AuditLog()
        
        event = record_audit_event(
            tenant_id="test-tenant",
            operation=AuditOperationType.EXPORT_REQUEST,
            decision=AuditDecision.ALLOW,
            reason=AuditReasonCode.POLICY_DISABLED,
            payload={"safe_key": "SAFE_VALUE", "count": 42},
            now_ms=1640995200000,  # Fixed timestamp
            log=log
        )
        
        result = {
            "event_id": event.event_id,
            "signature": event.signature,
            "serialized": serialize_event(event)
        }
        results.append(result)
    
    # All results should be identical
    first_result = results[0]
    for i, result in enumerate(results[1:], 1):
        assert_equal(result["event_id"], first_result["event_id"], f"Event ID differs on iteration {i+1}")
        assert_equal(result["signature"], first_result["signature"], f"Signature differs on iteration {i+1}")
        assert_equal(result["serialized"], first_result["serialized"], f"Serialization differs on iteration {i+1}")
    
    print("✓ Test 2: Deterministic behavior")


def test_append_only_chain():
    """Test 3: Append-only chain verification."""
    print("Test 3: Append-only chain verification")
    
    log = AuditLog()
    
    # Append 3 events
    event1 = record_audit_event(
        tenant_id="tenant1",
        operation=AuditOperationType.TOOL_CALL,
        decision=AuditDecision.ALLOW,
        reason=AuditReasonCode.POLICY_DISABLED,
        payload={"step": 1},
        now_ms=1000000,
        log=log
    )
    
    event2 = record_audit_event(
        tenant_id="tenant2",
        operation=AuditOperationType.MEMORY_READ,
        decision=AuditDecision.DENY,
        reason=AuditReasonCode.MEMORY_READ_NOT_ALLOWED,
        payload={"step": 2},
        now_ms=2000000,
        log=log
    )
    
    event3 = record_audit_event(
        tenant_id="tenant3",
        operation=AuditOperationType.ADMIN_ACTION,
        decision=AuditDecision.DENY,
        reason=AuditReasonCode.ADMIN_NOT_ALLOWED,
        payload={"step": 3},
        now_ms=3000000,
        log=log
    )
    
    # Verify chain is valid
    chain_ok, bad_index = log.verify_chain()
    assert_true(chain_ok, f"Chain should be valid, but failed at index {bad_index}")
    
    # Check chaining: event2.prev_sig should equal event1.signature
    assert_equal(event2.prev_sig, event1.signature, "Event 2 prev_sig should match event 1 signature")
    assert_equal(event3.prev_sig, event2.signature, "Event 3 prev_sig should match event 2 signature")
    
    # Test chain verification detects tampering
    events = log.list_events()
    assert_equal(len(events), 3, "Should have 3 events")
    
    # Create a new log with tampered event
    tampered_log = AuditLog()
    tampered_log.append(event1)
    
    # Create tampered event2 with different struct_meta
    tampered_payload = {"step": 999, "tampered": True}  # Different from original
    tampered_event2 = record_audit_event(
        tenant_id="tenant2",
        operation=AuditOperationType.MEMORY_READ,
        decision=AuditDecision.DENY,
        reason=AuditReasonCode.MEMORY_READ_NOT_ALLOWED,
        payload=tampered_payload,
        now_ms=2000000,
        log=AuditLog()  # Use fresh log to get same prev_sig as event1
    )
    
    # Manually set prev_sig to match event1 (simulating tampering attempt)
    tampered_event2_fixed_prev = AuditEvent(
        event_id=tampered_event2.event_id,
        event_version=tampered_event2.event_version,
        ts_bucket_ms=tampered_event2.ts_bucket_ms,
        tenant_ref=tampered_event2.tenant_ref,
        operation=tampered_event2.operation,
        decision=tampered_event2.decision,
        reason=tampered_event2.reason,
        struct_meta=tampered_event2.struct_meta,
        prev_sig=event1.signature,  # Correct prev_sig
        signature=tampered_event2.signature  # But wrong signature for the content
    )
    
    tampered_log.append(tampered_event2_fixed_prev)
    
    # Verification should fail due to signature mismatch
    tampered_ok, tampered_bad_index = tampered_log.verify_chain()
    assert_false(tampered_ok, "Tampered chain should fail verification")
    assert_equal(tampered_bad_index, 1, "Should detect tampering at index 1")
    
    print("✓ Test 3: Append-only chain verification")


def test_forbidden_keys_dropped():
    """Test 4: Forbidden keys are dropped from payload."""
    print("Test 4: Forbidden keys dropped")
    
    log = AuditLog()
    
    # Payload with forbidden keys at various nesting levels
    forbidden_payload = {
        "user_text": "This should be dropped",
        "prompt": "This should also be dropped",
        "safe_key": "SAFE_VALUE",
        "nested": {
            "message": "Nested forbidden",
            "tool_output": "More forbidden content",
            "safe_nested": "SAFE_NESTED",
            "deep": {
                "content": "Deep forbidden",
                "body": "Also forbidden",
                "safe_deep": "SAFE_DEEP"
            }
        },
        "list_with_forbidden": [
            {"snippet": "forbidden in list"},
            {"safe_list_item": "SAFE_LIST"}
        ]
    }
    
    event = record_audit_event(
        tenant_id="test-tenant",
        operation=AuditOperationType.GOVERNANCE_OP,
        decision=AuditDecision.DENY,
        reason=AuditReasonCode.FORBIDDEN_CONTENT_DETECTED,
        payload=forbidden_payload,
        now_ms=1000000,
        log=log
    )
    
    # Check forbidden keys are not present in struct_meta
    struct_meta = event.struct_meta
    
    # Direct forbidden keys should be absent
    assert_not_in("user_text", struct_meta, "user_text should be dropped")
    assert_not_in("prompt", struct_meta, "prompt should be dropped")
    
    # Safe keys should be present
    assert_in("safe_key", struct_meta, "safe_key should be preserved")
    
    # Check nested structure
    if "nested" in struct_meta:
        nested = struct_meta["nested"]
        assert_not_in("message", nested, "nested message should be dropped")
        assert_not_in("tool_output", nested, "nested tool_output should be dropped")
        assert_in("safe_nested", nested, "safe_nested should be preserved")
        
        if "deep" in nested:
            deep = nested["deep"]
            assert_not_in("content", deep, "deep content should be dropped")
            assert_not_in("body", deep, "deep body should be dropped")
            assert_in("safe_deep", deep, "safe_deep should be preserved")
    
    # Check structure-only counters
    assert_in("dropped_keys_count", struct_meta, "Should have dropped_keys_count")
    assert_in("had_forbidden_keys", struct_meta, "Should have had_forbidden_keys")
    assert_true(struct_meta["had_forbidden_keys"], "had_forbidden_keys should be True")
    assert_true(struct_meta["dropped_keys_count"] > 0, "dropped_keys_count should be > 0")
    
    print("✓ Test 4: Forbidden keys dropped")


def test_bounds_enforcement():
    """Test 5: Bounds enforcement on oversized inputs."""
    print("Test 5: Bounds enforcement")
    
    log = AuditLog()
    
    # Create oversized payload
    oversized_payload = {}
    
    # Too many keys (>64)
    for i in range(100):
        oversized_payload[f"key_{i:03d}"] = f"VALUE_{i}"
    
    # Oversized string
    oversized_payload["huge_string"] = "X" * 1000
    
    # Oversized list
    oversized_payload["huge_list"] = list(range(200))
    
    # Deep nesting (>6 levels)
    deep_dict = oversized_payload
    for i in range(10):
        deep_dict[f"level_{i}"] = {}
        deep_dict = deep_dict[f"level_{i}"]
    deep_dict["final"] = "DEEP_VALUE"
    
    event = record_audit_event(
        tenant_id="test-tenant",
        operation=AuditOperationType.LOGGING_CHANGE,
        decision=AuditDecision.ALLOW,
        reason=AuditReasonCode.POLICY_DISABLED,
        payload=oversized_payload,
        now_ms=1000000,
        log=log
    )
    
    # Should not crash and should produce valid event
    assert_true(isinstance(event, AuditEvent), "Should produce valid AuditEvent")
    assert_true(len(event.signature) > 0, "Should have valid signature")
    assert_true(len(event.event_id) > 0, "Should have valid event_id")
    
    # Check bounds are enforced
    struct_meta = event.struct_meta
    
    # Should have bounded number of keys (plus our structure counters)
    total_keys = len(struct_meta)
    assert_true(total_keys <= 67, f"Should have bounded keys, got {total_keys}")  # 64 + 3 counters
    
    # Check that dropped_keys_count reflects truncation
    if "dropped_keys_count" in struct_meta:
        assert_true(struct_meta["dropped_keys_count"] > 0, "Should have dropped some keys due to bounds")
    
    print("✓ Test 5: Bounds enforcement")


def test_fail_closed():
    """Test 6: Fail-closed behavior with invalid inputs."""
    print("Test 6: Fail-closed behavior")
    
    log = AuditLog()
    
    # Test with non-serializable payload
    class NonSerializable:
        def __init__(self):
            self.func = lambda x: x
    
    bad_payload = {
        "normal_key": "normal_value",
        "bad_object": NonSerializable(),
        "bad_function": lambda x: x * 2
    }
    
    # Should not crash, should produce safe event
    event = record_audit_event(
        tenant_id="test-tenant",
        operation=AuditOperationType.TOOL_CALL,
        decision=AuditDecision.ALLOW,
        reason=AuditReasonCode.POLICY_DISABLED,
        payload=bad_payload,
        now_ms=1000000,
        log=log
    )
    
    # Should produce valid event (possibly with AUDIT_SANITIZE_FAIL reason)
    assert_true(isinstance(event, AuditEvent), "Should produce valid AuditEvent even with bad payload")
    assert_true(len(event.signature) > 0, "Should have valid signature")
    assert_true(len(event.event_id) > 0, "Should have valid event_id")
    
    # Event should be appended to log
    events = log.list_events()
    assert_equal(len(events), 1, "Event should be appended to log")
    
    # Test with completely invalid inputs
    event2 = record_audit_event(
        tenant_id=None,  # Invalid tenant_id
        operation="INVALID_OPERATION",  # Invalid operation
        decision=AuditDecision.DENY,
        reason=AuditReasonCode.INTERNAL_INCONSISTENCY,
        payload={"circular": None},
        now_ms="invalid_timestamp",  # Invalid timestamp
        log=log
    )
    
    # Should still produce some kind of event
    assert_true(isinstance(event2, AuditEvent), "Should produce AuditEvent even with invalid inputs")
    
    print("✓ Test 6: Fail-closed behavior")


def test_no_raw_tenant_id():
    """Test 7: No raw tenant ID in audit data."""
    print("Test 7: No raw tenant ID")
    
    log = AuditLog()
    
    tenant_id = "very-specific-tenant-identifier-12345"
    
    event = record_audit_event(
        tenant_id=tenant_id,
        operation=AuditOperationType.EXPORT_REQUEST,
        decision=AuditDecision.ALLOW,
        reason=AuditReasonCode.POLICY_DISABLED,
        payload={"test": "data"},
        now_ms=1000000,
        log=log
    )
    
    # tenant_ref should be SHA256 hash
    assert_equal(len(event.tenant_ref), 64, "tenant_ref should be 64-char SHA256 hex")
    assert_true(all(c in '0123456789abcdef' for c in event.tenant_ref), "tenant_ref should be hex")
    
    # tenant_ref should not contain raw tenant_id
    assert_not_in(tenant_id, event.tenant_ref, "tenant_ref should not contain raw tenant_id")
    
    # Verify tenant_ref is correct hash
    expected_hash = compute_tenant_ref(tenant_id)
    assert_equal(event.tenant_ref, expected_hash, "tenant_ref should match computed hash")
    
    # Check serialized event doesn't contain raw tenant_id
    serialized = serialize_event(event)
    assert_not_in(tenant_id, serialized, "Serialized event should not contain raw tenant_id")
    
    # Check signature doesn't contain raw tenant_id
    assert_not_in(tenant_id, event.signature, "Signature should not contain raw tenant_id")
    assert_not_in(tenant_id, event.event_id, "Event ID should not contain raw tenant_id")
    
    print("✓ Test 7: No raw tenant ID")


def test_canonicalization():
    """Test 8: Canonical JSON representation."""
    print("Test 8: Canonicalization")
    
    # Test that different key orders produce same canonical JSON
    dict1 = {"z": 1, "a": 2, "m": {"y": 3, "b": 4}}
    dict2 = {"a": 2, "m": {"b": 4, "y": 3}, "z": 1}
    
    canonical1 = canonical_json(dict1)
    canonical2 = canonical_json(dict2)
    
    assert_equal(canonical1, canonical2, "Different key orders should produce same canonical JSON")
    
    # Test with nested structures
    nested1 = {"outer": {"inner": [{"c": 3, "a": 1}, {"b": 2}]}}
    nested2 = {"outer": {"inner": [{"a": 1, "c": 3}, {"b": 2}]}}
    
    canonical_nested1 = canonical_json(nested1)
    canonical_nested2 = canonical_json(nested2)
    
    assert_equal(canonical_nested1, canonical_nested2, "Nested structures should canonicalize consistently")
    
    print("✓ Test 8: Canonicalization")


def test_sanitization_edge_cases():
    """Test 9: Edge cases in sanitization."""
    print("Test 9: Sanitization edge cases")
    
    # Test empty and None payloads
    empty_meta = sanitize_to_struct_meta(None)
    assert_true(isinstance(empty_meta, dict), "None payload should produce dict")
    assert_in("dropped_keys_count", empty_meta, "Should have structure counters")
    
    empty_dict_meta = sanitize_to_struct_meta({})
    assert_true(isinstance(empty_dict_meta, dict), "Empty dict should produce dict")
    
    # Test with various data types
    mixed_payload = {
        "string": "test",
        "int": 42,
        "float": 3.14159,
        "bool": True,
        "null": None,
        "list": [1, 2, 3],
        "nested_dict": {"a": 1}
    }
    
    mixed_meta = sanitize_to_struct_meta(mixed_payload)
    assert_true(isinstance(mixed_meta, dict), "Mixed payload should produce dict")
    
    # Test safe enum-like strings are preserved
    safe_payload = {
        "reason_code": "TOOL_NOT_ALLOWED",
        "ttl_label": "TTL_1H",
        "bucket": "1-4"
    }
    
    safe_meta = sanitize_to_struct_meta(safe_payload)
    assert_equal(safe_meta.get("reason_code"), "TOOL_NOT_ALLOWED", "Safe enum should be preserved")
    assert_equal(safe_meta.get("ttl_label"), "TTL_1H", "Safe TTL should be preserved")
    assert_equal(safe_meta.get("bucket"), "1-4", "Safe bucket should be preserved")
    
    # Test unsafe strings are redacted
    unsafe_payload = {
        "unsafe_string": "This is some user content that should be redacted",
        "special_chars": "Special!@#$%^&*()chars"
    }
    
    unsafe_meta = sanitize_to_struct_meta(unsafe_payload)
    assert_equal(unsafe_meta.get("unsafe_string"), "REDACTED_TOKEN", "Unsafe string should be redacted")
    assert_equal(unsafe_meta.get("special_chars"), "REDACTED_TOKEN", "Special chars should be redacted")
    
    print("✓ Test 9: Sanitization edge cases")


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_all() -> bool:
    """Run all tests and return success status."""
    try:
        print("Running Phase 20 Audit Safety Tests...")
        print()
        
        test_sentinel_leakage_guard()
        test_determinism()
        test_append_only_chain()
        test_forbidden_keys_dropped()
        test_bounds_enforcement()
        test_fail_closed()
        test_no_raw_tenant_id()
        test_canonicalization()
        test_sanitization_edge_cases()
        
        print()
        print("ALL PHASE 20 AUDIT SAFETY TESTS PASSED ✓")
        return True
        
    except Exception as e:
        print(f"✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
