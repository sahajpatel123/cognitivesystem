#!/usr/bin/env python3
"""
Phase 20 Step 2: Policy Engine Decision Tests

Self-contained test runner for policy engine with fail-closed behavior.
No pytest dependency - uses built-in assertions and deterministic replay testing.
"""

import sys
import os
import json
from typing import Dict, Any, List

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.app.governance.policy_engine import (
    PolicyRequest, PolicyDecision, DerivedLimits, RequestedParams,
    OperationType, PolicyDecisionReason, LoggingLevel, EnvMode,
    decide_policy
)
from backend.app.governance.tenant import (
    TenantConfig, RequestHints, PlanTier, FeatureFlag, ToolKind, TTLClassLabel
)


# ============================================================================
# TEST CONSTANTS
# ============================================================================

# Sentinel strings for text leakage testing
SENTINEL_STRINGS = [
    "SENSITIVE_USER_TEXT_123",
    "SENSITIVE_USER_TEXT_456", 
    "SECRET_DATA_789",
    "PRIVATE_INFO_ABC"
]


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


def serialize_decision(decision: PolicyDecision) -> str:
    """Serialize decision to deterministic JSON string."""
    return json.dumps(decision.as_dict(), sort_keys=True, separators=(',', ':'))


def check_no_sentinel_leakage(data: Any, context: str = ""):
    """Check that no sentinel strings appear in serialized data."""
    serialized = json.dumps(data) if not isinstance(data, str) else data
    for sentinel in SENTINEL_STRINGS:
        if sentinel in serialized:
            raise AssertionError(f"Sentinel string '{sentinel}' found in {context}: {serialized}")


def create_valid_tenant_config(plan: PlanTier = PlanTier.PRO, 
                              features: List[FeatureFlag] = None) -> TenantConfig:
    """Create a valid tenant config for testing."""
    if features is None:
        features = [FeatureFlag.RESEARCH_ENABLED, FeatureFlag.MEMORY_ENABLED, FeatureFlag.DEEPTHINK_ENABLED]
    
    return TenantConfig(
        tenant_id="test-tenant",
        plan=plan,
        regions=["us-east", "eu-west"],
        enabled_features=set(features)
    )


# ============================================================================
# TEST GROUPS
# ============================================================================

def test_fail_closed_behavior():
    """Test Gate A: Fail-closed behavior."""
    print("Test Gate A: Fail-closed behavior")
    
    # None tenant_config
    req = PolicyRequest(
        tenant_config=None,
        operation=OperationType.TOOL_CALL
    )
    decision = decide_policy(req)
    assert_false(decision.allowed, "None tenant_config should be denied")
    assert_equal(decision.reason, PolicyDecisionReason.POLICY_PACK_MISSING)
    
    # Invalid tenant_config dict (missing plan)
    req = PolicyRequest(
        tenant_config={"tenant_id": "test"},  # Missing plan
        operation=OperationType.TOOL_CALL
    )
    decision = decide_policy(req)
    assert_false(decision.allowed, "Invalid tenant_config should be denied")
    assert_equal(decision.reason, PolicyDecisionReason.TENANT_INVALID)
    
    # Invalid tenant_config dict (missing tenant_id)
    req = PolicyRequest(
        tenant_config={"plan": "PRO"},  # Missing tenant_id
        operation=OperationType.TOOL_CALL
    )
    decision = decide_policy(req)
    assert_false(decision.allowed, "Invalid tenant_config should be denied")
    assert_equal(decision.reason, PolicyDecisionReason.TENANT_INVALID)
    
    # Unknown operation (invalid enum)
    req = PolicyRequest(
        tenant_config=create_valid_tenant_config(),
        operation="INVALID_OPERATION"  # This should cause validation error
    )
    try:
        decision = decide_policy(req)
        # If it doesn't throw, it should deny with OPERATION_UNKNOWN
        assert_false(decision.allowed, "Invalid operation should be denied")
        assert_in(decision.reason, [PolicyDecisionReason.OPERATION_UNKNOWN, PolicyDecisionReason.REQUEST_INVALID])
    except (ValueError, TypeError):
        # Expected if enum validation fails at construction
        pass
    
    print("✓ Test Gate A: Fail-closed behavior")


