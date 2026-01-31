"""
Phase 19 Step 3: TTL Policy Engine Tests

Self-check runner for TTL policy engine.
CI-grade tests with deterministic behavior.
"""

import json
import os
import sys
from dataclasses import asdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.memory.ttl_policy import (
    resolve_ttl,
    TTLClass,
    PlanTier,
    TTLDecision,
    TTL_POLICY_VERSION,
    TTL_1H,
    TTL_1D,
    TTL_10D,
    REQUEST_TIME_BUCKET_MS,
    ReasonCode,
)


def decision_to_json(decision: TTLDecision) -> str:
    """Convert TTLDecision to deterministic JSON string."""
    return json.dumps(asdict(decision), sort_keys=True, separators=(",", ":"))


# ============================================================================
# TEST 1: Determinism (20 replays)
# ============================================================================

class Test1_Determinism:
    """Test determinism across multiple runs."""
    
    def test_same_inputs_20_times_identical_result(self):
        """Same inputs 20 times produces identical TTLDecision."""
        results = []
        for _ in range(20):
            decision = resolve_ttl(
                plan_tier="FREE",
                requested_ttl_class="TTL_1H",
                now_ms=1000000,
            )
            results.append(decision_to_json(decision))
        
        first = results[0]
        for i, r in enumerate(results[1:], 1):
            assert r == first, f"Run {i}: result differs from first run"
    
    def test_different_plans_deterministic(self):
        """Different plans produce deterministic results."""
        for plan in ["FREE", "PRO", "MAX"]:
            results = []
            for _ in range(20):
                decision = resolve_ttl(
                    plan_tier=plan,
                    requested_ttl_class=None,
                    now_ms=5000000,
                )
                results.append(decision_to_json(decision))
            
            first = results[0]
            for i, r in enumerate(results[1:], 1):
                assert r == first, f"Plan {plan}, Run {i}: result differs"


# ============================================================================
# TEST 2: Bucket Behavior
# ============================================================================

class Test2_BucketBehavior:
    """Test time bucketing behavior."""
    
    def test_same_bucket_same_expiry(self):
        """now_ms = 60_001 and 60_999 => same bucket_start_ms, same expires_at_ms."""
        decision1 = resolve_ttl("FREE", "TTL_1H", 60_001)
        decision2 = resolve_ttl("FREE", "TTL_1H", 60_999)
        
        assert decision1.bucket_start_ms == decision2.bucket_start_ms, \
            f"Bucket start should be same: {decision1.bucket_start_ms} vs {decision2.bucket_start_ms}"
        assert decision1.expires_at_ms == decision2.expires_at_ms, \
            f"Expires should be same: {decision1.expires_at_ms} vs {decision2.expires_at_ms}"
        
        # Both should be in bucket starting at 60_000
        assert decision1.bucket_start_ms == 60_000, \
            f"Expected bucket_start_ms=60000, got {decision1.bucket_start_ms}"
    
    def test_different_buckets_different_expiry(self):
        """now_ms = 119_999 vs 120_000 => bucket_start_ms differs by exactly 60_000."""
        decision1 = resolve_ttl("FREE", "TTL_1H", 119_999)
        decision2 = resolve_ttl("FREE", "TTL_1H", 120_000)
        
        assert decision1.bucket_start_ms == 60_000, \
            f"Expected bucket_start_ms=60000, got {decision1.bucket_start_ms}"
        assert decision2.bucket_start_ms == 120_000, \
            f"Expected bucket_start_ms=120000, got {decision2.bucket_start_ms}"
        
        assert decision2.bucket_start_ms - decision1.bucket_start_ms == REQUEST_TIME_BUCKET_MS, \
            f"Bucket difference should be {REQUEST_TIME_BUCKET_MS}"
        
        # Expiry should also differ by bucket size
        assert decision2.expires_at_ms - decision1.expires_at_ms == REQUEST_TIME_BUCKET_MS, \
            f"Expiry difference should be {REQUEST_TIME_BUCKET_MS}"
    
    def test_bucket_start_zero_for_small_now(self):
        """now_ms < bucket size => bucket_start_ms = 0."""
        decision = resolve_ttl("FREE", "TTL_1H", 30_000)
        
        assert decision.bucket_start_ms == 0, \
            f"Expected bucket_start_ms=0, got {decision.bucket_start_ms}"


