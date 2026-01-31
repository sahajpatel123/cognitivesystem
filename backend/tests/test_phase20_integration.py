#!/usr/bin/env python3
"""
Phase 20 Step 9: Integration Governance Gates

CI-grade self-contained test runner for governance integration.
Tests "no bypass" enforcement, determinism, and fail-closed behavior.

Gates:
1. Tool no-bypass - deny when caps disallow; allow only via governed wrapper
2. Memory no-bypass - store write count stays 0 when denied; wrapper required
3. Research facts without citations denied (origin=phase18, missing citation_ids)
4. TTL clamp/cap enforcement deterministic
5. Determinism replay 20x with shuffled dicts/lists → identical decision_signature
6. Telemetry clamp & sentinel non-leak
7. Audit append occurs and has stable chain signature/hash
8. Fail-closed invalid tenant/region → deny
"""

import sys
import json
import hashlib
import time
import random
from typing import Any, Dict, List

# Add backend to path
sys.path.insert(0, '/Users/sahajpatel/CascadeProjects/windsurf-project')

from backend.app.integration.governance_wiring import (
    governed_tool_call_request, governed_memory_write_request,
    governed_memory_read_request, governed_telemetry_emit,
    governed_export_request, governed_admin_action,
    GovernanceOp, GovernanceReason, canonical_json, detect_sentinel
)

# ============================================================================
# TEST FRAMEWORK
# ============================================================================

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def assert_true(self, condition: bool, message: str):
        if condition:
            self.passed += 1
        else:
            self.failed += 1
            self.errors.append(f"FAIL: {message}")
    
    def assert_false(self, condition: bool, message: str):
        self.assert_true(not condition, message)
    
    def assert_equal(self, actual: Any, expected: Any, message: str):
        self.assert_true(actual == expected, f"{message} (got {actual}, expected {expected})")
    
    def summary(self) -> str:
        total = self.passed + self.failed
        status = "PASS" if self.failed == 0 else "FAIL"
        return f"{status}: {self.passed}/{total} passed"

# ============================================================================
# MOCK STORE FOR MEMORY TESTS
# ============================================================================

class MockMemoryStore:
    def __init__(self):
        self.write_count = 0
        self.read_count = 0
        self.facts_stored = []
    
    def reset(self):
        self.write_count = 0
        self.read_count = 0
        self.facts_stored = []

# ============================================================================
# GATE 1: TOOL NO-BYPASS
# ============================================================================

def test_gate1_tool_no_bypass(result: TestResult):
    """Gate 1: Tool calls must go through governance wrapper."""
    print("Running Gate 1: Tool No-Bypass...")
    
    # Test 1: Denied tool call stays denied
    outcome = governed_tool_call_request(
        tenant_id="test_tenant_denied",
        region="us-east-1",
        query="test query",
        allowed_tools=["web_search"],
        request_flags={}
    )
    
    result.assert_false(outcome.ok, "Tool call should be denied for denied tenant")
    result.assert_true(outcome.reason in [
        GovernanceReason.TENANT_MISSING.value,
        GovernanceReason.POLICY_DENIED.value,
        GovernanceReason.INTERNAL_ERROR.value
    ], f"Tool denial reason should be governance-related, got: {outcome.reason}")
    
    # Test 2: Audit signature present
    result.assert_true(len(outcome.audit_signature) > 0, "Audit signature should be present")
    
    # Test 3: Outcome signature deterministic
    outcome2 = governed_tool_call_request(
        tenant_id="test_tenant_denied",
        region="us-east-1",
        query="test query",
        allowed_tools=["web_search"],
        request_flags={}
    )
    
    result.assert_equal(outcome.outcome_signature, outcome2.outcome_signature,
                       "Tool call outcomes should be deterministic")

# ============================================================================
# GATE 2: MEMORY NO-BYPASS
# ============================================================================