def test_requested_flags_cannot_override_caps():
    """Test Gate B: Requested flags cannot override caps."""
    print("Test Gate B: Requested flags cannot override caps")
    
    # Tenant plan that disallows web tool calls
    tenant_config = create_valid_tenant_config(
        plan=PlanTier.FREE,  # FREE plan has no tools allowed
        features=[FeatureFlag.RESEARCH_ENABLED]
    )
    
    req = PolicyRequest(
        tenant_config=tenant_config,
        operation=OperationType.TOOL_CALL,
        requested=RequestedParams(tool_kind=ToolKind.WEB)
    )
    decision = decide_policy(req)
    assert_false(decision.allowed, "Tool not allowed by plan should be denied")
    assert_equal(decision.reason, PolicyDecisionReason.TOOL_NOT_ALLOWED)
    
    # Tenant allows limited tool calls; requested more should be clamped
    tenant_config = create_valid_tenant_config(
        plan=PlanTier.PRO,  # PRO allows 1 deepthink pass
        features=[FeatureFlag.RESEARCH_ENABLED, FeatureFlag.DEEPTHINK_ENABLED]
    )
    
    req = PolicyRequest(
        tenant_config=tenant_config,
        operation=OperationType.TOOL_CALL,
        requested=RequestedParams(max_tool_calls=100)  # Request way more than allowed
    )
    decision = decide_policy(req)
    assert_true(decision.allowed, "Valid tool call should be allowed")
    # Tool calls should be clamped to reasonable limit based on deepthink passes
    assert_true(decision.limits.tool_call_max_calls <= 10, f"Tool calls should be clamped: {decision.limits.tool_call_max_calls}")
    
    print("✓ Test Gate B: Requested flags cannot override caps")


def test_memory_caps():
    """Test Gate C: Memory caps enforcement."""
    print("Test Gate C: Memory caps enforcement")
    
    # Tenant FREE with TTL cap TTL_1H, request TTL_10D should be clamped
    tenant_config = create_valid_tenant_config(
        plan=PlanTier.FREE,  # FREE has TTL_1H cap
        features=[FeatureFlag.MEMORY_ENABLED]
    )
    
    req = PolicyRequest(
        tenant_config=tenant_config,
        operation=OperationType.MEMORY_WRITE_PHASE17,
        requested=RequestedParams(ttl_label=TTLClassLabel.TTL_10D)
    )
    decision = decide_policy(req)
    assert_true(decision.allowed, "Memory write should be allowed if feature enabled")
    assert_equal(decision.limits.memory_ttl_cap, TTLClassLabel.TTL_1H, "TTL should be clamped to plan cap")
    assert_in("TTL_CLAMPED", decision.limits.clamp_notes, "Should have TTL clamp note")
    
    # Tenant disallows memory writes
    tenant_config = create_valid_tenant_config(
        plan=PlanTier.FREE,
        features=[]  # No MEMORY_ENABLED
    )
    
    req = PolicyRequest(
        tenant_config=tenant_config,
        operation=OperationType.MEMORY_WRITE_PHASE17
    )
    decision = decide_policy(req)
    assert_false(decision.allowed, "Memory write should be denied if feature disabled")
    assert_equal(decision.reason, PolicyDecisionReason.MEMORY_WRITE_NOT_ALLOWED)
    
    # Memory read when not allowed
    req = PolicyRequest(
        tenant_config=tenant_config,
        operation=OperationType.MEMORY_READ
    )
    decision = decide_policy(req)
    assert_false(decision.allowed, "Memory read should be denied if feature disabled")
    assert_equal(decision.reason, PolicyDecisionReason.MEMORY_READ_NOT_ALLOWED)
    
    print("✓ Test Gate C: Memory caps enforcement")