# ============================================================================
# TEST 3: Plan Cap Clamp
# ============================================================================

class Test3_PlanCapClamp:
    """Test plan cap clamping."""
    
    def test_free_clamps_ttl_10d_to_1h(self):
        """FREE + requested TTL_10D => effective TTL_1H, clamped."""
        decision = resolve_ttl("FREE", "TTL_10D", 1000000)
        
        assert decision.ok, f"Should be ok, got errors"
        assert decision.effective_ttl == "TTL_1H", \
            f"Expected TTL_1H, got {decision.effective_ttl}"
        assert decision.was_clamped, "Should be clamped"
        assert decision.reason_code == ReasonCode.CLAMPED_TO_PLAN_CAP, \
            f"Expected CLAMPED_TO_PLAN_CAP, got {decision.reason_code}"
    
    def test_free_clamps_ttl_1d_to_1h(self):
        """FREE + requested TTL_1D => effective TTL_1H, clamped."""
        decision = resolve_ttl("FREE", "TTL_1D", 1000000)
        
        assert decision.ok, f"Should be ok"
        assert decision.effective_ttl == "TTL_1H", \
            f"Expected TTL_1H, got {decision.effective_ttl}"
        assert decision.was_clamped, "Should be clamped"
    
    def test_pro_clamps_ttl_10d_to_1d(self):
        """PRO + requested TTL_10D => effective TTL_1D, clamped."""
        decision = resolve_ttl("PRO", "TTL_10D", 1000000)
        
        assert decision.ok, f"Should be ok"
        assert decision.effective_ttl == "TTL_1D", \
            f"Expected TTL_1D, got {decision.effective_ttl}"
        assert decision.was_clamped, "Should be clamped"
        assert decision.reason_code == ReasonCode.CLAMPED_TO_PLAN_CAP
    
    def test_max_no_clamp_ttl_10d(self):
        """MAX + requested TTL_10D => effective TTL_10D, not clamped."""
        decision = resolve_ttl("MAX", "TTL_10D", 1000000)
        
        assert decision.ok, f"Should be ok"
        assert decision.effective_ttl == "TTL_10D", \
            f"Expected TTL_10D, got {decision.effective_ttl}"
        assert not decision.was_clamped, "Should not be clamped"
        assert decision.reason_code == ReasonCode.OK


# ============================================================================
# TEST 4: Default TTL Behavior
# ============================================================================

class Test4_DefaultTTL:
    """Test default TTL behavior when no TTL requested."""
    
    def test_free_default_ttl_1h(self):
        """FREE + requested None => effective TTL_1H, DEFAULT_APPLIED."""
        decision = resolve_ttl("FREE", None, 1000000)
        
        assert decision.ok, f"Should be ok"
        assert decision.effective_ttl == "TTL_1H", \
            f"Expected TTL_1H, got {decision.effective_ttl}"
        assert decision.reason_code == ReasonCode.DEFAULT_APPLIED
        assert not decision.was_clamped, "Default is not clamping"
    
    def test_pro_default_ttl_1d(self):
        """PRO + requested None => effective TTL_1D, DEFAULT_APPLIED."""
        decision = resolve_ttl("PRO", None, 1000000)
        
        assert decision.ok, f"Should be ok"
        assert decision.effective_ttl == "TTL_1D", \
            f"Expected TTL_1D, got {decision.effective_ttl}"
        assert decision.reason_code == ReasonCode.DEFAULT_APPLIED
    
    def test_max_default_ttl_1d_not_10d(self):
        """MAX + requested None => effective TTL_1D (not TTL_10D), DEFAULT_APPLIED."""
        decision = resolve_ttl("MAX", None, 1000000)
        
        assert decision.ok, f"Should be ok"
        assert decision.effective_ttl == "TTL_1D", \
            f"Expected TTL_1D (not TTL_10D), got {decision.effective_ttl}"
        assert decision.reason_code == ReasonCode.DEFAULT_APPLIED


# ============================================================================
# TEST 5: Invalid Inputs Fail-Closed
# ============================================================================

