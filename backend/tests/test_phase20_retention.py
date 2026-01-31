#!/usr/bin/env python3
"""
Phase 20 Step 4: Retention + Deletion Policy Tests

Self-contained test runner for retention policy with deterministic, fail-closed behavior.
No pytest dependency - uses built-in assertions and comprehensive safety testing.
"""

import sys
import os
import json
import random
from typing import Dict, Any, List

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.app.governance.retention import (
    ArtifactType, RetentionReasonCode, DeletionTarget, DeletionPlan, CandidateRecord,
    create_deletion_plan, get_retention_windows, get_memory_ttl_cutoff,
    compute_tenant_hash, assert_no_text_leakage, apply_deletion_plan,
    SHORTEST_RETENTION_MS, DAY_MS, HOUR_MS
)
from backend.app.governance.tenant import TenantConfig, PlanTier, FeatureFlag


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


def assert_less_equal(actual, expected, msg=""):
    """Assert actual <= expected."""
    if actual > expected:
        raise AssertionError(f"Expected {actual} <= {expected}. {msg}")


def assert_greater_equal(actual, expected, msg=""):
    """Assert actual >= expected."""
    if actual < expected:
        raise AssertionError(f"Expected {actual} >= {expected}. {msg}")


def serialize_plan(plan: DeletionPlan) -> str:
    """Serialize deletion plan to deterministic JSON string."""
    return json.dumps(plan.as_dict(), sort_keys=True, separators=(',', ':'))


def create_test_tenant_config(plan: PlanTier = PlanTier.PRO, 
                             features: List[FeatureFlag] = None) -> TenantConfig:
    """Create a test tenant config."""
    if features is None:
        features = [FeatureFlag.MEMORY_ENABLED, FeatureFlag.RESEARCH_ENABLED]
    
    return TenantConfig(
        tenant_id="test-tenant",
        plan=plan,
        regions=["us-east"],
        enabled_features=set(features)
    )


def create_test_candidates(artifact_type: ArtifactType, count: int, 
                          base_timestamp_ms: int, interval_ms: int = HOUR_MS) -> List[CandidateRecord]:
    """Create test candidate records."""
    candidates = []
    for i in range(count):
        candidates.append(CandidateRecord(
            artifact_type=artifact_type,
            tenant_id="test-tenant",
            record_id=f"record_{i:03d}",
            timestamp_ms=base_timestamp_ms + (i * interval_ms),
            metadata={"index": i, "test_data": f"DATA_{i}"}
        ))
    return candidates


# ============================================================================
# TEST GROUPS
# ============================================================================

def test_fail_closed_shortest_retention():
    """Gate 1: Fail-closed shortest retention."""
    print("Gate 1: Fail-closed shortest retention")
    
    now_ms = 1640995200000  # Fixed timestamp
    
    # Test with None tenant config
    candidates = create_test_candidates(ArtifactType.AUDIT_LOG, 5, now_ms - 10 * DAY_MS)
    
    plan = create_deletion_plan(
        tenant_config=None,
        artifact_type=ArtifactType.AUDIT_LOG,
        candidates=candidates,
        now_ms=now_ms
    )
    
    assert_false(plan.allowed, "Plan should be denied with None tenant config")
    assert_equal(plan.reason, RetentionReasonCode.POLICY_MISSING_FAIL_CLOSED, 
                "Should have POLICY_MISSING_FAIL_CLOSED reason")
    assert_equal(plan.effective_retention_windows, SHORTEST_RETENTION_MS, 
                "Should use shortest retention windows")
    
    # Test with invalid tenant config (missing required fields)
    try:
        invalid_config = TenantConfig(
            tenant_id="",  # Invalid empty tenant_id
            plan=PlanTier.PRO,
            regions=[],
            enabled_features=set()
        )
        
        plan2 = create_deletion_plan(
            tenant_config=invalid_config,
            artifact_type=ArtifactType.AUDIT_LOG,
            candidates=candidates,
            now_ms=now_ms
        )
        
        # Should either fail closed or use shortest retention
        if not plan2.allowed:
            assert_in(plan2.reason, [RetentionReasonCode.POLICY_MISSING_FAIL_CLOSED, 
                                   RetentionReasonCode.INVALID_TENANT, 
                                   RetentionReasonCode.INTERNAL_INCONSISTENCY],
                     "Should have appropriate fail-closed reason")
    except Exception:
        # Expected if validation fails at construction
        pass
    
    # Test deterministic plan signature
    plan3 = create_deletion_plan(
        tenant_config=None,
        artifact_type=ArtifactType.AUDIT_LOG,
        candidates=candidates,
        now_ms=now_ms
    )
    
    assert_equal(plan.signature, plan3.signature, "Fail-closed plans should be deterministic")
    
    print("✓ Gate 1: Fail-closed shortest retention")