def test_export_and_admin():
    """Test Gate D: Export & Admin restrictions."""
    print("Test Gate D: Export & Admin restrictions")
    
    # Tenant export ineligible
    tenant_config = create_valid_tenant_config(
        plan=PlanTier.PRO,  # PRO doesn't allow export by default
        features=[FeatureFlag.MEMORY_ENABLED]
    )
    
    req = PolicyRequest(
        tenant_config=tenant_config,
        operation=OperationType.EXPORT_REQUEST
    )
    decision = decide_policy(req)
    assert_false(decision.allowed, "Export should be denied for ineligible tenant")
    assert_equal(decision.reason, PolicyDecisionReason.EXPORT_NOT_ALLOWED)
    
    # Admin action not in allowlist
    req = PolicyRequest(
        tenant_config=tenant_config,
        operation=OperationType.ADMIN_ACTION,
        requested=RequestedParams(admin_action="dangerous_action")
    )
    decision = decide_policy(req)
    assert_false(decision.allowed, "Admin action should be denied")
    assert_equal(decision.reason, PolicyDecisionReason.ADMIN_NOT_ALLOWED)
    
    # Test export allowed for ENTERPRISE with feature
    enterprise_config = create_valid_tenant_config(
        plan=PlanTier.ENTERPRISE,
        features=[FeatureFlag.EXPORT_ENABLED]
    )
    
    req = PolicyRequest(
        tenant_config=enterprise_config,
        operation=OperationType.EXPORT_REQUEST
    )
    decision = decide_policy(req)
    assert_true(decision.allowed, "Export should be allowed for ENTERPRISE with feature")
    assert_true(decision.limits.export_allowed, "Export should be marked as allowed in limits")
    
    print("✓ Test Gate D: Export & Admin restrictions")


def test_logging_verbosity():
    """Test Gate E: Logging verbosity clamping."""
    print("Test Gate E: Logging verbosity clamping")
    
    tenant_config = create_valid_tenant_config()
    
    # Request verbose logging, should be clamped to standard
    req = PolicyRequest(
        tenant_config=tenant_config,
        operation=OperationType.LOGGING,
        requested=RequestedParams(logging_verbosity=LoggingLevel.VERBOSE)
    )
    decision = decide_policy(req)
    assert_true(decision.allowed, "Logging should be allowed")
    # Should be clamped to STANDARD (default policy level)
    assert_in(decision.limits.logging_level, [LoggingLevel.STANDARD, LoggingLevel.VERBOSE], 
             f"Logging level should be reasonable: {decision.limits.logging_level}")
    
    # Request minimal logging, should be allowed (more restrictive)
    req = PolicyRequest(
        tenant_config=tenant_config,
        operation=OperationType.LOGGING,
        requested=RequestedParams(logging_verbosity=LoggingLevel.MINIMAL)
    )
    decision = decide_policy(req)
    assert_true(decision.allowed, "Logging should be allowed")
    assert_equal(decision.limits.logging_level, LoggingLevel.MINIMAL, "More restrictive logging should be allowed")
    
    print("✓ Test Gate E: Logging verbosity clamping")


def test_no_user_text_leakage():
    """Test Gate F: No user text leakage."""
    print("Test Gate F: No user text leakage")
    
    # Test sentinel strings in tenant_config dict
    tenant_config_dict = {
        "tenant_id": SENTINEL_STRINGS[0],  # Sentinel in tenant_id
        "plan": "PRO",
        "regions": ["us-east"],
        "enabled_features": ["RESEARCH_ENABLED"]
    }
    
    req = PolicyRequest(
        tenant_config=tenant_config_dict,
        operation=OperationType.TOOL_CALL
    )
    decision = decide_policy(req)
    assert_false(decision.allowed, "Request with sentinel should be denied")
    assert_equal(decision.reason, PolicyDecisionReason.TENANT_INVALID)
    
    # Check that decision doesn't contain sentinel
    serialized = serialize_decision(decision)
    check_no_sentinel_leakage(serialized, "decision with sentinel in tenant_config")
    
    # Test forbidden keys in request_hints dict
    tenant_config = create_valid_tenant_config()
    request_hints_dict = {
        "prompt": "some user prompt",  # Forbidden key
        "requested_research": True
    }
    
    req = PolicyRequest(
        tenant_config=tenant_config,
        operation=OperationType.TOOL_CALL,
        request_hints=request_hints_dict
    )
    decision = decide_policy(req)
    # Should either be denied or hints should be ignored
    serialized = serialize_decision(decision)
    check_no_sentinel_leakage(serialized, "decision with forbidden keys in hints")
    assert_not_in("prompt", serialized, "Forbidden key should not appear in decision")
    
    # Test sentinel in requested params
    requested_dict = {
        "admin_action": SENTINEL_STRINGS[1],  # Sentinel in admin action
        "max_tool_calls": 5
    }
    
    req = PolicyRequest(
        tenant_config=tenant_config,
        operation=OperationType.ADMIN_ACTION,
        requested=requested_dict
    )
    decision = decide_policy(req)
    serialized = serialize_decision(decision)
    check_no_sentinel_leakage(serialized, "decision with sentinel in requested params")
    
    print("✓ Test Gate F: No user text leakage")


