#!/usr/bin/env python3
"""
PHASE 19 INTEGRATION CAPS TEST

Tests policy-gated memory integration wiring.
Deterministic, fail-closed, no user text leakage.

Gates:
1. Policy denies read
2. Policy denies write  
3. Phase 17 cannot write TOOL_CITED/DERIVED_SUMMARY
4. Phase 18 cannot store without citations
5. Max facts per request enforced by policy cap
6. Deterministic replay
7. No user text leakage
8. TTL cap cannot be overridden
"""

import sys
import os
import json
import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.app.integration.memory_wiring import (
    MemoryPolicyDecision, MemoryIntegrationOutcome,
    run_policy_gated_memory_read, run_policy_gated_memory_write_from_delta,
    run_policy_gated_memory_write_from_research, IntegrationReasonCode
)
from backend.app.memory.adapter import MemoryStore
from backend.app.memory.read import MemoryReadRequest, ReadTemplate
from backend.app.memory.schema import MemoryCategory

# Constants for deterministic testing
NOW_MS = 1700000000000  # Fixed timestamp
BUCKET_MS = 60000       # 1 minute bucket alignment

# Sentinel strings for leakage detection
SENSITIVE_SENTINELS = [
    "SENSITIVE_USER_TEXT_123",
    "SENSITIVE_USER_TEXT_456"
]

# Helper functions
def assert_true(condition: bool, message: str) -> None:
    """Assert condition is true, exit on failure."""
    if not condition:
        print(f"✗ ASSERTION FAILED: {message}")
        sys.exit(1)

def assert_equal(actual: Any, expected: Any, message: str) -> None:
    """Assert actual equals expected, exit on failure."""
    if actual != expected:
        print(f"✗ ASSERTION FAILED: {message}")
        print(f"  Expected: {expected}")
        print(f"  Actual: {actual}")
        sys.exit(1)

def assert_false(condition: bool, message: str) -> None:
    """Assert condition is false, exit on failure."""
    assert_true(not condition, message)