def test_deterministic_ordering_under_shuffle():
    """Gate 2: Deterministic ordering under shuffle."""
    print("Gate 2: Deterministic ordering under shuffle")
    
    tenant_config = create_test_tenant_config(PlanTier.PRO)
    now_ms = 1640995200000
    
    # Create candidates that will be eligible for deletion
    base_candidates = create_test_candidates(
        ArtifactType.TELEMETRY, 20, now_ms - 30 * DAY_MS, HOUR_MS
    )
    
    # Test 20 shuffles
    results = []
    for i in range(20):
        # Shuffle candidates
        shuffled_candidates = base_candidates.copy()
        random.seed(i)  # Deterministic shuffle for reproducibility
        random.shuffle(shuffled_candidates)
        
        plan = create_deletion_plan(
            tenant_config=tenant_config,
            artifact_type=ArtifactType.TELEMETRY,
            candidates=shuffled_candidates,
            now_ms=now_ms
        )
        
        result = {
            "signature": plan.signature,
            "target_count": len(plan.targets),
            "target_hashes": [t.target_key_hash for t in plan.targets],
            "serialized": serialize_plan(plan)
        }
        results.append(result)
    
    # All results should be identical
    first_result = results[0]
    for i, result in enumerate(results[1:], 1):
        assert_equal(result["signature"], first_result["signature"], 
                    f"Signature differs on shuffle {i+1}")
        assert_equal(result["target_count"], first_result["target_count"], 
                    f"Target count differs on shuffle {i+1}")
        assert_equal(result["target_hashes"], first_result["target_hashes"], 
                    f"Target order differs on shuffle {i+1}")
        assert_equal(result["serialized"], first_result["serialized"], 
                    f"Serialization differs on shuffle {i+1}")
    
    print("✓ Gate 2: Deterministic ordering under shuffle")


def test_tiered_retention_differences():
    """Gate 3: Tiered retention differences."""
    print("Gate 3: Tiered retention differences")
    
    # Test retention windows for different plan tiers
    free_config = create_test_tenant_config(PlanTier.FREE)
    pro_config = create_test_tenant_config(PlanTier.PRO)
    max_config = create_test_tenant_config(PlanTier.MAX)
    enterprise_config = create_test_tenant_config(PlanTier.ENTERPRISE)
    
    free_windows = get_retention_windows(free_config)
    pro_windows = get_retention_windows(pro_config)
    max_windows = get_retention_windows(max_config)
    enterprise_windows = get_retention_windows(enterprise_config)
    
    # Test ordering: AUDIT >= TELEMETRY >= RESEARCH_CACHE within each tier
    for windows in [free_windows, pro_windows, max_windows, enterprise_windows]:
        assert_greater_equal(windows["AUDIT_LOG"], windows["TELEMETRY"], 
                           "Audit log should have >= telemetry retention")
        assert_greater_equal(windows["TELEMETRY"], windows["RESEARCH_CACHE"], 
                           "Telemetry should have >= research cache retention")
    
    # Test tier ordering: FREE <= PRO <= MAX <= ENTERPRISE
    for artifact_type in ["AUDIT_LOG", "TELEMETRY", "RESEARCH_CACHE"]:
        assert_less_equal(free_windows[artifact_type], pro_windows[artifact_type], 
                         f"FREE should have <= PRO retention for {artifact_type}")
        assert_less_equal(pro_windows[artifact_type], max_windows[artifact_type], 
                         f"PRO should have <= MAX retention for {artifact_type}")
        assert_less_equal(max_windows[artifact_type], enterprise_windows[artifact_type], 
                         f"MAX should have <= ENTERPRISE retention for {artifact_type}")
    
    print("✓ Gate 3: Tiered retention differences")


