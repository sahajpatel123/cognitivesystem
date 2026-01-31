"""
Phase 20 Step 9: Governance Integration Wiring (Umbrella Enforcement)

Single chokepoint for governance enforcement over Phases 16/17/18/19.
Fail-closed, deterministic, no user text leakage.

Contract guarantees:
- Governance is boss: no bypass of Phase 20 caps
- Tool calls require governance allow
- Memory writes/reads require governance allow + origin rules
- Telemetry emission requires governance clamp + sanitization
- Export/admin require governance allow (decision-only stubs)
- Deterministic outcomes for same inputs
- Structure-only outputs, no raw user text
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import json
import hashlib
import time

from backend.app.governance import (
    resolve_tenant_caps, decide_policy, record_audit_event,
    resolve_region_caps, PolicyRequest, PolicyDecision,
    ResolvedTenantCaps, RegionMode, AuditOperationType
)
from backend.app.integration.research_wiring import (
    run_policy_gated_research, ResearchPolicyDecision, ResearchOutcome
)
from backend.app.integration.memory_wiring import (
    run_policy_gated_memory_read, run_policy_gated_memory_write_from_delta,
    run_policy_gated_memory_write_from_research, MemoryPolicyDecision,
    MemoryIntegrationOutcome
)

# ============================================================================
# ENUMS AND DATACLASSES
# ============================================================================

class GovernanceOp(Enum):
    """Governance operation types (bounded set)."""
    TOOL_CALL = "TOOL_CALL"
    MEMORY_READ = "MEMORY_READ"
    MEMORY_WRITE = "MEMORY_WRITE"
    TELEMETRY_EMIT = "TELEMETRY_EMIT"
    EXPORT_REQUEST = "EXPORT_REQUEST"
    ADMIN_ACTION = "ADMIN_ACTION"

class GovernanceReason(Enum):
    """Governance decision reasons (priority order)."""
    OK = "OK"
    TENANT_MISSING = "TENANT_MISSING"
    REGION_VIOLATION = "REGION_VIOLATION"
    POLICY_DENIED = "POLICY_DENIED"
    CAPS_EXCEEDED = "CAPS_EXCEEDED"
    ORIGIN_VIOLATION = "ORIGIN_VIOLATION"
    CITATION_MISSING = "CITATION_MISSING"
    SENTINEL_DETECTED = "SENTINEL_DETECTED"
    INTERNAL_ERROR = "INTERNAL_ERROR"

@dataclass(frozen=True)
class GovernanceContext:
    """Resolved governance context (structure-only)."""
    tenant_hash: str
    region_mode: str
    caps_signature: str
    policy_version: str
    context_signature: str

@dataclass(frozen=True)
class GovernanceDecision:
    """Governance decision outcome (structure-only)."""
    allowed: bool
    reason: str
    clamps_applied: Dict[str, Any] = field(default_factory=dict)
    decision_signature: str = ""

@dataclass
class GovernanceOutcome:
    """Final governance outcome (structure-only)."""
    ok: bool
    op: str
    reason: str
    context: Optional[GovernanceContext] = None
    decision: Optional[GovernanceDecision] = None
    audit_signature: str = ""
    outcome_signature: str = ""

# ============================================================================
# CORE HELPERS
# ============================================================================

def canonical_json(obj: Any) -> str:
    """Convert object to canonical JSON string."""
    def sanitize_for_json(item):
        if hasattr(item, '__dict__'):
            return {k: sanitize_for_json(v) for k, v in item.__dict__.items()}
        elif isinstance(item, dict):
            return {k: sanitize_for_json(v) for k, v in item.items()}
        elif isinstance(item, (list, tuple)):
            return [sanitize_for_json(x) for x in item]
        elif isinstance(item, Enum):
            return item.value
        else:
            return item
    
    sanitized = sanitize_for_json(obj)
    return json.dumps(sanitized, sort_keys=True, separators=(",", ":"))

def sha256_hash(data: str) -> str:
    """Compute SHA256 hash of string."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def tenant_id_hash(tenant_id: str) -> str:
    """Hash tenant ID for structure-only output."""
    return sha256_hash(f"tenant:{tenant_id}")[:16]

def detect_sentinel(text: str) -> bool:
    """Detect sentinel strings that indicate user text leakage."""
    if not isinstance(text, str):
        return False
    upper_text = text.upper()
    return any(pattern in upper_text for pattern in [
        "SENSITIVE_", "SECRET_", "PRIVATE_", "USER_TEXT"
    ])