class Test5_InvalidInputs:
    """Test fail-closed behavior for invalid inputs."""
    
    def test_invalid_plan_falls_back_to_free(self):
        """Invalid plan => ok False, INVALID_PLAN, fallback to FREE defaults."""
        decision = resolve_ttl("INVALID_PLAN", "TTL_1H", 1000000)
        
        assert not decision.ok, "Should not be ok"
        assert decision.reason_code == ReasonCode.INVALID_PLAN
        assert decision.plan == "FREE", f"Should fallback to FREE, got {decision.plan}"
        assert decision.effective_ttl == "TTL_1H", \
            f"Should use FREE default TTL_1H, got {decision.effective_ttl}"
    
    def test_invalid_ttl_uses_plan_default(self):
        """Invalid TTL => ok False, INVALID_TTL, effective TTL becomes plan default."""
        decision = resolve_ttl("PRO", "INVALID_TTL", 1000000)
        
        assert not decision.ok, "Should not be ok"
        assert decision.reason_code == ReasonCode.INVALID_TTL
        assert decision.effective_ttl == "TTL_1D", \
            f"Should use PRO default TTL_1D, got {decision.effective_ttl}"
    
    def test_negative_now_ms_fails_closed(self):
        """now_ms = -1 => ok False, INVALID_NOW, bucket_start_ms = 0."""
        decision = resolve_ttl("FREE", "TTL_1H", -1)
        
        assert not decision.ok, "Should not be ok"
        assert decision.reason_code == ReasonCode.INVALID_NOW
        assert decision.bucket_start_ms == 0, \
            f"Expected bucket_start_ms=0, got {decision.bucket_start_ms}"
        # Expiry should still be computed deterministically
        assert decision.expires_at_ms == TTL_1H, \
            f"Expected expires_at_ms={TTL_1H}, got {decision.expires_at_ms}"
    
    def test_invalid_inputs_still_deterministic(self):
        """Invalid inputs produce deterministic results across runs."""
        results = []
        for _ in range(20):
            decision = resolve_ttl("INVALID", "INVALID", -999)
            results.append(decision_to_json(decision))
        
        first = results[0]
        for i, r in enumerate(results[1:], 1):
            assert r == first, f"Run {i}: invalid input result differs"


# ============================================================================
# TEST 6: Requested TTL Cannot Override Plan Caps
# ============================================================================

class Test6_CapEnforcement:
    """Test that requested TTL cannot override plan caps."""
    
    def test_free_never_returns_ttl_1d(self):
        """FREE never returns TTL_1D as effective."""
        for ttl in ["TTL_1H", "TTL_1D", "TTL_10D"]:
            decision = resolve_ttl("FREE", ttl, 1000000)
            assert decision.effective_ttl == "TTL_1H", \
                f"FREE with {ttl} should return TTL_1H, got {decision.effective_ttl}"
    
    def test_free_never_returns_ttl_10d(self):
        """FREE never returns TTL_10D as effective."""
        decision = resolve_ttl("FREE", "TTL_10D", 1000000)
        assert decision.effective_ttl != "TTL_10D", \
            f"FREE should never return TTL_10D, got {decision.effective_ttl}"
    
    def test_pro_never_returns_ttl_10d(self):
        """PRO never returns TTL_10D as effective."""
        for ttl in ["TTL_1H", "TTL_1D", "TTL_10D"]:
            decision = resolve_ttl("PRO", ttl, 1000000)
            assert decision.effective_ttl != "TTL_10D", \
                f"PRO with {ttl} should not return TTL_10D, got {decision.effective_ttl}"
    
    def test_max_can_return_all_ttl_classes(self):
        """MAX can return any TTL class."""
        for ttl in ["TTL_1H", "TTL_1D", "TTL_10D"]:
            decision = resolve_ttl("MAX", ttl, 1000000)
            assert decision.effective_ttl == ttl, \
                f"MAX with {ttl} should return {ttl}, got {decision.effective_ttl}"


# ============================================================================
# TEST 7: Policy Version
# ============================================================================

class Test7_PolicyVersion:
    """Test policy version is always set."""
    
    def test_policy_version_always_set(self):
        """policy_version is always set to TTL_POLICY_VERSION."""
        for plan in ["FREE", "PRO", "MAX", "INVALID"]:
            for ttl in [None, "TTL_1H", "TTL_1D", "TTL_10D", "INVALID"]:
                for now in [0, 1000000, -1]:
                    decision = resolve_ttl(plan, ttl, now)
                    assert decision.policy_version == TTL_POLICY_VERSION, \
                        f"Expected version {TTL_POLICY_VERSION}, got {decision.policy_version}"