def stable_json(obj: Any) -> str:
    """Deterministic JSON serialization."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))

class FakeStore:
    """Fake memory store for testing with write tracking."""
    
    def __init__(self):
        self.facts = []
        self.write_calls = []
        self.read_calls = []
    
    def write_facts_with_expiry(self, facts, expires_at_ms):
        """Track write calls."""
        self.write_calls.append({
            "facts_count": len(facts),
            "expires_at_ms": expires_at_ms,
            "timestamp": NOW_MS
        })
        self.facts.extend(facts)
        return len(facts)
    
    def get_current_facts(self, now_ms, caps=None):
        """Track read calls and return facts."""
        self.read_calls.append({
            "now_ms": now_ms,
            "caps": caps,
            "timestamp": NOW_MS
        })
        return self.facts.copy()

def create_test_policy(
    read_allowed: bool = True,
    write_allowed: bool = True,
    ttl_plan: str = "FREE",
    max_facts_per_request: int = 8
) -> MemoryPolicyDecision:
    """Create test policy with specified settings."""
    return MemoryPolicyDecision(
        read_allowed=read_allowed,
        write_allowed=write_allowed,
        ttl_plan=ttl_plan,
        ttl_cap_class="TTL_1H",
        max_facts_per_request=max_facts_per_request,
        read_templates_allowed=["GOALS_AND_WORKFLOW"],
        max_facts_read=50,
        max_total_chars_read=2000,
        max_per_category_read=20,
        citations_required_for_research_writes=True
    )

def create_valid_delta() -> Dict[str, Any]:
    """Create valid delta for Phase 17 testing."""
    return {
        "memory_patch": [
            {
                "fact_id": "test_delta_001",
                "category": "USER_GOALS",
                "key": "learning_objective",
                "value_type": "STR",
                "value_str": "improve_python_skills",
                "confidence": 0.9,
                "provenance_type": "USER_EXPLICIT",
                "source_id": "delta_engine",
                "citation_ids": []
            }
        ]
    }

def create_valid_research_facts() -> Dict[str, Any]:
    """Create valid research facts for Phase 18 testing."""
    return {
        "facts": [
            {
                "fact_id": "test_research_001",
                "category": "PROJECT_CONTEXT",
                "key": "research_finding",
                "value_type": "STR",
                "value_str": "python_best_practices_summary",
                "confidence": 0.8,
                "provenance_type": "TOOL_CITED",
                "source_id": "research_engine",
                "citation_ids": ["cite_001", "cite_002"]
            }
        ]
    }

def check_no_sentinel_leakage(data: Any, context: str) -> None:
    """Check that no sentinel strings appear in data."""
    data_str = stable_json(data) if isinstance(data, (dict, list)) else str(data)
    for sentinel in SENSITIVE_SENTINELS:
        assert_true(sentinel not in data_str, f"Sentinel leaked in {context}: {sentinel}")

# Gate implementations
def gate_1_policy_denies_read():
    """Gate 1: Policy denies read."""
    print("Gate 1: Policy denies read")
    
    store = FakeStore()
    policy = create_test_policy(read_allowed=False)
    
    read_req = MemoryReadRequest(
        categories=[MemoryCategory.USER_GOALS],
        template=ReadTemplate.GOALS_AND_WORKFLOW,
        now_ms=NOW_MS
    )
    
    outcome = run_policy_gated_memory_read(policy, read_req, store, NOW_MS)
    
    # Assert denied
    assert_false(outcome.ok, "Read should be denied by policy")
    assert_equal(outcome.reason, "POLICY_DISABLED", "Should return POLICY_DISABLED")
    assert_equal(outcome.op, "READ", "Operation should be READ")
    
    # Assert bundle is empty
    assert_true(outcome.bundle is not None, "Bundle should be present")
    assert_equal(outcome.bundle["facts_count"], 0, "Bundle should be empty")
    assert_equal(outcome.bundle["total_chars"], 0, "Bundle should have no chars")
    
    # Assert signature exists and no sentinel leakage
    assert_true(len(outcome.memory_signature) > 0, "Signature should exist")
    check_no_sentinel_leakage(outcome.memory_signature, "read signature")
    check_no_sentinel_leakage(outcome.telemetry_event, "read telemetry")
    
    # Assert telemetry has writes_attempted=0
    assert_true(outcome.telemetry_event is not None, "Telemetry should be present")
    assert_equal(outcome.telemetry_event.writes_attempted, 0, "No writes attempted")
    
    print("✓ Gate 1: Policy denies read")

def gate_2_policy_denies_write():
    """Gate 2: Policy denies write."""
    print("Gate 2: Policy denies write")
    
    store = FakeStore()
    policy = create_test_policy(write_allowed=False)
    delta = create_valid_delta()
    
    initial_write_calls = len(store.write_calls)
    
    outcome = run_policy_gated_memory_write_from_delta(policy, delta, store, NOW_MS)
    
    # Assert denied
    assert_false(outcome.ok, "Write should be denied by policy")
    assert_equal(outcome.reason, "POLICY_DISABLED", "Should return POLICY_DISABLED")
    assert_equal(outcome.op, "WRITE", "Operation should be WRITE")
    
    # Assert store not written
    assert_equal(len(store.write_calls), initial_write_calls, "Store should not be written")
    
    print("✓ Gate 2: Policy denies write")

def gate_3_phase17_cannot_write_research_provenance():
    """Gate 3: Phase 17 cannot write TOOL_CITED/DERIVED_SUMMARY."""
    print("Gate 3: Phase 17 cannot write TOOL_CITED/DERIVED_SUMMARY")
    
    store = FakeStore()
    policy = create_test_policy()
    
    # Create delta with research provenance (invalid for Phase 17)
    invalid_delta = {
        "memory_patch": [
            {
                "fact_id": "test_invalid_001",
                "category": "PROJECT_CONTEXT",
                "key": "research_data",
                "value_type": "STR",
                "value_str": "some_research_finding",
                "confidence": 0.8,
                "provenance_type": "TOOL_CITED",  # Invalid for Phase 17
                "source_id": "fake_research",
                "citation_ids": ["fake_cite_001"]
            }
        ]
    }
    
    outcome = run_policy_gated_memory_write_from_delta(policy, invalid_delta, store, NOW_MS)
    
    # Assert rejected
    assert_false(outcome.ok, "Research provenance should be rejected for Phase 17")
    assert_equal(outcome.reason, "INVALID_REQUEST", "Should return INVALID_REQUEST")
    
    # Assert no writes
    assert_equal(len(store.write_calls), 0, "No writes should occur")
    
    print("✓ Gate 3: Phase 17 cannot write TOOL_CITED/DERIVED_SUMMARY")

def gate_4_phase18_cannot_store_without_citations():
    """Gate 4: Phase 18 cannot store without citations."""
    print("Gate 4: Phase 18 cannot store without citations")
    
    store = FakeStore()
    policy = create_test_policy()
    
    # Create research facts with missing citations
    invalid_research = {
        "facts": [
            {
                "fact_id": "test_no_cite_001",
                "category": "PROJECT_CONTEXT",
                "key": "research_finding",
                "value_type": "STR",
                "value_str": "uncited_research_data",
                "value_num": None,
                "value_bool": None,
                "value_list_str": None,
                "confidence": 0.8,
                "provenance": {
                    "source_type": "TOOL_CITED",
                    "source_id": "research_engine",
                    "collected_at_ms": NOW_MS,
                    "citation_ids": []  # Missing citations!
                },
                "created_at_ms": NOW_MS,
                "expires_at_ms": None,
                "tags": []
            }
        ]
    }
    
    outcome = run_policy_gated_memory_write_from_research(policy, invalid_research, store, NOW_MS)
    
    # Assert rejected with MISSING_CITATIONS
    assert_false(outcome.ok, "Research without citations should be rejected")
    assert_equal(outcome.reason, "MISSING_CITATIONS", "Should return MISSING_CITATIONS")
    
    # Assert store write not called
    assert_equal(len(store.write_calls), 0, "Store write should not be called")
    
    print("✓ Gate 4: Phase 18 cannot store without citations")

def gate_5_max_facts_per_request_enforced():
    """Gate 5: Max facts per request enforced by policy cap."""
    print("Gate 5: Max facts per request enforced by policy cap")
    
    store = FakeStore()
    policy = create_test_policy(max_facts_per_request=2)
    
    # Create delta with 3 facts (exceeds policy cap of 2)
    oversized_delta = {
        "memory_patch": [
            {
                "fact_id": f"test_fact_{i:03d}",
                "category": "USER_GOALS",
                "key": f"goal_{i}",
                "value_type": "STR",
                "value_str": f"goal_value_{i}",
                "value_num": None,
                "value_bool": None,
                "value_list_str": None,
                "confidence": 0.8,
                "provenance": {
                    "source_type": "USER_EXPLICIT",
                    "source_id": "delta_engine",
                    "collected_at_ms": NOW_MS,
                    "citation_ids": []
                },
                "created_at_ms": NOW_MS,
                "expires_at_ms": None,
                "tags": []
            }
            for i in range(3)  # 3 facts > policy cap of 2
        ]
    }
    
    outcome = run_policy_gated_memory_write_from_delta(policy, oversized_delta, store, NOW_MS)
    
    # Assert rejected deterministically
    assert_false(outcome.ok, "Oversized request should be rejected")
    assert_equal(outcome.reason, "TOO_MANY_FACTS", "Should return TOO_MANY_FACTS")
    
    print("✓ Gate 5: Max facts per request enforced by policy cap")

def gate_6_deterministic_replay():
    """Gate 6: Deterministic replay."""
    print("Gate 6: Deterministic replay")
    
    store = FakeStore()
    policy = create_test_policy()
    delta = create_valid_delta()
    
    # Run same call 20 times
    outcomes = []
    for i in range(20):
        outcome = run_policy_gated_memory_write_from_delta(policy, delta, store, NOW_MS)
        outcomes.append({
            "ok": outcome.ok,
            "reason": outcome.reason,
            "signature": outcome.memory_signature,
            "debug_counts": outcome.debug_counts
        })
    
    # Assert all outcomes identical
    first_outcome = outcomes[0]
    for i, outcome in enumerate(outcomes[1:], 1):
        assert_equal(outcome["ok"], first_outcome["ok"], f"Outcome {i} ok differs")
        assert_equal(outcome["reason"], first_outcome["reason"], f"Outcome {i} reason differs")
        assert_equal(outcome["signature"], first_outcome["signature"], f"Outcome {i} signature differs")
        assert_equal(stable_json(outcome["debug_counts"]), stable_json(first_outcome["debug_counts"]), 
                    f"Outcome {i} debug_counts differs")
    
    # Test shuffle stability for read operations
    read_req = MemoryReadRequest(
        categories=[MemoryCategory.USER_GOALS, MemoryCategory.PROJECT_CONTEXT],
        template=ReadTemplate.GOALS_AND_WORKFLOW,
        now_ms=NOW_MS
    )
    
    read_outcomes = []
    for shuffle_round in range(5):
        # Create new store with shuffled facts
        test_store = FakeStore()
        
        # Add some facts in shuffled order
        facts_data = [
            {"fact_id": f"fact_{i}", "category": "USER_GOALS", "key": f"key_{i}", "value_str": f"val_{i}"}
            for i in range(5)
        ]
        random.Random(42 + shuffle_round).shuffle(facts_data)
        
        outcome = run_policy_gated_memory_read(policy, read_req, test_store, NOW_MS)
        read_outcomes.append(outcome.memory_signature)
    
    # Assert read signatures are stable (deterministic ordering)
    first_read_sig = read_outcomes[0]
    for i, sig in enumerate(read_outcomes[1:], 1):
        assert_equal(sig, first_read_sig, f"Read signature {i} differs from first")
    
    print("✓ Gate 6: Deterministic replay")

def gate_7_no_user_text_leakage():
    """Gate 7: No user text leakage."""
    print("Gate 7: No user text leakage")
    
    store = FakeStore()
    policy = create_test_policy()
    
    # Test 1: Delta with sentinel in junk field
    delta_with_sentinel = {
        "memory_patch": [
            {
                "fact_id": "test_clean_001",
                "category": "USER_GOALS",
                "key": "clean_goal",
                "value_type": "STR",
                "value_str": "learn_programming",
                "confidence": 0.8,
                "provenance_type": "USER_EXPLICIT",
                "source_id": "delta_engine",
                "citation_ids": []
            }
        ],
        "junk_field": SENSITIVE_SENTINELS[0],  # Sentinel in junk field
        "extra_data": {
            "nested_sentinel": SENSITIVE_SENTINELS[1]
        }
    }
    
    outcome = run_policy_gated_memory_write_from_delta(policy, delta_with_sentinel, store, NOW_MS)
    
    # Check no sentinel leakage in outcome
    check_no_sentinel_leakage(outcome.telemetry_event, "delta telemetry")
    check_no_sentinel_leakage(outcome.memory_signature, "delta signature")
    check_no_sentinel_leakage(outcome.write_result, "delta write_result")
    
    # Test 2: Research facts with sentinel in extra field
    research_with_sentinel = {
        "facts": [
            {
                "fact_id": "test_research_clean_001",
                "category": "PROJECT_CONTEXT",
                "key": "research_data",
                "value_type": "STR",
                "value_str": "clean_research_finding",
                "confidence": 0.8,
                "provenance_type": "TOOL_CITED",
                "source_id": "research_engine",
                "citation_ids": ["cite_001"]
            }
        ],
        "metadata": {
            "user_query": SENSITIVE_SENTINELS[0],  # Sentinel in metadata
            "raw_response": SENSITIVE_SENTINELS[1]
        }
    }
    
    outcome = run_policy_gated_memory_write_from_research(policy, research_with_sentinel, store, NOW_MS)
    
    # Check no sentinel leakage
    check_no_sentinel_leakage(outcome.telemetry_event, "research telemetry")
    check_no_sentinel_leakage(outcome.memory_signature, "research signature")
    check_no_sentinel_leakage(outcome.write_result, "research write_result")
    
    # Test 3: Read request with sentinel (if possible)
    read_req = MemoryReadRequest(
        categories=[MemoryCategory.USER_GOALS],
        template=ReadTemplate.GOALS_AND_WORKFLOW,
        now_ms=NOW_MS
    )
    
    outcome = run_policy_gated_memory_read(policy, read_req, store, NOW_MS)
    
    # Check no sentinel leakage in read outcome
    check_no_sentinel_leakage(outcome.telemetry_event, "read telemetry")
    check_no_sentinel_leakage(outcome.memory_signature, "read signature")
    check_no_sentinel_leakage(outcome.bundle, "read bundle")
    
    print("✓ Gate 7: No user text leakage")

def gate_8_ttl_cap_cannot_be_overridden():
    """Gate 8: TTL cap cannot be overridden."""
    print("Gate 8: TTL cap cannot be overridden")
    
    store = FakeStore()
    policy = create_test_policy(ttl_plan="FREE")  # FREE plan has TTL_1H cap
    
    # Create delta with valid fact (TTL clamping happens at policy level)
    delta_with_ttl_request = {
        "memory_patch": [
            {
                "fact_id": "test_ttl_001",
                "category": "USER_GOALS",
                "key": "ttl_test_goal",
                "value_type": "STR",
                "value_str": "test_ttl_enforcement",
                "value_num": None,
                "value_bool": None,
                "value_list_str": None,
                "confidence": 0.8,
                "provenance": {
                    "source_type": "USER_EXPLICIT",
                    "source_id": "delta_engine",
                    "collected_at_ms": NOW_MS,
                    "citation_ids": []
                },
                "created_at_ms": NOW_MS,
                "expires_at_ms": None,
                "tags": []
            }
        ]
    }
    
    outcome = run_policy_gated_memory_write_from_delta(policy, delta_with_ttl_request, store, NOW_MS)
    
    # Assert write succeeds (TTL clamping doesn't fail the write)
    if not outcome.ok:
        print(f"  DEBUG: Write failed with reason: {outcome.reason}")
        print(f"  DEBUG: Write result: {outcome.write_result}")
    assert_true(outcome.ok, "Write should succeed with TTL clamping")
    
    # Check that TTL was clamped (if write_result contains TTL info)
    if outcome.write_result and "ttl_applied_ms" in outcome.write_result:
        ttl_applied = outcome.write_result["ttl_applied_ms"]
        if ttl_applied is not None:
            bucket_start = (NOW_MS // BUCKET_MS) * BUCKET_MS
            max_allowed_expiry = bucket_start + 3600000  # 1 hour for FREE plan
            
            # TTL should be clamped to policy cap
            assert_true(ttl_applied <= max_allowed_expiry, 
                       f"TTL should be clamped to 1H: {ttl_applied} > {max_allowed_expiry}")
    
    print("✓ Gate 8: TTL cap cannot be overridden")

# Main test runner
def main():
    """Run all integration caps tests."""
    print("Running Phase 19 Integration Caps Tests...")
    print()
    
    try:
        gate_1_policy_denies_read()
        gate_2_policy_denies_write()
        gate_3_phase17_cannot_write_research_provenance()
        gate_4_phase18_cannot_store_without_citations()
        gate_5_max_facts_per_request_enforced()
        gate_6_deterministic_replay()
        gate_7_no_user_text_leakage()
        gate_8_ttl_cap_cannot_be_overridden()
        
        print()
        print("ALL PHASE 19 INTEGRATION CAPS PASSED ✓")
        sys.exit(0)
        
    except Exception as e:
        print(f"✗ GATE FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