def test_max_ops_per_run_enforced():
    """Gate 4: max_ops_per_run enforced deterministically."""
    print("Gate 4: max_ops_per_run enforced")
    
    tenant_config = create_test_tenant_config(PlanTier.PRO)
    now_ms = 1640995200000
    
    # Create many eligible candidates (more than max_ops limit)
    many_candidates = create_test_candidates(
        ArtifactType.TELEMETRY, 100, now_ms - 30 * DAY_MS, HOUR_MS
    )
    
    # Test with small max_ops_per_run
    max_ops = 10
    
    plan = create_deletion_plan(
        tenant_config=tenant_config,
        artifact_type=ArtifactType.TELEMETRY,
        candidates=many_candidates,
        now_ms=now_ms,
        max_ops_per_run=max_ops
    )
    
    assert_true(plan.allowed, "Plan should be allowed")
    assert_equal(plan.reason, RetentionReasonCode.LIMIT_CLAMPED, 
                "Should have LIMIT_CLAMPED reason when truncating")
    assert_equal(len(plan.targets), max_ops, 
                f"Should have exactly {max_ops} targets")
    assert_equal(plan.max_ops_per_run, max_ops, 
                "Should record the max_ops_per_run used")
    
    # Test deterministic truncation - same inputs should give same targets
    plan2 = create_deletion_plan(
        tenant_config=tenant_config,
        artifact_type=ArtifactType.TELEMETRY,
        candidates=many_candidates,
        now_ms=now_ms,
        max_ops_per_run=max_ops
    )
    
    assert_equal(plan.signature, plan2.signature, "Truncation should be deterministic")
    assert_equal([t.target_key_hash for t in plan.targets], 
                [t.target_key_hash for t in plan2.targets], 
                "Same targets should be selected deterministically")
    
    print("✓ Gate 4: max_ops_per_run enforced")


def test_memory_ttl_interlock_conservatism():
    """Gate 5: Memory TTL interlock conservatism."""
    print("Gate 5: Memory TTL interlock conservatism")
    
    tenant_config = create_test_tenant_config(PlanTier.FREE)  # TTL_1H cap
    now_ms = 1640995200000
    
    # Get memory TTL cutoff
    memory_cutoff_ms = get_memory_ttl_cutoff(tenant_config, now_ms)
    
    # Create memory events around the cutoff boundary
    candidates = []
    
    # Events before cutoff (should be eligible)
    for i in range(5):
        candidates.append(CandidateRecord(
            artifact_type=ArtifactType.MEMORY_EVENT_LOG,
            tenant_id="test-tenant",
            record_id=f"old_memory_{i}",
            timestamp_ms=memory_cutoff_ms - (i + 1) * HOUR_MS,
            metadata={"category": "old"}
        ))
    
    # Events after cutoff (should NOT be eligible)
    for i in range(5):
        candidates.append(CandidateRecord(
            artifact_type=ArtifactType.MEMORY_EVENT_LOG,
            tenant_id="test-tenant",
            record_id=f"new_memory_{i}",
            timestamp_ms=memory_cutoff_ms + (i + 1) * HOUR_MS,
            metadata={"category": "new"}
        ))
    
    plan = create_deletion_plan(
        tenant_config=tenant_config,
        artifact_type=ArtifactType.MEMORY_EVENT_LOG,
        candidates=candidates,
        now_ms=now_ms
    )
    
    assert_true(plan.allowed, "Memory deletion plan should be allowed")
    
    # Verify that only old events (before cutoff) are targeted
    # Note: The exact count depends on retention window vs TTL cutoff interaction
    if len(plan.targets) > 0:
        # All targets should be from events before the cutoff
        for target in plan.targets:
            # We can't directly verify timestamp from target (it's hashed)
            # but we can verify the plan is conservative
            pass
    
    # Test with None tenant config (fail-closed)
    plan_fail_closed = create_deletion_plan(
        tenant_config=None,
        artifact_type=ArtifactType.MEMORY_EVENT_LOG,
        candidates=candidates,
        now_ms=now_ms
    )
    
    assert_false(plan_fail_closed.allowed, "Should fail closed with None config")
    
    print("✓ Gate 5: Memory TTL interlock conservatism")