def sanitize_structure_only(obj: Any) -> Dict[str, Any]:
    """Sanitize object to structure-only fields."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if detect_sentinel(str(v)):
                continue  # Drop sentinel fields
            if isinstance(v, (str, int, float, bool)):
                if isinstance(v, str) and len(v) > 100:
                    result[k] = f"<truncated:{len(v)}>"
                else:
                    result[k] = v
            elif isinstance(v, (list, tuple)):
                result[k] = len(v)
            elif isinstance(v, dict):
                result[k] = sanitize_structure_only(v)
        return result
    return {"type": type(obj).__name__}

# ============================================================================
# GOVERNANCE CONTEXT RESOLUTION
# ============================================================================

def resolve_governance_context(
    tenant_id: str,
    region: str,
    now_ms: Optional[int] = None
) -> GovernanceContext:
    """
    Resolve governance context from tenant and region.
    Fail-closed on any error.
    """
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    
    try:
        # Resolve tenant caps (fail-closed)
        tenant_caps = resolve_tenant_caps(tenant_id, now_ms)
        
        # Resolve region compliance (fail-closed)
        region_compliance = resolve_region_caps(region, tenant_caps)
        
        # Build context signature
        context_data = {
            "tenant_hash": tenant_id_hash(tenant_id),
            "region": region,
            "region_mode": region_compliance.mode.value if hasattr(region_compliance, 'mode') else "STRICT",
            "caps_version": tenant_caps.version,
            "now_bucket": now_ms // 60000  # 1-minute buckets for determinism
        }
        
        context_json = canonical_json(context_data)
        context_signature = sha256_hash(context_json)[:16]
        
        return GovernanceContext(
            tenant_hash=tenant_id_hash(tenant_id),
            region_mode=region_compliance.mode.value if hasattr(region_compliance, 'mode') else "STRICT",
            caps_signature=sha256_hash(canonical_json(tenant_caps))[:16],
            policy_version="v1.0",
            context_signature=context_signature
        )
        
    except Exception as e:
        # Fail-closed context
        return GovernanceContext(
            tenant_hash="ERROR",
            region_mode="STRICT",
            caps_signature="ERROR",
            policy_version="v1.0",
            context_signature=sha256_hash("FAIL_CLOSED")[:16]
        )

# ============================================================================
# POLICY DECISION BRIDGE
# ============================================================================

def decide_governed_op(
    context: GovernanceContext,
    op: GovernanceOp,
    request_hints: Dict[str, Any],
    tenant_id: str,
    now_ms: Optional[int] = None
) -> GovernanceDecision:
    """
    Bridge to Phase 20 policy engine for governance decisions.
    Fail-closed on any error.
    """
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    
    # Fail-closed if context indicates error
    if context.tenant_hash == "ERROR":
        return GovernanceDecision(
            allowed=False,
            reason=GovernanceReason.TENANT_MISSING.value,
            decision_signature=sha256_hash("FAIL_CLOSED_TENANT")[:16]
        )
    
    try:
        # Build policy request (structure-only)
        policy_req = PolicyRequest(
            tenant_id=tenant_id,
            operation=op.value,
            request_hints=sanitize_structure_only(request_hints),
            requested={}  # No raw requested payload in signature
        )
        
        # Call policy engine
        policy_decision = decide_policy(policy_req, now_ms)
        
        # Build decision signature (no raw payload)
        decision_data = {
            "op": op.value,
            "allowed": policy_decision.allowed,
            "reason": policy_decision.reason,
            "context_sig": context.context_signature,
            "clamps": sanitize_structure_only(policy_decision.derived_limits.__dict__ if policy_decision.derived_limits else {})
        }
        
        decision_signature = sha256_hash(canonical_json(decision_data))[:16]
        
        return GovernanceDecision(
            allowed=policy_decision.allowed,
            reason=policy_decision.reason,
            clamps_applied=sanitize_structure_only(policy_decision.derived_limits.__dict__ if policy_decision.derived_limits else {}),
            decision_signature=decision_signature
        )
        
    except Exception as e:
        # Fail-closed decision
        return GovernanceDecision(
            allowed=False,
            reason=GovernanceReason.INTERNAL_ERROR.value,
            decision_signature=sha256_hash("FAIL_CLOSED_POLICY")[:16]
        )

# ============================================================================
# AUDIT INTEGRATION
# ============================================================================

def record_governance_audit(
    op: GovernanceOp,
    context: GovernanceContext,
    decision: GovernanceDecision,
    tenant_id: str
) -> str:
    """
    Record governance audit event (structure-only).
    Returns audit signature or empty string on failure.
    """
    try:
        # Structure-only audit payload
        audit_payload = {
            "op": op.value,
            "tenant_hash": context.tenant_hash,
            "allowed": decision.allowed,
            "reason": decision.reason,
            "context_sig": context.context_signature,
            "decision_sig": decision.decision_signature
        }
        
        # Record audit event
        record_audit_event(
            operation_type=AuditOperationType.GOVERNANCE_DECISION,
            tenant_id=tenant_id,
            payload=audit_payload
        )
        
        # Return audit signature
        return sha256_hash(canonical_json(audit_payload))[:16]
        
    except Exception:
        return ""  # Fail-closed audit

# ============================================================================
# TOOL CALL GOVERNANCE WRAPPER
# ============================================================================

def governed_tool_call_request(
    tenant_id: str,
    region: str,
    query: str,
    allowed_tools: List[str],
    request_flags: Dict[str, Any],
    now_ms: Optional[int] = None
) -> GovernanceOutcome:
    """
    Governance wrapper for Phase 18 tool calls.
    Enforces governance allow before calling research_wiring.
    """
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    
    # Resolve governance context
    context = resolve_governance_context(tenant_id, region, now_ms)
    
    # Check governance decision
    decision = decide_governed_op(
        context=context,
        op=GovernanceOp.TOOL_CALL,
        request_hints={"tools_count": len(allowed_tools), "query_len": len(query)},
        tenant_id=tenant_id,
        now_ms=now_ms
    )
    
    # Record audit
    audit_sig = record_governance_audit(GovernanceOp.TOOL_CALL, context, decision, tenant_id)
    
    if not decision.allowed:
        return GovernanceOutcome(
            ok=False,
            op="TOOL_CALL",
            reason=decision.reason,
            context=context,
            decision=decision,
            audit_signature=audit_sig,
            outcome_signature=sha256_hash(f"DENIED:{decision.reason}")[:16]
        )
    
    # If allowed, call Phase 18 research wiring
    try:
        research_decision = ResearchPolicyDecision(
            allowed_tools=allowed_tools,
            caps=decision.clamps_applied
        )
        
        research_outcome = run_policy_gated_research(research_decision, query, now_ms)
        
        return GovernanceOutcome(
            ok=research_outcome.ok,
            op="TOOL_CALL",
            reason=research_outcome.stop_reason,
            context=context,
            decision=decision,
            audit_signature=audit_sig,
            outcome_signature=sha256_hash(canonical_json({
                "research_sig": research_outcome.research_signature,
                "decision_sig": decision.decision_signature
            }))[:16]
        )
        
    except Exception:
        return GovernanceOutcome(
            ok=False,
            op="TOOL_CALL",
            reason=GovernanceReason.INTERNAL_ERROR.value,
            context=context,
            decision=decision,
            audit_signature=audit_sig,
            outcome_signature=sha256_hash("TOOL_CALL_ERROR")[:16]
        )

# ============================================================================
# MEMORY GOVERNANCE WRAPPERS
# ============================================================================

def governed_memory_write_request(
    tenant_id: str,
    region: str,
    facts_data: Any,
    origin: str,  # "phase17" or "phase18"
    now_ms: Optional[int] = None
) -> GovernanceOutcome:
    """
    Governance wrapper for memory writes with origin rules.
    
    Origin rules:
    - phase17: deny TOOL_CITED/DERIVED_SUMMARY provenance
    - phase18: require citation_ids non-empty for TOOL_CITED/DERIVED_SUMMARY
    """
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    
    # Resolve governance context
    context = resolve_governance_context(tenant_id, region, now_ms)
    
    # Check governance decision
    decision = decide_governed_op(
        context=context,
        op=GovernanceOp.MEMORY_WRITE,
        request_hints={"origin": origin, "facts_type": type(facts_data).__name__},
        tenant_id=tenant_id,
        now_ms=now_ms
    )
    
    # Record audit
    audit_sig = record_governance_audit(GovernanceOp.MEMORY_WRITE, context, decision, tenant_id)
    
    if not decision.allowed:
        return GovernanceOutcome(
            ok=False,
            op="MEMORY_WRITE",
            reason=decision.reason,
            context=context,
            decision=decision,
            audit_signature=audit_sig,
            outcome_signature=sha256_hash(f"DENIED:{decision.reason}")[:16]
        )
    
    # Origin-specific validation
    if origin == "phase18":
        # Validate research facts have citations
        if isinstance(facts_data, dict) and "facts" in facts_data:
            for fact in facts_data.get("facts", []):
                if isinstance(fact, dict):
                    prov = fact.get("provenance", {})
                    if isinstance(prov, dict):
                        source_type = prov.get("source_type", "")
                        citation_ids = prov.get("citation_ids", [])
                        if source_type in ["TOOL_CITED", "DERIVED_SUMMARY"] and not citation_ids:
                            return GovernanceOutcome(
                                ok=False,
                                op="MEMORY_WRITE",
                                reason=GovernanceReason.CITATION_MISSING.value,
                                context=context,
                                decision=decision,
                                audit_signature=audit_sig,
                                outcome_signature=sha256_hash("CITATION_MISSING")[:16]
                            )
    
    # Call Phase 19 memory wiring
    try:
        memory_policy = MemoryPolicyDecision(
            read_allowed=True,
            write_allowed=True,
            ttl_plan=decision.clamps_applied.get("ttl_plan", "FREE"),
            max_facts_per_request=decision.clamps_applied.get("max_facts", 8)
        )
        
        if origin == "phase17":
            memory_outcome = run_policy_gated_memory_write_from_delta(
                memory_policy, facts_data, None, now_ms
            )
        else:  # phase18
            memory_outcome = run_policy_gated_memory_write_from_research(
                memory_policy, facts_data, None, now_ms
            )
        
        return GovernanceOutcome(
            ok=memory_outcome.ok,
            op="MEMORY_WRITE",
            reason=memory_outcome.reason,
            context=context,
            decision=decision,
            audit_signature=audit_sig,
            outcome_signature=sha256_hash(canonical_json({
                "memory_sig": memory_outcome.memory_signature,
                "decision_sig": decision.decision_signature
            }))[:16]
        )
        
    except Exception:
        return GovernanceOutcome(
            ok=False,
            op="MEMORY_WRITE",
            reason=GovernanceReason.INTERNAL_ERROR.value,
            context=context,
            decision=decision,
            audit_signature=audit_sig,
            outcome_signature=sha256_hash("MEMORY_WRITE_ERROR")[:16]
        )

def governed_memory_read_request(
    tenant_id: str,
    region: str,
    read_request: Any,
    now_ms: Optional[int] = None
) -> GovernanceOutcome:
    """Governance wrapper for memory reads."""
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    
    # Resolve governance context
    context = resolve_governance_context(tenant_id, region, now_ms)
    
    # Check governance decision
    decision = decide_governed_op(
        context=context,
        op=GovernanceOp.MEMORY_READ,
        request_hints={"request_type": type(read_request).__name__},
        tenant_id=tenant_id,
        now_ms=now_ms
    )
    
    # Record audit
    audit_sig = record_governance_audit(GovernanceOp.MEMORY_READ, context, decision, tenant_id)
    
    if not decision.allowed:
        return GovernanceOutcome(
            ok=False,
            op="MEMORY_READ",
            reason=decision.reason,
            context=context,
            decision=decision,
            audit_signature=audit_sig,
            outcome_signature=sha256_hash(f"DENIED:{decision.reason}")[:16]
        )
    
    # Call Phase 19 memory wiring
    try:
        memory_policy = MemoryPolicyDecision(
            read_allowed=True,
            write_allowed=False,
            ttl_plan="FREE",
            max_facts_read=decision.clamps_applied.get("max_facts_read", 50)
        )
        
        memory_outcome = run_policy_gated_memory_read(
            memory_policy, read_request, None, now_ms
        )
        
        return GovernanceOutcome(
            ok=memory_outcome.ok,
            op="MEMORY_READ",
            reason=memory_outcome.reason,
            context=context,
            decision=decision,
            audit_signature=audit_sig,
            outcome_signature=sha256_hash(canonical_json({
                "memory_sig": memory_outcome.memory_signature,
                "decision_sig": decision.decision_signature
            }))[:16]
        )
        
    except Exception:
        return GovernanceOutcome(
            ok=False,
            op="MEMORY_READ",
            reason=GovernanceReason.INTERNAL_ERROR.value,
            context=context,
            decision=decision,
            audit_signature=audit_sig,
            outcome_signature=sha256_hash("MEMORY_READ_ERROR")[:16]
        )

# ============================================================================
# TELEMETRY GOVERNANCE WRAPPER
# ============================================================================

def governed_telemetry_emit(
    tenant_id: str,
    region: str,
    telemetry_data: Dict[str, Any],
    now_ms: Optional[int] = None
) -> GovernanceOutcome:
    """
    Governance wrapper for telemetry emission.
    Enforces region+tenant clamps and structure-only sanitization.
    """
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    
    # Resolve governance context
    context = resolve_governance_context(tenant_id, region, now_ms)
    
    # Check governance decision
    decision = decide_governed_op(
        context=context,
        op=GovernanceOp.TELEMETRY_EMIT,
        request_hints={"data_keys": len(telemetry_data), "data_size": len(str(telemetry_data))},
        tenant_id=tenant_id,
        now_ms=now_ms
    )
    
    # Record audit
    audit_sig = record_governance_audit(GovernanceOp.TELEMETRY_EMIT, context, decision, tenant_id)
    
    if not decision.allowed:
        return GovernanceOutcome(
            ok=False,
            op="TELEMETRY_EMIT",
            reason=decision.reason,
            context=context,
            decision=decision,
            audit_signature=audit_sig,
            outcome_signature=sha256_hash(f"DENIED:{decision.reason}")[:16]
        )
    
    # Sanitize telemetry data (structure-only)
    sanitized_data = sanitize_structure_only(telemetry_data)
    
    # Check for sentinel leakage
    if detect_sentinel(canonical_json(sanitized_data)):
        return GovernanceOutcome(
            ok=False,
            op="TELEMETRY_EMIT",
            reason=GovernanceReason.SENTINEL_DETECTED.value,
            context=context,
            decision=decision,
            audit_signature=audit_sig,
            outcome_signature=sha256_hash("SENTINEL_DETECTED")[:16]
        )
    
    return GovernanceOutcome(
        ok=True,
        op="TELEMETRY_EMIT",
        reason=GovernanceReason.OK.value,
        context=context,
        decision=decision,
        audit_signature=audit_sig,
        outcome_signature=sha256_hash(canonical_json({
            "sanitized_sig": sha256_hash(canonical_json(sanitized_data))[:16],
            "decision_sig": decision.decision_signature
        }))[:16]
    )

# ============================================================================
# EXPORT/ADMIN STUBS
# ============================================================================

def governed_export_request(
    tenant_id: str,
    region: str,
    export_request: Dict[str, Any],
    now_ms: Optional[int] = None
) -> GovernanceOutcome:
    """Decision-only stub for export requests."""
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    
    context = resolve_governance_context(tenant_id, region, now_ms)
    decision = decide_governed_op(
        context=context,
        op=GovernanceOp.EXPORT_REQUEST,
        request_hints={"export_type": export_request.get("type", "unknown")},
        tenant_id=tenant_id,
        now_ms=now_ms
    )
    
    audit_sig = record_governance_audit(GovernanceOp.EXPORT_REQUEST, context, decision, tenant_id)
    
    return GovernanceOutcome(
        ok=decision.allowed,
        op="EXPORT_REQUEST",
        reason=decision.reason,
        context=context,
        decision=decision,
        audit_signature=audit_sig,
        outcome_signature=sha256_hash(f"EXPORT:{decision.allowed}")[:16]
    )

def governed_admin_action(
    tenant_id: str,
    region: str,
    admin_request: Dict[str, Any],
    now_ms: Optional[int] = None
) -> GovernanceOutcome:
    """Decision-only stub for admin actions."""
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    
    context = resolve_governance_context(tenant_id, region, now_ms)
    decision = decide_governed_op(
        context=context,
        op=GovernanceOp.ADMIN_ACTION,
        request_hints={"action_type": admin_request.get("action", "unknown")},
        tenant_id=tenant_id,
        now_ms=now_ms
    )
    
    audit_sig = record_governance_audit(GovernanceOp.ADMIN_ACTION, context, decision, tenant_id)
    
    return GovernanceOutcome(
        ok=decision.allowed,
        op="ADMIN_ACTION",
        reason=decision.reason,
        context=context,
        decision=decision,
        audit_signature=audit_sig,
        outcome_signature=sha256_hash(f"ADMIN:{decision.allowed}")[:16]
    )