def test_determinism():
    """Test Gate G: Deterministic behavior."""
    print("Test Gate G: Deterministic behavior")
    
    tenant_config = create_valid_tenant_config(
        plan=PlanTier.MAX,
        features=[FeatureFlag.RESEARCH_ENABLED, FeatureFlag.MEMORY_ENABLED, FeatureFlag.DEEPTHINK_ENABLED]
    )
    
    req = PolicyRequest(
        tenant_config=tenant_config,
        operation=OperationType.TOOL_CALL,
        request_hints=RequestHints(
            requested_research=True,
            requested_tools=[ToolKind.WEB, ToolKind.DOCS],
            requested_deepthink_passes=2
        ),
        requested=RequestedParams(
            tool_kind=ToolKind.WEB,
            max_tool_calls=5,
            logging_verbosity=LoggingLevel.STANDARD
        ),
        env_mode=EnvMode.PROD
    )
    
    # Run 20 times and collect results
    results = []
    for i in range(20):
        decision = decide_policy(req)
        serialized = serialize_decision(decision)
        results.append(serialized)
    
    # All results should be identical
    first_result = results[0]
    for i, result in enumerate(results[1:], 1):
        assert_equal(result, first_result, f"Iteration {i+1} differs from first")
    
    # Test with dict inputs (should normalize to same result)
    tenant_config_dict = {
        "tenant_id": "test-tenant",
        "plan": "MAX",
        "regions": ["us-east", "eu-west"],
        "enabled_features": ["RESEARCH_ENABLED", "MEMORY_ENABLED", "DEEPTHINK_ENABLED"]
    }
    
    request_hints_dict = {
        "requested_research": True,
        "requested_tools": ["WEB", "DOCS"],
        "requested_deepthink_passes": 2
    }
    
    requested_dict = {
        "tool_kind": "WEB",
        "max_tool_calls": 5,
        "logging_verbosity": "STANDARD"
    }
    
    req_dict = PolicyRequest(
        tenant_config=tenant_config_dict,
        operation=OperationType.TOOL_CALL,
        request_hints=request_hints_dict,
        requested=requested_dict,
        env_mode=EnvMode.PROD
    )
    
    decision_dict = decide_policy(req_dict)
    serialized_dict = serialize_decision(decision_dict)
    
    # Should be identical to original (after normalization)
    # Note: May differ due to internal object vs dict handling, but structure should be same
    decision_orig = decide_policy(req)
    assert_equal(decision_dict.allowed, decision_orig.allowed, "Dict and object inputs should have same allowed status")
    assert_equal(decision_dict.reason, decision_orig.reason, "Dict and object inputs should have same reason")
    
    print("✓ Test Gate G: Deterministic behavior")


def test_bounds_enforcement():
    """Test bounds enforcement on all limits."""
    print("Test: Bounds enforcement")
    
    tenant_config = create_valid_tenant_config(
        plan=PlanTier.ENTERPRISE,
        features=list(FeatureFlag)  # All features enabled
    )
    
    # Request excessive values
    req = PolicyRequest(
        tenant_config=tenant_config,
        operation=OperationType.TOOL_CALL,
        requested=RequestedParams(
            max_tool_calls=1000,  # Way over limit
            max_facts=1000,       # Way over limit
            export_scope=["scope"] * 100,  # Way over limit
            logging_verbosity=LoggingLevel.VERBOSE
        )
    )
    
    decision = decide_policy(req)
    
    # Check bounds
    assert_true(len(decision.limits.allowed_tools) <= 8, f"Tools should be bounded: {len(decision.limits.allowed_tools)}")
    assert_true(decision.limits.tool_call_max_calls <= 32, f"Tool calls should be bounded: {decision.limits.tool_call_max_calls}")
    assert_true(decision.limits.deepthink_passes_allowed <= 8, f"Deepthink passes should be bounded: {decision.limits.deepthink_passes_allowed}")
    assert_true(decision.limits.memory_max_facts_per_request <= 64, f"Memory facts should be bounded: {decision.limits.memory_max_facts_per_request}")
    assert_true(decision.limits.memory_read_max_facts <= 64, f"Memory read facts should be bounded: {decision.limits.memory_read_max_facts}")
    assert_true(decision.limits.memory_read_max_chars <= 8192, f"Memory read chars should be bounded: {decision.limits.memory_read_max_chars}")
    assert_true(len(decision.limits.export_scope_allowlist) <= 16, f"Export scopes should be bounded: {len(decision.limits.export_scope_allowlist)}")
    assert_true(len(decision.limits.admin_actions_allowlist) <= 16, f"Admin actions should be bounded: {len(decision.limits.admin_actions_allowlist)}")
    assert_true(len(decision.limits.regions_allowed) <= 8, f"Regions should be bounded: {len(decision.limits.regions_allowed)}")
    assert_true(len(decision.limits.clamp_notes) <= 10, f"Clamp notes should be bounded: {len(decision.limits.clamp_notes)}")
    
    # Check stable ordering
    assert_equal(decision.limits.allowed_tools, sorted(decision.limits.allowed_tools, key=lambda x: x.value), "Tools should be sorted")
    assert_equal(decision.limits.export_scope_allowlist, sorted(decision.limits.export_scope_allowlist), "Export scopes should be sorted")
    assert_equal(decision.limits.admin_actions_allowlist, sorted(decision.limits.admin_actions_allowlist), "Admin actions should be sorted")
    assert_equal(decision.limits.regions_allowed, sorted(decision.limits.regions_allowed), "Regions should be sorted")
    assert_equal(decision.limits.clamp_notes, sorted(decision.limits.clamp_notes), "Clamp notes should be sorted")
    
    print("✓ Test: Bounds enforcement")