# ============================================================================
# TEST 8: Expiry Computation
# ============================================================================

class Test8_ExpiryComputation:
    """Test expiry computation is correct."""
    
    def test_expiry_is_bucket_plus_duration(self):
        """expires_at_ms = bucket_start_ms + duration."""
        decision = resolve_ttl("FREE", "TTL_1H", 120_000)
        
        expected_bucket = 120_000
        expected_expiry = expected_bucket + TTL_1H
        
        assert decision.bucket_start_ms == expected_bucket, \
            f"Expected bucket {expected_bucket}, got {decision.bucket_start_ms}"
        assert decision.expires_at_ms == expected_expiry, \
            f"Expected expiry {expected_expiry}, got {decision.expires_at_ms}"
    
    def test_expiry_for_each_ttl_class(self):
        """Verify expiry for each TTL class."""
        now_ms = 60_000
        bucket = 60_000
        
        for ttl_class, duration in [
            ("TTL_1H", TTL_1H),
            ("TTL_1D", TTL_1D),
            ("TTL_10D", TTL_10D),
        ]:
            decision = resolve_ttl("MAX", ttl_class, now_ms)
            expected = bucket + duration
            assert decision.expires_at_ms == expected, \
                f"{ttl_class}: expected {expected}, got {decision.expires_at_ms}"


# ============================================================================
# TEST 9: Adapter Integration Micro-Test
# ============================================================================

class Test9_AdapterIntegration:
    """Minimal test to verify adapter uses TTL policy."""
    
    def test_adapter_uses_policy_engine(self):
        """Verify adapter imports and uses TTL policy."""
        from backend.app.memory.adapter import (
            MemoryWriteRequest,
            write_memory,
            create_store,
        )
        from backend.app.memory.schema import (
            MemoryFact,
            MemoryCategory,
            MemoryValueType,
            Provenance,
            ProvenanceType,
        )
        
        # Create a valid fact
        prov = Provenance(
            source_type=ProvenanceType.USER_EXPLICIT,
            source_id="test_123",
            collected_at_ms=1000000,
            citation_ids=[],
        )
        fact = MemoryFact(
            fact_id="test_fact_001",
            category=MemoryCategory.PREFERENCES_CONSTRAINTS,
            key="test_key",
            value_type=MemoryValueType.STR,
            value_str="test value",
            value_num=None,
            value_bool=None,
            value_list_str=None,
            confidence=0.8,
            provenance=prov,
            created_at_ms=1000000,
            expires_at_ms=None,
            tags=[],
        )
        
        store = create_store()
        req = MemoryWriteRequest(
            facts=[fact],
            tier="FREE",
            now_ms=120_000,  # Bucket = 120_000
        )
        
        result = write_memory(req, store)
        
        assert result.accepted, f"Should accept, got: {result.errors}"
        assert result.ttl_applied_ms == TTL_1H, \
            f"Expected TTL_1H ({TTL_1H}), got {result.ttl_applied_ms}"


# ============================================================================
# RUNNER
# ============================================================================

def run_all():
    """Run all tests."""
    print("=" * 60)
    print("Phase 19 Step 3: TTL Policy Engine Tests")
    print("=" * 60)
    
    test_classes = [
        ("Test 1: Determinism", Test1_Determinism),
        ("Test 2: Bucket Behavior", Test2_BucketBehavior),
        ("Test 3: Plan Cap Clamp", Test3_PlanCapClamp),
        ("Test 4: Default TTL", Test4_DefaultTTL),
        ("Test 5: Invalid Inputs", Test5_InvalidInputs),
        ("Test 6: Cap Enforcement", Test6_CapEnforcement),
        ("Test 7: Policy Version", Test7_PolicyVersion),
        ("Test 8: Expiry Computation", Test8_ExpiryComputation),
        ("Test 9: Adapter Integration", Test9_AdapterIntegration),
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
        print("ALL PHASE 19 TTL POLICY TESTS PASSED ✓")
        print("=" * 60)


if __name__ == "__main__":
    run_all()