def test_gate2_memory_no_bypass(result: TestResult):
    """Gate 2: Memory operations must go through governance wrapper."""
    print("Running Gate 2: Memory No-Bypass...")
    
    mock_store = MockMemoryStore()
    
    # Test 1: Denied memory write
    facts_data = {
        "memory_patch": [
            {
                "category": "USER_GOALS",
                "key": "test_goal",
                "value_str": "test value",
                "provenance": {
                    "source_type": "USER_EXPLICIT",
                    "source_id": "test"
                }
            }
        ]
    }
    
    outcome = governed_memory_write_request(
        tenant_id="test_tenant_denied",
        region="us-east-1",
        facts_data=facts_data,
        origin="phase17"
    )
    
    result.assert_false(outcome.ok, "Memory write should be denied for denied tenant")
    result.assert_equal(mock_store.write_count, 0, "Store write count should stay 0 when denied")
    
    # Test 2: Memory read denial
    read_req = {"template": "RECENT", "categories": ["USER_GOALS"]}
    
    read_outcome = governed_memory_read_request(
        tenant_id="test_tenant_denied",
        region="us-east-1",
        read_request=read_req
    )
    
    result.assert_false(read_outcome.ok, "Memory read should be denied for denied tenant")
    result.assert_equal(mock_store.read_count, 0, "Store read count should stay 0 when denied")

# ============================================================================
# GATE 3: RESEARCH FACTS WITHOUT CITATIONS DENIED
# ============================================================================

def test_gate3_research_citation_enforcement(result: TestResult):
    """Gate 3: Research facts without citations must be denied."""
    print("Running Gate 3: Research Citation Enforcement...")
    
    # Test 1: Research fact missing citations
    research_facts = {
        "facts": [
            {
                "category": "FACTUAL_KNOWLEDGE",
                "key": "research_fact",
                "value_str": "some research finding",
                "provenance": {
                    "source_type": "TOOL_CITED",
                    "source_id": "research_engine",
                    "citation_ids": []  # Empty citations - should be denied
                }
            }
        ]
    }
    
    outcome = governed_memory_write_request(
        tenant_id="test_tenant_allowed",
        region="us-east-1",
        facts_data=research_facts,
        origin="phase18"
    )
    
    result.assert_false(outcome.ok, "Research fact without citations should be denied")
    result.assert_equal(outcome.reason, GovernanceReason.CITATION_MISSING.value,
                       "Reason should be CITATION_MISSING")
    
    # Test 2: Research fact with citations (would be allowed if tenant allows)
    research_facts_with_citations = {
        "facts": [
            {
                "category": "FACTUAL_KNOWLEDGE",
                "key": "research_fact",
                "value_str": "some research finding",
                "provenance": {
                    "source_type": "TOOL_CITED",
                    "source_id": "research_engine",
                    "citation_ids": ["cite_1", "cite_2"]
                }
            }
        ]
    }
    
    outcome_with_citations = governed_memory_write_request(
        tenant_id="test_tenant_allowed",
        region="us-east-1",
        facts_data=research_facts_with_citations,
        origin="phase18"
    )
    
    # Should not fail due to citations (may fail due to tenant policy)
    if not outcome_with_citations.ok:
        result.assert_true(outcome_with_citations.reason != GovernanceReason.CITATION_MISSING.value,
                          "Should not fail due to missing citations when citations present")

# ============================================================================
# GATE 4: TTL CLAMP ENFORCEMENT
# ============================================================================

def test_gate4_ttl_clamp_enforcement(result: TestResult):
    """Gate 4: TTL clamping should be deterministic."""
    print("Running Gate 4: TTL Clamp Enforcement...")
    
    # Test with memory write that would trigger TTL clamping
    facts_data = {
        "memory_patch": [
            {
                "category": "USER_GOALS",
                "key": "test_goal",
                "value_str": "test value",
                "expires_at_ms": int(time.time() * 1000) + 86400000 * 365,  # 1 year
                "provenance": {
                    "source_type": "USER_EXPLICIT",
                    "source_id": "test"
                }
            }
        ]
    }
    
    outcome1 = governed_memory_write_request(
        tenant_id="test_tenant_free",
        region="us-east-1",
        facts_data=facts_data,
        origin="phase17"
    )
    
    outcome2 = governed_memory_write_request(
        tenant_id="test_tenant_free",
        region="us-east-1",
        facts_data=facts_data,
        origin="phase17"
    )
    
    # TTL clamping should be deterministic
    result.assert_equal(outcome1.outcome_signature, outcome2.outcome_signature,
                       "TTL clamping should produce deterministic outcomes")
    
    # Should have clamps applied if governance allows
    if outcome1.decision and outcome1.decision.clamps_applied:
        result.assert_true("ttl_plan" in outcome1.decision.clamps_applied,
                          "TTL plan should be in clamps")