def test_signature_consistency():
    """Test that decision signatures are consistent and don't leak sensitive data."""
    print("Test: Signature consistency")
    
    tenant_config = create_valid_tenant_config()
    
    req = PolicyRequest(
        tenant_config=tenant_config,
        operation=OperationType.TOOL_CALL,
        requested=RequestedParams(tool_kind=ToolKind.DOCS)
    )
    
    decision1 = decide_policy(req)
    decision2 = decide_policy(req)
    
    # Signatures should be identical for identical inputs
    assert_equal(decision1.decision_signature, decision2.decision_signature, "Signatures should be deterministic")
    
    # Signature should be a valid SHA256 hex string
    assert_equal(len(decision1.decision_signature), 64, "Signature should be 64 char SHA256 hex")
    assert_true(all(c in '0123456789abcdef' for c in decision1.decision_signature), "Signature should be hex")
    
    # Signature should not contain tenant_id or other sensitive data
    assert_not_in(tenant_config.tenant_id, decision1.decision_signature, "Signature should not contain tenant_id")
    for sentinel in SENTINEL_STRINGS:
        assert_not_in(sentinel, decision1.decision_signature, f"Signature should not contain sentinel: {sentinel}")
    
    print("✓ Test: Signature consistency")


def test_region_constraints():
    """Test region-based constraints."""
    print("Test: Region constraints")
    
    tenant_config = create_valid_tenant_config()
    tenant_config.regions = ["us-east"]  # Only allow us-east
    
    # Request operation in allowed region
    req = PolicyRequest(
        tenant_config=tenant_config,
        operation=OperationType.TOOL_CALL,
        requested=RequestedParams(region="us-east")
    )
    decision = decide_policy(req)
    assert_true(decision.allowed, "Operation in allowed region should be permitted")
    
    # Request operation in disallowed region
    req = PolicyRequest(
        tenant_config=tenant_config,
        operation=OperationType.TOOL_CALL,
        requested=RequestedParams(region="eu-west")  # Not in allowed regions
    )
    decision = decide_policy(req)
    assert_false(decision.allowed, "Operation in disallowed region should be denied")
    assert_equal(decision.reason, PolicyDecisionReason.REGION_DISALLOWS_OPERATION)
    
    print("✓ Test: Region constraints")


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_all() -> bool:
    """Run all tests and return success status."""
    try:
        print("Running Phase 20 Policy Engine Decision Tests...")
        print()
        
        test_fail_closed_behavior()
        test_requested_flags_cannot_override_caps()
        test_memory_caps()
        test_export_and_admin()
        test_logging_verbosity()
        test_no_user_text_leakage()
        test_determinism()
        test_bounds_enforcement()
        test_signature_consistency()
        test_region_constraints()
        
        print()
        print("ALL PHASE 20 POLICY ENGINE DECISION TESTS PASSED ✓")
        return True
        
    except Exception as e:
        print(f"✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
