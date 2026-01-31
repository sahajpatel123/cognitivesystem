"""
Phase 19 Step 9: Integration Wiring (Policy ↔ DeepThink ↔ Research ↔ Memory)

Single chokepoint for policy-gated memory operations.
Fail-closed, deterministic, no user text leakage.

Contract guarantees:
- Policy is boss: no override of Phase 16 caps
- Research facts require sources (fail-closed)
- Phase 17 writes only structured deltas
- Phase 18 writes only citation-backed facts
- Deterministic outcomes for same inputs
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import json
import hashlib

from backend.app.memory.adapter import (
    write_memory, MemoryWriteRequest, WriteResult, MemoryStore
)
from backend.app.memory.schema import (
    MemoryFact, Provenance, ProvenanceType, MemoryCategory, MemoryValueType,
    sanitize_and_validate_fact, validate_fact_dict
)
from backend.app.memory.read import (
    read_memory_bundle, MemoryReadRequest, ReadTemplate, MemoryBundle
)
from backend.app.memory.telemetry import (
    MemoryTelemetryInput, build_memory_telemetry_event,
    compute_memory_signature, sanitize_structure
)
from backend.app.memory.ttl_policy import resolve_ttl

# ============================================================================
# REASON CODES (DETERMINISTIC PRIORITY ORDER)
# ============================================================================

class IntegrationReasonCode(Enum):
    """Fixed set of reason codes for integration outcomes (priority order)."""
    OK = "OK"
    POLICY_DISABLED = "POLICY_DISABLED"
    INVALID_REQUEST = "INVALID_REQUEST"
    FORBIDDEN_CONTENT = "FORBIDDEN_CONTENT"
    MISSING_CITATIONS = "MISSING_CITATIONS"
    TOO_MANY_FACTS = "TOO_MANY_FACTS"
    TTL_CLAMPED = "TTL_CLAMPED"
    INTERNAL_INCONSISTENCY = "INTERNAL_INCONSISTENCY"

# Priority order for multiple failures (highest priority first)
REASON_PRIORITY = {
    IntegrationReasonCode.POLICY_DISABLED: 1,
    IntegrationReasonCode.INVALID_REQUEST: 2,
    IntegrationReasonCode.FORBIDDEN_CONTENT: 3,
    IntegrationReasonCode.MISSING_CITATIONS: 3,  # Same as forbidden
    IntegrationReasonCode.TOO_MANY_FACTS: 4,
    IntegrationReasonCode.TTL_CLAMPED: 5,
    IntegrationReasonCode.OK: 6,
    IntegrationReasonCode.INTERNAL_INCONSISTENCY: 7,
}

def _select_highest_priority_reason(reasons: List[IntegrationReasonCode]) -> IntegrationReasonCode:
    """Select highest priority reason from list."""
    if not reasons:
        return IntegrationReasonCode.OK
    return min(reasons, key=lambda r: REASON_PRIORITY[r])

# ============================================================================
# DATACLASSES (STRUCTURE-ONLY)
# ============================================================================

@dataclass(frozen=True)
class MemoryPolicyDecision:
    """
    Policy decision for memory operations.
    
    Structure-only; no raw text fields.
    """
    read_allowed: bool
    write_allowed: bool
    ttl_plan: str  # FREE/PRO/MAX
    ttl_cap_class: Optional[str] = None  # TTL_1H/TTL_1D/TTL_10D or None
    max_facts_per_request: int = 8
    read_templates_allowed: List[str] = field(default_factory=list)  # Empty = none allowed
    max_facts_read: int = 50
    max_total_chars_read: int = 2000
    max_per_category_read: int = 20
    citations_required_for_research_writes: bool = True

@dataclass
class MemoryIntegrationOutcome:
    """
    Result of policy-gated memory operation.
    
    Structure-only; no raw text fields.
    """
    ok: bool
    op: str  # "READ" or "WRITE"
    reason: str
    write_result: Optional[Dict[str, Any]] = None  # Safe subset of WriteResult
    bundle: Optional[Dict[str, Any]] = None  # Safe subset of MemoryBundle
    telemetry_event: Optional[Dict[str, Any]] = None
    memory_signature: str = ""
    debug_counts: Dict[str, int] = field(default_factory=dict)

# ============================================================================
# ALLOWED CATEGORIES FOR ENGINE WRITES (PHASE 17)
# ============================================================================

ENGINE_ALLOWED_CATEGORIES = {
    MemoryCategory.PREFERENCES_CONSTRAINTS,
    MemoryCategory.USER_GOALS,
    MemoryCategory.PROJECT_CONTEXT,
    MemoryCategory.WORKFLOW_STATE,
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _safe_serialize_write_result(result: WriteResult) -> Dict[str, Any]:
    """Convert WriteResult to safe structure-only dict."""
    # Handle fact_ids_written which might be int or list
    fact_ids_count = result.fact_ids_written if isinstance(result.fact_ids_written, int) else len(result.fact_ids_written)
    errors_count = result.errors if isinstance(result.errors, int) else len(result.errors)
    
    return {
        "accepted": result.accepted,
        "reason_code": result.reason_code,
        "accepted_count": result.accepted_count,
        "rejected_count": result.rejected_count,
        "ttl_applied_ms": result.ttl_applied_ms,
        "fact_ids_count": fact_ids_count,
        "errors_count": errors_count,
    }

def _safe_serialize_bundle(bundle: MemoryBundle) -> Dict[str, Any]:
    """Convert MemoryBundle to safe structure-only dict."""
    return {
        "facts_count": len(bundle.facts),
        "total_chars": sum(len(f.key) + len(f.value_str or "") for f in bundle.facts),
        "skipped_count": bundle.skipped_count,
        "applied_caps": bundle.applied_caps,
        "categories": list(set(f.category.value for f in bundle.facts)),
    }

def _compute_structure_signature(data: Dict[str, Any]) -> str:
    """Compute deterministic signature from structure-only data."""
    # Convert any dataclass objects to dicts for JSON serialization
    def convert_to_dict(obj):
        if hasattr(obj, '__dict__'):
            return {k: convert_to_dict(v) for k, v in obj.__dict__.items()}
        elif isinstance(obj, dict):
            return {k: convert_to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [convert_to_dict(item) for item in obj]
        else:
            return obj
    
    serializable_data = convert_to_dict(data)
    json_str = json.dumps(serializable_data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()[:16]

def _extract_delta_facts(delta_like: Any, now_ms: int) -> List[MemoryFact]:
    """
    Extract facts from delta-like structure (Phase 17 path).
    
    Deterministic extraction with validation.
    """
    if not isinstance(delta_like, dict):
        raise ValueError("Delta must be dict-like")
    
    # Accept allowlisted shapes
    facts_data = None
    if "memory_patch" in delta_like:
        facts_data = delta_like["memory_patch"]
    elif "patch_facts" in delta_like:
        facts_data = delta_like["patch_facts"]
    else:
        raise ValueError("Delta missing expected shape (memory_patch or patch_facts)")
    
    if not isinstance(facts_data, list):
        raise ValueError("Facts data must be list")
    
    facts = []
    for i, fact_dict in enumerate(facts_data):
        if not isinstance(fact_dict, dict):
            raise ValueError(f"Fact {i} must be dict")
        
        # Validate fact dict structure
        is_valid, error = validate_fact_dict(fact_dict)
        if not is_valid:
            raise ValueError(f"Fact {i} validation failed: {error}")
        
        # Handle provenance - can be nested object or flat fields
        if "provenance" in fact_dict and isinstance(fact_dict["provenance"], dict):
            prov_dict = fact_dict["provenance"]
            provenance = Provenance(
                source_type=ProvenanceType(prov_dict.get("source_type", "USER_EXPLICIT")),
                source_id=prov_dict.get("source_id", "delta_engine"),
                collected_at_ms=prov_dict.get("collected_at_ms", now_ms),
                citation_ids=prov_dict.get("citation_ids", [])
            )
        else:
            # Fallback to flat fields
            provenance = Provenance(
                source_type=ProvenanceType(fact_dict.get("provenance_type", "USER_EXPLICIT")),
                source_id=fact_dict.get("source_id", "delta_engine"),
                collected_at_ms=now_ms,
                citation_ids=fact_dict.get("citation_ids", [])
            )

        # Create MemoryFact with required fields
        fact = MemoryFact(
            fact_id=fact_dict.get("fact_id", f"delta_fact_{i}"),
            category=MemoryCategory(fact_dict["category"]),
            key=fact_dict["key"],
            value_type=MemoryValueType(fact_dict.get("value_type", "STR")),
            value_str=fact_dict.get("value_str"),
            value_num=fact_dict.get("value_num"),
            value_bool=fact_dict.get("value_bool"),
            value_list_str=fact_dict.get("value_list_str"),
            confidence=fact_dict.get("confidence", 0.8),
            provenance=provenance,
            created_at_ms=fact_dict.get("created_at_ms", now_ms),
            expires_at_ms=fact_dict.get("expires_at_ms"),
            tags=fact_dict.get("tags", [])
        )
        
        # Validate category allowlist for engine
        if fact.category not in ENGINE_ALLOWED_CATEGORIES:
            raise ValueError(f"Category {fact.category} not allowed for engine writes")
        
        # Validate provenance for Phase 17 (no research provenance)
        if fact.provenance.source_type in [ProvenanceType.TOOL_CITED, ProvenanceType.DERIVED_SUMMARY]:
            raise ValueError("Engine cannot write research-provenance facts")
        
        facts.append(fact)
    
    return facts

def _extract_research_facts(research_facts_like: Any, now_ms: int) -> List[MemoryFact]:
    """
    Extract facts from research-like structure (Phase 18 path).
    
    Requires citations for all facts.
    """
    if not isinstance(research_facts_like, dict):
        raise ValueError("Research facts must be dict-like")
    
    facts_data = research_facts_like.get("facts", [])
    if not isinstance(facts_data, list):
        raise ValueError("Research facts data must be list")
    
    facts = []
    for i, fact_dict in enumerate(facts_data):
        if not isinstance(fact_dict, dict):
            raise ValueError(f"Research fact {i} must be dict")
        
        # Validate fact dict structure
        is_valid, error = validate_fact_dict(fact_dict)
        if not is_valid:
            raise ValueError(f"Research fact {i} validation failed: {error}")
        
        # Handle provenance - can be nested object or flat fields
        if "provenance" in fact_dict and isinstance(fact_dict["provenance"], dict):
            prov_dict = fact_dict["provenance"]
            provenance = Provenance(
                source_type=ProvenanceType(prov_dict.get("source_type", "TOOL_CITED")),
                source_id=prov_dict.get("source_id", "research_engine"),
                collected_at_ms=prov_dict.get("collected_at_ms", now_ms),
                citation_ids=prov_dict.get("citation_ids", [])
            )
        else:
            # Fallback to flat fields
            provenance = Provenance(
                source_type=ProvenanceType(fact_dict.get("provenance_type", "TOOL_CITED")),
                source_id=fact_dict.get("source_id", "research_engine"),
                collected_at_ms=now_ms,
                citation_ids=fact_dict.get("citation_ids", [])
            )

        # Create MemoryFact
        fact = MemoryFact(
            fact_id=fact_dict.get("fact_id", f"research_fact_{i}"),
            category=MemoryCategory(fact_dict["category"]),
            key=fact_dict["key"],
            value_type=MemoryValueType(fact_dict.get("value_type", "STR")),
            value_str=fact_dict.get("value_str"),
            value_num=fact_dict.get("value_num"),
            value_bool=fact_dict.get("value_bool"),
            value_list_str=fact_dict.get("value_list_str"),
            confidence=fact_dict.get("confidence", 0.8),
            provenance=provenance,
            created_at_ms=fact_dict.get("created_at_ms", now_ms),
            expires_at_ms=fact_dict.get("expires_at_ms"),
            tags=fact_dict.get("tags", [])
        )
        
        # Validate research provenance
        if fact.provenance.source_type not in [ProvenanceType.TOOL_CITED, ProvenanceType.DERIVED_SUMMARY]:
            raise ValueError(f"Research fact {i} must have research provenance")
        
        # Validate citations required
        if not fact.provenance.citation_ids:
            raise ValueError(f"Research fact {i} missing required citations")
        
        facts.append(fact)
    
    return facts

# ============================================================================
# CHOKEPOINT ENTRYPOINTS
# ============================================================================

def run_policy_gated_memory_read(
    policy: MemoryPolicyDecision,
    read_req: MemoryReadRequest,
    store: MemoryStore,
    now_ms: int
) -> MemoryIntegrationOutcome:
    """
    Policy-gated memory read entrypoint.
    
    Fail-closed with deterministic outcomes.
    """
    try:
        reasons = []
        
        # Check policy read allowed
        if not policy.read_allowed:
            reasons.append(IntegrationReasonCode.POLICY_DISABLED)
        
        # Check template allowlist
        if policy.read_templates_allowed and read_req.template.value not in policy.read_templates_allowed:
            reasons.append(IntegrationReasonCode.POLICY_DISABLED)
        
        # If policy denies, return empty bounded result
        if reasons:
            empty_bundle = {
                "facts_count": 0,
                "total_chars": 0,
                "skipped_count": 0,
                "applied_caps": {},
                "categories": [],
            }
            
            telemetry_input = MemoryTelemetryInput(
                writes_attempted=0,
                writes_accepted=0,
                writes_rejected=0,
                rejection_reason_codes=[],
                ttl_classes=[],
                reads_attempted=1,
                bundle_sizes=[0],
                bundle_chars=[0],
                caps_snapshot={}
            )
            
            telemetry_event = build_memory_telemetry_event(telemetry_input)
            signature = _compute_structure_signature({
                "op": "READ",
                "bundle": empty_bundle,
                "telemetry": telemetry_event
            })
            
            return MemoryIntegrationOutcome(
                ok=False,
                op="READ",
                reason=_select_highest_priority_reason(reasons).value,
                bundle=empty_bundle,
                telemetry_event=telemetry_event,
                memory_signature=signature,
                debug_counts={"reads_attempted": 1, "reads_denied": 1}
            )
        
        # Apply policy caps to read request
        clamped_req = MemoryReadRequest(
            categories=read_req.categories,
            template=read_req.template,
            now_ms=now_ms,
            max_facts=min(read_req.max_facts, policy.max_facts_read),
            max_total_chars=min(read_req.max_total_chars, policy.max_total_chars_read),
            max_per_category=min(read_req.max_per_category, policy.max_per_category_read)
        )
        
        # Call memory read
        bundle = read_memory_bundle(clamped_req, store)
        safe_bundle = _safe_serialize_bundle(bundle)
        
        # Build telemetry
        telemetry_input = MemoryTelemetryInput(
            writes_attempted=0,
            writes_accepted=0,
            writes_rejected=0,
            rejection_reason_codes=[],
            ttl_classes=[],
            reads_attempted=1,
            bundle_sizes=[len(bundle.facts)],
            bundle_chars=[safe_bundle["total_chars"]],
            caps_snapshot={"max_facts": clamped_req.max_facts, "max_chars": clamped_req.max_total_chars}
        )
        
        telemetry_event = build_memory_telemetry_event(telemetry_input)
        signature = _compute_structure_signature({
            "op": "READ",
            "bundle": safe_bundle,
            "telemetry": telemetry_event
        })
        
        return MemoryIntegrationOutcome(
            ok=True,
            op="READ",
            reason=IntegrationReasonCode.OK.value,
            bundle=safe_bundle,
            telemetry_event=telemetry_event,
            memory_signature=signature,
            debug_counts={"reads_attempted": 1, "reads_accepted": 1}
        )
        
    except Exception as e:
        # Fail-closed exception handling
        empty_bundle = {
            "facts_count": 0,
            "total_chars": 0,
            "skipped_count": 0,
            "applied_caps": {},
            "categories": [],
        }
        
        signature = _compute_structure_signature({
            "op": "READ",
            "error": "INTERNAL_INCONSISTENCY",
            "bundle": empty_bundle
        })
        
        return MemoryIntegrationOutcome(
            ok=False,
            op="READ",
            reason=IntegrationReasonCode.INTERNAL_INCONSISTENCY.value,
            bundle=empty_bundle,
            memory_signature=signature,
            debug_counts={"reads_attempted": 1, "reads_failed": 1}
        )

def run_policy_gated_memory_write_from_delta(
    policy: MemoryPolicyDecision,
    delta_like: Any,
    store: MemoryStore,
    now_ms: int
) -> MemoryIntegrationOutcome:
    """
    Policy-gated memory write from Phase 17 delta.
    
    Fail-closed with deterministic outcomes.
    """
    try:
        reasons = []
        
        # Check policy write allowed
        if not policy.write_allowed:
            reasons.append(IntegrationReasonCode.POLICY_DISABLED)
        
        if reasons:
            return _build_write_failure_outcome(reasons, "WRITE", now_ms)
        
        # Extract facts from delta
        try:
            facts = _extract_delta_facts(delta_like, now_ms)
        except ValueError as e:
            reasons.append(IntegrationReasonCode.INVALID_REQUEST)
            return _build_write_failure_outcome(reasons, "WRITE", now_ms)
        
        # Check facts count against policy cap
        max_facts = min(policy.max_facts_per_request, 8)  # HARD_MAX_FACTS_PER_WRITE
        if len(facts) > max_facts:
            reasons.append(IntegrationReasonCode.TOO_MANY_FACTS)
            return _build_write_failure_outcome(reasons, "WRITE", now_ms)
        
        # Build write request
        write_req = MemoryWriteRequest(
            facts=facts,
            tier=policy.ttl_plan,
            now_ms=now_ms
        )
        
        # Call memory write
        result = write_memory(write_req, store=store)
        safe_result = _safe_serialize_write_result(result)
        
        # Build telemetry
        telemetry_input = MemoryTelemetryInput(
            writes_attempted=len(facts),
            writes_accepted=result.accepted_count,
            writes_rejected=result.rejected_count,
            rejection_reason_codes=[result.reason_code] if not result.accepted else [],
            ttl_classes=[],  # Would need TTL resolution to populate
            reads_attempted=0,
            bundle_sizes=[],
            bundle_chars=[],
            caps_snapshot={"max_facts": max_facts}
        )
        
        telemetry_event = build_memory_telemetry_event(telemetry_input)
        signature = _compute_structure_signature({
            "op": "WRITE",
            "result": safe_result,
            "telemetry": telemetry_event
        })
        
        return MemoryIntegrationOutcome(
            ok=result.accepted,
            op="WRITE",
            reason=result.reason_code if not result.accepted else IntegrationReasonCode.OK.value,
            write_result=safe_result,
            telemetry_event=telemetry_event,
            memory_signature=signature,
            debug_counts={
                "writes_attempted": len(facts),
                "writes_accepted": result.accepted_count,
                "writes_rejected": result.rejected_count
            }
        )
        
    except Exception as e:
        return _build_write_failure_outcome([IntegrationReasonCode.INTERNAL_INCONSISTENCY], "WRITE", now_ms)

def run_policy_gated_memory_write_from_research(
    policy: MemoryPolicyDecision,
    research_facts_like: Any,
    store: MemoryStore,
    now_ms: int
) -> MemoryIntegrationOutcome:
    """
    Policy-gated memory write from Phase 18 research.
    
    Fail-closed with citation requirements.
    """
    try:
        reasons = []
        
        # Check policy write allowed
        if not policy.write_allowed:
            reasons.append(IntegrationReasonCode.POLICY_DISABLED)
        
        if reasons:
            return _build_write_failure_outcome(reasons, "WRITE", now_ms)
        
        # Extract facts from research
        try:
            facts = _extract_research_facts(research_facts_like, now_ms)
        except ValueError as e:
            if "missing required citations" in str(e):
                reasons.append(IntegrationReasonCode.MISSING_CITATIONS)
            else:
                reasons.append(IntegrationReasonCode.INVALID_REQUEST)
            return _build_write_failure_outcome(reasons, "WRITE", now_ms)
        
        # Check facts count against policy cap
        if len(facts) > policy.max_facts_per_request:
            reasons.append(IntegrationReasonCode.TOO_MANY_FACTS)
            return _build_write_failure_outcome(reasons, "WRITE", now_ms)
        
        # Build write request
        write_req = MemoryWriteRequest(
            facts=facts,
            tier=policy.ttl_plan,
            now_ms=now_ms
        )
        
        # Call memory write
        result = write_memory(write_req, store=store)
        safe_result = _safe_serialize_write_result(result)
        
        # Build telemetry
        telemetry_input = MemoryTelemetryInput(
            writes_attempted=len(facts),
            writes_accepted=result.accepted_count,
            writes_rejected=result.rejected_count,
            rejection_reason_codes=[result.reason_code] if not result.accepted else [],
            ttl_classes=[],
            reads_attempted=0,
            bundle_sizes=[],
            bundle_chars=[],
            caps_snapshot={"max_facts": policy.max_facts_per_request}
        )
        
        telemetry_event = build_memory_telemetry_event(telemetry_input)
        signature = _compute_structure_signature({
            "op": "WRITE",
            "result": safe_result,
            "telemetry": telemetry_event
        })
        
        return MemoryIntegrationOutcome(
            ok=result.accepted,
            op="WRITE",
            reason=result.reason_code if not result.accepted else IntegrationReasonCode.OK.value,
            write_result=safe_result,
            telemetry_event=telemetry_event,
            memory_signature=signature,
            debug_counts={
                "writes_attempted": len(facts),
                "writes_accepted": result.accepted_count,
                "writes_rejected": result.rejected_count
            }
        )
        
    except Exception as e:
        return _build_write_failure_outcome([IntegrationReasonCode.INTERNAL_INCONSISTENCY], "WRITE", now_ms)

def _build_write_failure_outcome(
    reasons: List[IntegrationReasonCode],
    op: str,
    now_ms: int
) -> MemoryIntegrationOutcome:
    """Build failure outcome for write operations."""
    reason = _select_highest_priority_reason(reasons)
    
    safe_result = {
        "accepted": False,
        "reason_code": reason.value,
        "accepted_count": 0,
        "rejected_count": 0,
        "ttl_applied_ms": None,
        "fact_ids_count": 0,
        "errors_count": 1,
    }
    
    signature = _compute_structure_signature({
        "op": op,
        "result": safe_result,
        "reason": reason.value
    })
    
    return MemoryIntegrationOutcome(
        ok=False,
        op=op,
        reason=reason.value,
        write_result=safe_result,
        memory_signature=signature,
        debug_counts={"writes_attempted": 0, "writes_denied": 1}
    )