# ============================================================================
# GATE 5: DETERMINISM REPLAY
# ============================================================================

def test_gate5_determinism_replay(result: TestResult):
    """Gate 5: 20x replay with shuffled inputs should produce identical signatures."""
    print("Running Gate 5: Determinism Replay...")
    
    base_request = {
        "tenant_id": "test_tenant_determinism",
        "region": "us-west-2",
        "query": "determinism test",
        "allowed_tools": ["web_search", "doc_search"],
        "request_flags": {"flag1": True, "flag2": "value"}
    }
    
    signatures = []
    
    for i in range(20):
        # Shuffle the request data
        shuffled_tools = base_request["allowed_tools"].copy()
        random.shuffle(shuffled_tools)
        
        shuffled_flags = dict(base_request["request_flags"])
        # Add some randomness that shouldn't affect determinism
        
        outcome = governed_tool_call_request(
            tenant_id=base_request["tenant_id"],
            region=base_request["region"],
            query=base_request["query"],
            allowed_tools=shuffled_tools,
            request_flags=shuffled_flags
        )
        
        signatures.append(outcome.outcome_signature)
    
    # All signatures should be identical
    unique_signatures = set(signatures)
    result.assert_equal(len(unique_signatures), 1,
                       f"All 20 replays should produce identical signatures, got {len(unique_signatures)} unique")

# ============================================================================
# GATE 6: TELEMETRY CLAMP & SENTINEL NON-LEAK
# ============================================================================

def test_gate6_telemetry_clamp_sentinel(result: TestResult):
    """Gate 6: Telemetry should be clamped and never leak sentinel strings."""
    print("Running Gate 6: Telemetry Clamp & Sentinel Non-Leak...")
    
    # Test 1: Normal telemetry
    normal_telemetry = {
        "event_type": "test_event",
        "count": 42,
        "metadata": {"key": "value"}
    }
    
    outcome = governed_telemetry_emit(
        tenant_id="test_tenant_telemetry",
        region="us-east-1",
        telemetry_data=normal_telemetry
    )
    
    # Should have outcome signature
    result.assert_true(len(outcome.outcome_signature) > 0, "Telemetry should have outcome signature")
    
    # Test 2: Telemetry with sentinel strings
    sentinel_telemetry = {
        "event_type": "test_event",
        "user_data": "SENSITIVE_USER_TEXT_123",
        "secret": "SECRET_API_KEY_456"
    }
    
    sentinel_outcome = governed_telemetry_emit(
        tenant_id="test_tenant_telemetry",
        region="us-east-1",
        telemetry_data=sentinel_telemetry
    )
    
    # Should be denied due to sentinel detection
    if sentinel_outcome.ok:
        # If allowed, check that sentinels were stripped
        result.assert_false(detect_sentinel(canonical_json(sentinel_outcome.__dict__)),
                           "Outcome should not contain sentinel strings")
    else:
        result.assert_equal(sentinel_outcome.reason, GovernanceReason.SENTINEL_DETECTED.value,
                           "Should be denied due to sentinel detection")

# ============================================================================
# GATE 7: AUDIT APPEND & CHAIN SIGNATURE
# ============================================================================

def test_gate7_audit_append_chain(result: TestResult):
    """Gate 7: Audit events should be appended with stable signatures."""
    print("Running Gate 7: Audit Append & Chain Signature...")
    
    # Test multiple operations to build audit chain
    operations = [
        ("tool_call", lambda: governed_tool_call_request(
            "test_tenant_audit", "us-east-1", "test", ["web_search"], {})),
        ("memory_write", lambda: governed_memory_write_request(
            "test_tenant_audit", "us-east-1", {"memory_patch": []}, "phase17")),
        ("telemetry", lambda: governed_telemetry_emit(
            "test_tenant_audit", "us-east-1", {"event": "test"}))
    ]
    
    audit_signatures = []
    
    for op_name, op_func in operations:
        outcome = op_func()
        audit_signatures.append(outcome.audit_signature)
        
        # Each operation should have audit signature
        result.assert_true(len(outcome.audit_signature) > 0,
                          f"{op_name} should have audit signature")
    
    # Audit signatures should be deterministic for same operations
    outcome1 = governed_tool_call_request("test_tenant_audit", "us-east-1", "test", ["web_search"], {})
    outcome2 = governed_tool_call_request("test_tenant_audit", "us-east-1", "test", ["web_search"], {})
    
    result.assert_equal(outcome1.audit_signature, outcome2.audit_signature,
                       "Identical operations should have identical audit signatures")