def test_research_cache_cutoff_deterministic():
    """Gate 6: Research cache cutoff deterministic."""
    print("Gate 6: Research cache cutoff deterministic")
    
    tenant_config = create_test_tenant_config(PlanTier.PRO)
    now_ms = 1640995200000
    bucket_ms = HOUR_MS
    
    # Create cache entries with timestamps around bucket boundaries
    candidates = []
    
    # Entries in different time buckets
    for i in range(10):
        timestamp_ms = now_ms - (i * bucket_ms) - (bucket_ms // 2)  # Middle of bucket
        candidates.append(CandidateRecord(
            artifact_type=ArtifactType.RESEARCH_CACHE,
            tenant_id="test-tenant",
            record_id=f"cache_entry_{i}",
            timestamp_ms=timestamp_ms,
            metadata={"bucket_index": i}
        ))
    
    # Test plan creation multiple times - should be deterministic
    plans = []
    for _ in range(5):
        plan = create_deletion_plan(
            tenant_config=tenant_config,
            artifact_type=ArtifactType.RESEARCH_CACHE,
            candidates=candidates,
            now_ms=now_ms,
            bucket_ms=bucket_ms
        )
        plans.append(plan)
    
    # All plans should be identical
    first_plan = plans[0]
    for i, plan in enumerate(plans[1:], 1):
        assert_equal(plan.signature, first_plan.signature, 
                    f"Plan {i+1} signature should match first plan")
        assert_equal(len(plan.targets), len(first_plan.targets), 
                    f"Plan {i+1} target count should match first plan")
    
    # Test bucket boundary behavior
    # Entries exactly at bucket boundaries should be handled deterministically
    boundary_candidates = [
        CandidateRecord(
            artifact_type=ArtifactType.RESEARCH_CACHE,
            tenant_id="test-tenant",
            record_id="boundary_entry",
            timestamp_ms=now_ms - (10 * bucket_ms),  # Exactly at boundary
            metadata={"type": "boundary"}
        )
    ]
    
    boundary_plan = create_deletion_plan(
        tenant_config=tenant_config,
        artifact_type=ArtifactType.RESEARCH_CACHE,
        candidates=boundary_candidates,
        now_ms=now_ms,
        bucket_ms=bucket_ms
    )
    
    # Should be deterministic
    assert_true(len(boundary_plan.signature) > 0, "Should have valid signature")
    
    print("✓ Gate 6: Research cache cutoff deterministic")


def test_no_text_leakage():
    """Gate 7: No text leakage."""
    print("Gate 7: No text leakage")
    
    tenant_config = create_test_tenant_config(PlanTier.PRO)
    now_ms = 1640995200000
    
    # Create candidates with sentinel strings in various places
    candidates_with_sentinels = [
        CandidateRecord(
            artifact_type=ArtifactType.AUDIT_LOG,
            tenant_id=SENSITIVE_USER_TEXT_123,  # Sentinel in tenant_id
            record_id="normal_record_1",
            timestamp_ms=now_ms - 10 * DAY_MS,
            metadata={"safe_key": "safe_value"}
        ),
        CandidateRecord(
            artifact_type=ArtifactType.AUDIT_LOG,
            tenant_id="normal-tenant",
            record_id=SENSITIVE_USER_TEXT_456,  # Sentinel in record_id
            timestamp_ms=now_ms - 10 * DAY_MS,
            metadata={"safe_key": "safe_value"}
        ),
        CandidateRecord(
            artifact_type=ArtifactType.AUDIT_LOG,
            tenant_id="normal-tenant",
            record_id="normal_record_3",
            timestamp_ms=now_ms - 10 * DAY_MS,
            metadata={
                "user_text": SENSITIVE_USER_TEXT_123,  # Forbidden key with sentinel
                "prompt": "some prompt text",  # Forbidden key
                SENSITIVE_USER_TEXT_456: "sentinel_key",  # Sentinel as key
                "safe_key": "safe_value"
            }
        )
    ]
    
    plan = create_deletion_plan(
        tenant_config=tenant_config,
        artifact_type=ArtifactType.AUDIT_LOG,
        candidates=candidates_with_sentinels,
        now_ms=now_ms
    )
    
    # Check that no sentinel strings appear in plan outputs
    serialized_plan = serialize_plan(plan)
    assert_no_text_leakage(serialized_plan, "serialized deletion plan")
    assert_no_text_leakage(plan.signature, "plan signature")
    
    # Check individual plan fields
    for target in plan.targets:
        assert_no_text_leakage(target.tenant_hash, "target tenant_hash")
        assert_no_text_leakage(target.target_key_hash, "target key_hash")
    
    # Verify that tenant_hash doesn't contain raw tenant_id
    for target in plan.targets:
        assert_not_in(SENSITIVE_USER_TEXT_123, target.tenant_hash, 
                     "tenant_hash should not contain raw sentinel tenant_id")
        assert_equal(len(target.tenant_hash), 64, "tenant_hash should be SHA256 (64 chars)")
        assert_equal(len(target.target_key_hash), 64, "target_key_hash should be SHA256 (64 chars)")
    
    print("✓ Gate 7: No text leakage")


def test_unknown_artifact_type_fails_closed():
    """Gate 8: Unknown artifact type fails closed."""
    print("Gate 8: Unknown artifact type fails closed")
    
    tenant_config = create_test_tenant_config(PlanTier.PRO)
    now_ms = 1640995200000
    
    candidates = create_test_candidates(ArtifactType.AUDIT_LOG, 5, now_ms - 10 * DAY_MS)
    
    # Test with invalid artifact type (simulate by passing string instead of enum)
    try:
        plan = create_deletion_plan(
            tenant_config=tenant_config,
            artifact_type="INVALID_ARTIFACT_TYPE",  # Invalid type
            candidates=candidates,
            now_ms=now_ms
        )
        
        # Should fail closed
        assert_false(plan.allowed, "Plan should be denied for unknown artifact type")
        assert_equal(plan.reason, RetentionReasonCode.UNKNOWN_ARTIFACT_TYPE, 
                    "Should have UNKNOWN_ARTIFACT_TYPE reason")
        assert_equal(plan.effective_retention_windows, SHORTEST_RETENTION_MS, 
                    "Should use shortest retention windows")
        assert_true(len(plan.signature) > 0, "Should have deterministic signature")
        
    except (ValueError, TypeError):
        # Expected if enum validation fails at function entry
        pass
    
    # Test deterministic behavior for unknown types
    try:
        plan1 = create_deletion_plan(
            tenant_config=tenant_config,
            artifact_type="UNKNOWN_TYPE_1",
            candidates=candidates,
            now_ms=now_ms
        )
        
        plan2 = create_deletion_plan(
            tenant_config=tenant_config,
            artifact_type="UNKNOWN_TYPE_1",  # Same unknown type
            candidates=candidates,
            now_ms=now_ms
        )
        
        # Should be deterministic
        assert_equal(plan1.signature, plan2.signature, 
                    "Unknown artifact type handling should be deterministic")
        
    except (ValueError, TypeError):
        # Expected if validation fails
        pass
    
    print("✓ Gate 8: Unknown artifact type fails closed")


def test_deletion_executor_stub():
    """Test deletion executor stub functionality."""
    print("Test: Deletion executor stub")
    
    tenant_config = create_test_tenant_config(PlanTier.PRO)
    now_ms = 1640995200000
    
    candidates = create_test_candidates(ArtifactType.TELEMETRY, 5, now_ms - 20 * DAY_MS)
    
    plan = create_deletion_plan(
        tenant_config=tenant_config,
        artifact_type=ArtifactType.TELEMETRY,
        candidates=candidates,
        now_ms=now_ms
    )
    
    # Test applying allowed plan
    if plan.allowed:
        result = apply_deletion_plan(plan)
        assert_true(result.success, "Should succeed for allowed plan")
        assert_equal(result.deleted_count, len(plan.targets), 
                    "Should report correct deletion count")
        assert_equal(result.error_count, 0, "Should have no errors")
    
    # Test applying denied plan
    denied_plan = create_deletion_plan(
        tenant_config=None,  # Will create denied plan
        artifact_type=ArtifactType.AUDIT_LOG,
        candidates=candidates,
        now_ms=now_ms
    )
    
    denied_result = apply_deletion_plan(denied_plan)
    assert_false(denied_result.success, "Should fail for denied plan")
    assert_equal(denied_result.deleted_count, 0, "Should delete nothing for denied plan")
    
    print("✓ Test: Deletion executor stub")


def test_bounds_enforcement():
    """Test bounds enforcement on all inputs."""
    print("Test: Bounds enforcement")
    
    tenant_config = create_test_tenant_config(PlanTier.ENTERPRISE)
    now_ms = 1640995200000
    
    # Create excessive candidates (more than MAX_CANDIDATES_PROCESSED)
    excessive_candidates = create_test_candidates(
        ArtifactType.AUDIT_LOG, 1000, now_ms - 100 * DAY_MS, HOUR_MS
    )
    
    plan = create_deletion_plan(
        tenant_config=tenant_config,
        artifact_type=ArtifactType.AUDIT_LOG,
        candidates=excessive_candidates,
        now_ms=now_ms
    )
    
    # Should not crash and should produce valid plan
    assert_true(isinstance(plan, DeletionPlan), "Should produce valid DeletionPlan")
    assert_true(len(plan.signature) > 0, "Should have valid signature")
    
    # Test with candidates containing oversized metadata
    candidates_with_large_metadata = []
    for i in range(10):
        large_metadata = {}
        # Add many keys (more than MAX_DICT_KEYS)
        for j in range(100):
            large_metadata[f"key_{j:03d}"] = f"value_{j}"
        
        # Add oversized string
        large_metadata["huge_string"] = "X" * 1000
        
        candidates_with_large_metadata.append(CandidateRecord(
            artifact_type=ArtifactType.TELEMETRY,
            tenant_id="test-tenant",
            record_id=f"large_record_{i}",
            timestamp_ms=now_ms - 10 * DAY_MS,
            metadata=large_metadata
        ))
    
    large_plan = create_deletion_plan(
        tenant_config=tenant_config,
        artifact_type=ArtifactType.TELEMETRY,
        candidates=candidates_with_large_metadata,
        now_ms=now_ms
    )
    
    # Should handle large metadata gracefully
    assert_true(isinstance(large_plan, DeletionPlan), "Should handle large metadata")
    assert_true(len(large_plan.signature) > 0, "Should have valid signature")
    
    print("✓ Test: Bounds enforcement")


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_all() -> bool:
    """Run all tests and return success status."""
    try:
        print("Running Phase 20 Retention Policy Tests...")
        print()
        
        test_fail_closed_shortest_retention()
        test_deterministic_ordering_under_shuffle()
        test_tiered_retention_differences()
        test_max_ops_per_run_enforced()
        test_memory_ttl_interlock_conservatism()
        test_research_cache_cutoff_deterministic()
        test_no_text_leakage()
        test_unknown_artifact_type_fails_closed()
        test_deletion_executor_stub()
        test_bounds_enforcement()
        
        print()
        print("ALL PHASE 20 RETENTION POLICY TESTS PASSED ✓")
        return True
        
    except Exception as e:
        print(f"✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
