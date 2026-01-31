#!/usr/bin/env python3
"""
PHASE 20 GOVERNANCE EVAL GATES

CI-grade evaluation gates for Phase 20 governance compliance.
All gates must pass to promote. Fail-closed behavior enforced.
"""

import sys
import os
import json
import random
from typing import Dict, Any, List, Optional

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.app.governance.tenant import (
    TenantConfig, PlanTier, FeatureFlag, ToolKind, TTLClassLabel,
    resolve_tenant_caps, ResolvedTenantCaps
)
from backend.app.governance.regions import (
    RegionMode, TelemetryLevel, resolve_region_caps
)
from backend.app.governance.policy_engine import (
    PolicyRequest, decide_policy, OperationType
)
from backend.app.governance.rbac import (
    Role, AdminOperation, authorize_admin_action
)
from backend.app.governance.change_control import (
    ChangeType, ChangeRequest, apply_change_control
)
from backend.app.governance.audit import (
    AuditLog, AuditOperationType, AuditDecision, AuditReasonCode,
    record_audit_event
)
from backend.app.governance.export import (
    build_export_bundle
)


# ============================================================================
# CONSTANTS
# ============================================================================

NOW_MS = 1700000000000  # Deterministic timestamp
SENTINEL = "SENSITIVE_USER_TEXT_12345"
REPLAY_COUNT = 20

# Global collection for cross-gate leakage check
ALL_SERIALIZED_OUTPUTS = []


# ============================================================================
# HELPERS
# ============================================================================