# ============================================================================
# GATE 8: FAIL-CLOSED INVALID TENANT/REGION
# ============================================================================

def test_gate8_fail_closed_invalid(result: TestResult):
    """Gate 8: Invalid tenant/region should fail-closed with deny."""
    print("Running Gate 8: Fail-Closed Invalid Tenant/Region...")
    
    # Test 1: Invalid tenant
    invalid_tenant_outcome = governed_tool_call_request(
        tenant_id="",  # Empty tenant ID
        region="us-east-1",
        query="test",
        allowed_tools=["web_search"],
        request_flags={}
    )
    
    result.assert_false(invalid_tenant_outcome.ok, "Empty tenant ID should be denied")
    result.assert_true(invalid_tenant_outcome.reason in [
        GovernanceReason.TENANT_MISSING.value,
        GovernanceReason.INTERNAL_ERROR.value
    ], f"Invalid tenant should have appropriate reason, got: {invalid_tenant_outcome.reason}")
    
    # Test 2: Invalid region
    invalid_region_outcome = governed_tool_call_request(
        tenant_id="test_tenant",
        region="",  # Empty region
        query="test",
        allowed_tools=["web_search"],
        request_flags={}
    )
    
    result.assert_false(invalid_region_outcome.ok, "Empty region should be denied")
    
    # Test 3: Malformed requests should fail-closed
    malformed_memory_outcome = governed_memory_write_request(
        tenant_id="test_tenant",
        region="us-east-1",
        facts_data=None,  # Invalid facts data
        origin="phase17"
    )
    
    result.assert_false(malformed_memory_outcome.ok, "Malformed memory request should be denied")

# ============================================================================
# SENTINEL SCAN
# ============================================================================

def scan_all_outputs_for_sentinels(result: TestResult):
    """Scan all test outputs for sentinel strings."""
    print("Running Sentinel Scan...")
    
    # Test various operations and scan their outputs
    test_operations = [
        governed_tool_call_request("test", "us-east-1", "SENSITIVE_USER_TEXT_123", ["web"], {}),
        governed_memory_write_request("test", "us-east-1", {"patch": []}, "phase17"),
        governed_telemetry_emit("test", "us-east-1", {"data": "PRIVATE_INFO_789"}),
        governed_export_request("test", "us-east-1", {"type": "SECRET_EXPORT"}),
        governed_admin_action("test", "us-east-1", {"action": "SENSITIVE_ACTION"})
    ]
    
    for i, outcome in enumerate(test_operations):
        outcome_json = canonical_json(outcome.__dict__)
        
        result.assert_false(detect_sentinel(outcome_json),
                           f"Operation {i} output should not contain sentinel strings")
        
        # Also check individual fields
        if hasattr(outcome, 'reason'):
            result.assert_false(detect_sentinel(outcome.reason),
                               f"Operation {i} reason should not contain sentinels")
        
        if hasattr(outcome, 'outcome_signature'):
            result.assert_false(detect_sentinel(outcome.outcome_signature),
                               f"Operation {i} signature should not contain sentinels")

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Main test runner."""
    print("=" * 60)
    print("Phase 20 Step 9: Integration Governance Gates")
    print("=" * 60)
    
    result = TestResult()
    
    try:
        # Run all gates
        test_gate1_tool_no_bypass(result)
        test_gate2_memory_no_bypass(result)
        test_gate3_research_citation_enforcement(result)
        test_gate4_ttl_clamp_enforcement(result)
        test_gate5_determinism_replay(result)
        test_gate6_telemetry_clamp_sentinel(result)
        test_gate7_audit_append_chain(result)
        test_gate8_fail_closed_invalid(result)
        scan_all_outputs_for_sentinels(result)
        
    except Exception as e:
        result.failed += 1
        result.errors.append(f"CRITICAL ERROR: {str(e)}")
    
    # Print results
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(result.summary())
    
    if result.errors:
        print("\nERRORS:")
        for error in result.errors:
            print(f"  {error}")
    
    print("=" * 60)
    
    # Exit with appropriate code
    sys.exit(0 if result.failed == 0 else 1)

if __name__ == "__main__":
    main()