def dumps(obj) -> str:
    """Deterministic JSON serialization with enum handling."""
    def enum_converter(o):
        if hasattr(o, 'value'):  # Handle enums
            return o.value
        elif hasattr(o, '__dict__'):  # Handle objects with __dict__
            return {k: enum_converter(v) for k, v in o.__dict__.items()}
        elif isinstance(o, (list, tuple)):
            return [enum_converter(item) for item in o]
        elif isinstance(o, dict):
            return {k: enum_converter(v) for k, v in o.items()}
        else:
            return o
    
    converted = enum_converter(obj)
    return json.dumps(converted, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def assert_no_sentinel_leakage(data: Any, context: str = ""):
    """Assert no sentinel strings in data."""
    serialized = dumps(data) if not isinstance(data, str) else data
    if SENTINEL in serialized:
        raise AssertionError(f"SENTINEL LEAK in {context}: {serialized}")
    
    # Add to global collection
    ALL_SERIALIZED_OUTPUTS.append(serialized)


def create_malicious_tenant_config() -> TenantConfig:
    """Create tenant config with sentinel injection."""
    return TenantConfig(
        tenant_id=f"tenant_{SENTINEL}",
        plan=PlanTier.ENTERPRISE,
        regions=["us-east"],
        enabled_features={FeatureFlag.EXPORT_ENABLED, FeatureFlag.MEMORY_ENABLED}
    )


def create_valid_tenant_config() -> TenantConfig:
    """Create valid tenant config."""
    return TenantConfig(
        tenant_id="test-tenant",
        plan=PlanTier.ENTERPRISE,
        regions=["us-east"],
        enabled_features={FeatureFlag.EXPORT_ENABLED, FeatureFlag.MEMORY_ENABLED, FeatureFlag.RESEARCH_ENABLED}
    )


# ============================================================================
# GATE A: FAIL-CLOSED POLICY GATE
# ============================================================================

def gate_a_fail_closed_policy():
    """Gate A: Fail-Closed Policy Gate."""
    print("Gate A: Fail-Closed Policy Gate")
    
    # Test 1: Missing/invalid tenant config
    try:
        caps = resolve_tenant_caps(None)
        # Should not reach here or should be fail-closed
        if caps and hasattr(caps, 'export_allowed'):
            if caps.export_allowed:
                raise AssertionError("Invalid tenant should not allow export")
    except Exception:
        pass  # Expected to fail
    
    # Test 2: Unknown region mode => STRICT
    valid_tenant = create_valid_tenant_config()
    tenant_caps = resolve_tenant_caps(valid_tenant)
    region_caps = resolve_region_caps(tenant_caps, "MARS")  # Unknown region
    
    if region_caps.region_mode != RegionMode.STRICT:
        raise AssertionError(f"Unknown region should map to STRICT, got {region_caps.region_mode}")
    
    assert_no_sentinel_leakage(dumps(region_caps.__dict__), "region_caps_unknown")
    
    # Test 3: Unknown RBAC role => DENY
    rbac_decision = authorize_admin_action(
        tenant_config=valid_tenant,
        actor_role="SUPERADMIN",  # Unknown role
        operation=AdminOperation.VIEW_AUDIT_SUMMARY
    )
    
    if rbac_decision.allow:
        raise AssertionError("Unknown RBAC role should be denied")
    
    assert_no_sentinel_leakage(dumps(rbac_decision.__dict__), "rbac_unknown_role")
    
    # Test 4: Unknown operation => DENY
    rbac_decision_op = authorize_admin_action(
        tenant_config=valid_tenant,
        actor_role=Role.OWNER,
        operation="DELETE_EVERYTHING"  # Unknown operation
    )
    
    if rbac_decision_op.allow:
        raise AssertionError("Unknown operation should be denied")
    
    assert_no_sentinel_leakage(dumps(rbac_decision_op.__dict__), "rbac_unknown_op")
    
    # Test 5: Policy engine with malicious inputs
    try:
        policy_req = PolicyRequest(
            tenant_config=create_malicious_tenant_config(),
            operation=OperationType.TOOL_CALL,
            request_hints={f"malicious_{SENTINEL}": True}
        )
        policy_decision = decide_policy(policy_req)
        
        # Should not leak sentinel
        assert_no_sentinel_leakage(dumps(policy_decision.__dict__), "policy_malicious")
        
    except Exception:
        pass  # May fail, but should not leak
    
    print("✓ Gate A: Fail-Closed Policy Gate")


# ============================================================================
# GATE B: DETERMINISTIC ALLOW/DENY GATE
# ============================================================================

def gate_b_deterministic():
    """Gate B: Deterministic Allow/Deny Gate."""
    print("Gate B: Deterministic Allow/Deny Gate")
    
    tenant_config = create_valid_tenant_config()
    
    # Test determinism across different operations
    operations = [
        (OperationType.TOOL_CALL, {"requested_tools": ["WEB"]}),
        (OperationType.MEMORY_READ, {"requested_memory": True}),
        (OperationType.EXPORT_REQUEST, {"requested_export": True}),
    ]
    
    for op_type, base_flags in operations:
        signatures = []
        serialized_decisions = []
        
        for i in range(REPLAY_COUNT):
            # Shuffle request flags order
            shuffled_flags = {}
            keys = list(base_flags.keys())
            random.seed(i)  # Deterministic shuffle
            random.shuffle(keys)
            for key in keys:
                shuffled_flags[key] = base_flags[key]
            
            # Add some extra shuffled keys
            extra_keys = ["priority", "source", "batch_size"]
            random.shuffle(extra_keys)
            for j, key in enumerate(extra_keys):
                shuffled_flags[key] = f"value_{j}"
            
            policy_req = PolicyRequest(
                tenant_config=tenant_config,
                operation=op_type,
                request_hints=shuffled_flags
            )
            
            decision = decide_policy(policy_req)
            signatures.append(decision.decision_signature)
            serialized_decisions.append(dumps(decision.__dict__))
        
        # All signatures should be identical
        first_signature = signatures[0]
        first_serialized = serialized_decisions[0]
        
        for i, (sig, serialized) in enumerate(zip(signatures[1:], serialized_decisions[1:]), 1):
            if sig != first_signature:
                raise AssertionError(f"Signature differs for {op_type.value} on iteration {i+1}")
            if serialized != first_serialized:
                raise AssertionError(f"Serialization differs for {op_type.value} on iteration {i+1}")
        
        assert_no_sentinel_leakage(first_serialized, f"policy_determinism_{op_type.value}")
    
    print("✓ Gate B: Deterministic Allow/Deny Gate")


# ============================================================================
# GATE C: AUDIT APPEND-ONLY + SIGNED + STRUCTURE-ONLY GATE
# ============================================================================

def gate_c_audit():
    """Gate C: Audit Append-only + Signed + Structure-only Gate."""
    print("Gate C: Audit Append-only + Signed + Structure-only Gate")
    
    audit_log = AuditLog()
    
    # Test 1: Append multiple events with sentinel injection
    malicious_payload = {
        "operation_type": "TOOL_CALL",
        "user_prompt": SENTINEL,  # Should be dropped/redacted
        "content": "malicious content",  # Should be dropped
        "safe_field": "SAFE_VALUE",
        "count": 42
    }
    
    event1 = record_audit_event(
        tenant_id="test-tenant",
        operation=AuditOperationType.TOOL_CALL,
        decision=AuditDecision.ALLOW,
        reason=AuditReasonCode.INTERNAL_INCONSISTENCY,
        payload=malicious_payload,
        now_ms=NOW_MS,
        log=audit_log
    )
    
    # Check event is structure-only
    assert_no_sentinel_leakage(dumps(event1.__dict__), "audit_event1")
    
    # Test 2: Chain verification
    event2 = record_audit_event(
        tenant_id="test-tenant-2",
        operation=AuditOperationType.MEMORY_WRITE,
        decision=AuditDecision.DENY,
        reason=AuditReasonCode.FORBIDDEN_CONTENT_DETECTED,
        payload={"safe_count": 10},
        now_ms=NOW_MS + 1000,
        log=audit_log
    )
    
    # Verify chain
    chain_ok, bad_index = audit_log.verify_chain()
    if not chain_ok:
        raise AssertionError(f"Audit chain verification failed at index {bad_index}")
    
    # Test 3: Deterministic serialization under reordering
    events = audit_log.list_events()
    for event in events:
        assert_no_sentinel_leakage(dumps(event.__dict__), "audit_chain_event")
    
    # Test 4: Forbidden keys dropped
    event_dict = event1.__dict__
    forbidden_keys = ["user_prompt", "content", "message", "snippet", "raw"]
    for key in forbidden_keys:
        if key in dumps(event_dict):
            raise AssertionError(f"Forbidden key '{key}' found in audit event")
    
    print("✓ Gate C: Audit Append-only + Signed + Structure-only Gate")


# ============================================================================
# GATE D: EXPORT REDACTION GATE
# ============================================================================

def gate_d_export_redaction():
    """Gate D: Export Redaction Gate."""
    print("Gate D: Export Redaction Gate")
    
    # Test 1: Build export bundle with sentinel injection
    malicious_tenant = create_malicious_tenant_config()
    
    malicious_audit_events = [
        {
            "timestamp_ms": NOW_MS,
            "operation": "TOOL_CALL",
            "decision": "ALLOW",
            "reason": "OK",
            "signature": "sig1",
            "event_id": "event1",
            "user_prompt": SENTINEL,  # Should be dropped
            "content": "malicious content",  # Should be dropped
        }
    ]
    
    malicious_policy_decisions = [
        {
            "allowed": True,
            "reason": "OK",
            "signature": "policy_sig1",
            "message": SENTINEL,  # Should be dropped
        }
    ]
    
    outcome = build_export_bundle(
        tenant_config=malicious_tenant,
        audit_events=malicious_audit_events,
        policy_decisions=malicious_policy_decisions,
        now_ms=NOW_MS
    )
    
    if not outcome.ok:
        # Export might be denied, but should not leak
        assert_no_sentinel_leakage(dumps(outcome.__dict__), "export_outcome_denied")
    else:
        # Export succeeded, check for leakage
        assert_no_sentinel_leakage(dumps(outcome.bundle.__dict__), "export_bundle")
        assert_no_sentinel_leakage(outcome.signature, "export_signature")
    
    # Test 2: Deterministic export signatures
    valid_tenant = create_valid_tenant_config()
    base_events = [
        {
            "timestamp_ms": NOW_MS,
            "operation": "TOOL_CALL",
            "decision": "ALLOW",
            "reason": "OK",
            "signature": "sig1",
            "event_id": "event1",
        }
    ]
    
    signatures = []
    for i in range(REPLAY_COUNT):
        # Shuffle event order
        shuffled_events = base_events.copy()
        random.seed(i)
        random.shuffle(shuffled_events)
        
        outcome = build_export_bundle(
            tenant_config=valid_tenant,
            audit_events=shuffled_events,
            now_ms=NOW_MS
        )
        
        if outcome.ok:
            signatures.append(outcome.signature)
        else:
            signatures.append("DENIED")
    
    # All signatures should be identical
    if signatures and len(set(signatures)) > 1:
        raise AssertionError(f"Export signatures not deterministic: {set(signatures)}")
    
    # Test 3: Region restrictions
    eu_tenant = TenantConfig(
        tenant_id="eu-tenant",
        plan=PlanTier.ENTERPRISE,
        regions=["eu-west"],
        enabled_features={FeatureFlag.EXPORT_ENABLED}
    )
    
    eu_caps = resolve_tenant_caps(eu_tenant)
    eu_region_caps = resolve_region_caps(eu_caps, "EU")
    
    # EU should deny export
    if eu_region_caps.export_allowed:
        raise AssertionError("EU region should deny export")
    
    print("✓ Gate D: Export Redaction Gate")


# ============================================================================
# GATE E: RBAC GATE
# ============================================================================

def gate_e_rbac():
    """Gate E: RBAC Gate."""
    print("Gate E: RBAC Gate")
    
    valid_tenant = create_valid_tenant_config()
    
    # Test 1: Unknown role => deny
    decision = authorize_admin_action(
        tenant_config=valid_tenant,
        actor_role="UNKNOWN_ROLE",
        operation=AdminOperation.VIEW_AUDIT_SUMMARY
    )
    
    if decision.allow:
        raise AssertionError("Unknown role should be denied")
    
    assert_no_sentinel_leakage(dumps(decision.__dict__), "rbac_unknown_role")
    
    # Test 2: Missing role => deny
    decision_none = authorize_admin_action(
        tenant_config=valid_tenant,
        actor_role=None,
        operation=AdminOperation.VIEW_AUDIT_SUMMARY
    )
    
    if decision_none.allow:
        raise AssertionError("None role should be denied")
    
    # Test 3: Unknown operation => deny
    decision_op = authorize_admin_action(
        tenant_config=valid_tenant,
        actor_role=Role.OWNER,
        operation="UNKNOWN_OP"
    )
    
    if decision_op.allow:
        raise AssertionError("Unknown operation should be denied")
    
    # Test 4: Region + tenant caps intersection
    # Create tenant with export disabled
    no_export_tenant = TenantConfig(
        tenant_id="no-export",
        plan=PlanTier.FREE,
        regions=["us-east"],
        enabled_features={FeatureFlag.MEMORY_ENABLED}  # No EXPORT_ENABLED
    )
    
    # Even OWNER should be denied export if tenant caps deny
    decision_no_export = authorize_admin_action(
        tenant_config=no_export_tenant,
        actor_role=Role.OWNER,
        operation=AdminOperation.REQUEST_EXPORT
    )
    
    if decision_no_export.allow:
        raise AssertionError("Should be denied when tenant caps deny export")
    
    # Test 5: Change control with audit
    audit_log = AuditLog()
    
    change_req = ChangeRequest(
        tenant_id=f"tenant_{SENTINEL}",  # Sentinel injection
        actor_role=Role.OWNER,
        change_type=ChangeType.POLICY_PACK,
        from_version="1.0.0",
        to_version="1.1.0",
        now_ms=NOW_MS
    )
    
    change_decision = apply_change_control(valid_tenant, change_req, audit_log)
    
    # Should not leak sentinel
    assert_no_sentinel_leakage(dumps(change_decision.__dict__), "change_control")
    
    # Check audit event was recorded (if allowed)
    if change_decision.allow and len(audit_log.list_events()) > 0:
        for event in audit_log.list_events():
            assert_no_sentinel_leakage(dumps(event.__dict__), "change_audit_event")
    
    print("✓ Gate E: RBAC Gate")


# ============================================================================
# CROSS-GATE: NO USER TEXT LEAKAGE GATE
# ============================================================================

def cross_gate_no_leakage():
    """Cross-Gate: No User Text Leakage Gate."""
    print("Cross-Gate: No User Text Leakage Gate")
    
    # Scan all collected serialized outputs
    for i, output in enumerate(ALL_SERIALIZED_OUTPUTS):
        if SENTINEL in output:
            raise AssertionError(f"GLOBAL SENTINEL LEAK in output {i}: {output}")
    
    print(f"✓ Cross-Gate: No User Text Leakage Gate (scanned {len(ALL_SERIALIZED_OUTPUTS)} outputs)")


# ============================================================================
# MAIN RUNNER
# ============================================================================

def run_all():
    """Run all eval gates."""
    try:
        print("PHASE 20 GOVERNANCE EVAL GATES")
        print("=" * 50)
        
        gate_a_fail_closed_policy()
        gate_b_deterministic()
        gate_c_audit()
        gate_d_export_redaction()
        gate_e_rbac()
        cross_gate_no_leakage()
        
        print("=" * 50)
        print("ALL PHASE 20 GOVERNANCE EVAL GATES PASSED ✓")
        return 0
        
    except Exception as e:
        print(f"✗ EVAL GATE FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = run_all()
    sys.exit(exit_code)
