"""
Phase 19 Step 2: Memory Write Boundary (Single Chokepoint)

Every memory write MUST go through this adapter.
Deterministic, fail-closed, no raw user text.

Contract guarantees:
- Single entrypoint: write_memory()
- Allowlist categories enforced
- Provenance rules enforced
- TTL clamp (tier-based)
- Max facts per write enforced
- Fail-closed on any error
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from backend.app.memory.schema import (
    MemoryFact,
    MemoryCategory,
    MemoryValueType,
    Provenance,
    ProvenanceType,
    sanitize_and_validate_fact,
    validate_fact_dict,
)
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
)
from backend.app.memory.safety_filter import (
    scan_facts_forbidden,
    ForbiddenReason,
)

# ============================================================================
# CONSTANTS
# ============================================================================

HARD_MAX_FACTS_PER_WRITE = 8
MAX_REQUEST_ID_LEN = 64
MAX_ERRORS_RETURNED = 20

# TTL bounds (milliseconds)
ONE_HOUR_MS = 60 * 60 * 1000
ONE_DAY_MS = 24 * ONE_HOUR_MS
TEN_DAYS_MS = 10 * ONE_DAY_MS
ONE_YEAR_MS = 365 * ONE_DAY_MS


# ============================================================================
# REASON CODES (fixed set)
# ============================================================================

class ReasonCode(Enum):
    """Fixed set of reason codes for write results."""
    OK = "OK"
    TTL_CLAMPED = "TTL_CLAMPED"
    POLICY_DISABLED = "POLICY_DISABLED"
    REQUEST_INVALID = "REQUEST_INVALID"
    FORBIDDEN_CATEGORY = "FORBIDDEN_CATEGORY"
    FORBIDDEN_CONTENT_DETECTED = "FORBIDDEN_CONTENT_DETECTED"
    PROVENANCE_INVALID = "PROVENANCE_INVALID"
    TOO_MANY_FACTS = "TOO_MANY_FACTS"
    TTL_INVALID = "TTL_INVALID"
    VALIDATION_FAIL = "VALIDATION_FAIL"
    INTERNAL_INCONSISTENCY = "INTERNAL_INCONSISTENCY"


# Priority order for reason codes (highest first)
REASON_PRIORITY = [
    ReasonCode.REQUEST_INVALID,
    ReasonCode.TOO_MANY_FACTS,
    ReasonCode.FORBIDDEN_CATEGORY,
    ReasonCode.FORBIDDEN_CONTENT_DETECTED,
    ReasonCode.PROVENANCE_INVALID,
    ReasonCode.TTL_INVALID,
    ReasonCode.VALIDATION_FAIL,
    ReasonCode.INTERNAL_INCONSISTENCY,
]


# ============================================================================
# TIER CAPS (versioned constant)
# ============================================================================

class Tier(Enum):
    """Tier levels for memory entitlements."""
    FREE = "FREE"
    PRO = "PRO"
    MAX = "MAX"


@dataclass(frozen=True)
class TierCaps:
    """TTL caps for a tier."""
    max_ttl_ms: int
    default_ttl_ms: int


TIER_CAPS: Dict[Tier, TierCaps] = {
    Tier.FREE: TierCaps(max_ttl_ms=ONE_HOUR_MS, default_ttl_ms=ONE_HOUR_MS),
    Tier.PRO: TierCaps(max_ttl_ms=ONE_DAY_MS, default_ttl_ms=ONE_DAY_MS),
    Tier.MAX: TierCaps(max_ttl_ms=TEN_DAYS_MS, default_ttl_ms=ONE_DAY_MS),
}


# ============================================================================
# ALLOWED CATEGORIES (adapter-level allowlist)
# ============================================================================

ALLOWED_CATEGORIES = frozenset([
    MemoryCategory.PREFERENCES_CONSTRAINTS,
    MemoryCategory.USER_GOALS,
    MemoryCategory.PROJECT_CONTEXT,
    MemoryCategory.WORKFLOW_STATE,
])


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class MemoryWriteRequest:
    """
    Request to write memory facts.
    
    All fields bounded. No raw user text fields.
    """
    facts: List[MemoryFact]
    tier: str
    now_ms: int
    requested_ttl_ms: Optional[int] = None
    max_facts_per_write: int = HARD_MAX_FACTS_PER_WRITE
    provenance_required: bool = True
    request_id: Optional[str] = None


@dataclass
class WriteResult:
    """
    Result of a memory write operation.
    
    Deterministic, stable ordering.
    """
    accepted: bool
    reason_code: str
    accepted_count: int
    rejected_count: int
    ttl_applied_ms: Optional[int]
    fact_ids_written: List[str]
    errors: List[str]


# ============================================================================
# IN-MEMORY STORE STUB
# ============================================================================

class MemoryStore:
    """
    In-memory store stub for memory facts.
    
    This is the ONLY place where facts are stored.
    All writes MUST go through the adapter.
    """
    
    def __init__(self):
        self._facts: Dict[str, MemoryFact] = {}
        self._ttls: Dict[str, int] = {}  # fact_id -> expires_at_ms
    
    def write_facts(
        self,
        facts: List[MemoryFact],
        ttl_applied_ms: int,
        now_ms: int,
    ) -> List[str]:
        """
        Write facts to store (legacy method for backwards compatibility).
        
        Returns list of fact_ids written (stable order).
        """
        fact_ids = []
        expires_at_ms = now_ms + ttl_applied_ms
        
        for fact in facts:
            self._facts[fact.fact_id] = fact
            self._ttls[fact.fact_id] = expires_at_ms
            fact_ids.append(fact.fact_id)
        
        return fact_ids
    
    def write_facts_with_expiry(
        self,
        facts: List[MemoryFact],
        expires_at_ms: int,
    ) -> List[str]:
        """
        Write facts to store with pre-computed bucketed expiry.
        
        This is the preferred method as it uses deterministic bucketed expiry
        from the TTL policy engine.
        
        Returns list of fact_ids written (stable order).
        """
        fact_ids = []
        
        for fact in facts:
            self._facts[fact.fact_id] = fact
            self._ttls[fact.fact_id] = expires_at_ms
            fact_ids.append(fact.fact_id)
        
        return fact_ids
    
    def get_fact(self, fact_id: str) -> Optional[MemoryFact]:
        """Get a fact by ID."""
        return self._facts.get(fact_id)
    
    def count(self) -> int:
        """Get total fact count."""
        return len(self._facts)


# Default global store (can be overridden in tests)
_default_store = MemoryStore()


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def _parse_tier(tier_str: str) -> Tuple[Optional[Tier], Optional[str]]:
    """
    Parse tier string to Tier enum.
    
    Returns (tier, error) - one will be None.
    """
    try:
        return (Tier(tier_str.upper()), None)
    except (ValueError, AttributeError):
        return (None, "INVALID_TIER")


def _validate_request(req: MemoryWriteRequest) -> List[str]:
    """
    Validate request-level fields.
    
    Returns list of error codes.
    """
    errors = []
    
    # Validate tier
    tier, tier_error = _parse_tier(req.tier)
    if tier_error:
        errors.append(tier_error)
    
    # Validate max_facts_per_write
    if req.max_facts_per_write < 1:
        errors.append("MAX_FACTS_INVALID")
    
    # Validate now_ms
    if req.now_ms < 0:
        errors.append("NOW_MS_INVALID")
    
    # Validate request_id bounds
    if req.request_id and len(req.request_id) > MAX_REQUEST_ID_LEN:
        errors.append("REQUEST_ID_TOO_LONG")
    
    # Validate facts list exists
    if req.facts is None:
        errors.append("FACTS_MISSING")
    
    return sorted(errors)


def _validate_category(fact: MemoryFact) -> Optional[str]:
    """
    Validate fact category against allowlist.
    
    Returns error code or None.
    """
    if fact.category not in ALLOWED_CATEGORIES:
        return "CATEGORY_NOT_ALLOWED"
    return None


def _validate_provenance(fact: MemoryFact, provenance_required: bool) -> List[str]:
    """
    Validate provenance rules.
    
    Returns list of error codes.
    """
    errors = []
    
    if fact.provenance is None:
        if provenance_required:
            errors.append("PROVENANCE_MISSING")
        return errors
    
    prov = fact.provenance
    
    # Validate source_type
    if prov.source_type is None:
        errors.append("SOURCE_TYPE_MISSING")
        return errors
    
    # TOOL_CITED must have citation_ids
    if prov.source_type == ProvenanceType.TOOL_CITED:
        if not prov.citation_ids or len(prov.citation_ids) == 0:
            errors.append("TOOL_CITED_NO_CITATIONS")
    
    # DERIVED_SUMMARY: no source -> don't store
    if prov.source_type == ProvenanceType.DERIVED_SUMMARY:
        if not prov.citation_ids or len(prov.citation_ids) == 0:
            errors.append("DERIVED_NO_SOURCE")
    
    return sorted(errors)


def _ms_to_ttl_class(ttl_ms: Optional[int]) -> Optional[str]:
    """
    Convert TTL milliseconds to TTL class string.
    
    Returns TTL class string or None if no mapping.
    """
    if ttl_ms is None:
        return None
    
    # Map to nearest TTL class (round up)
    if ttl_ms <= TTL_1H:
        return TTLClass.TTL_1H.value
    elif ttl_ms <= TTL_1D:
        return TTLClass.TTL_1D.value
    else:
        return TTLClass.TTL_10D.value


def _compute_ttl_via_policy(
    requested_ttl_ms: Optional[int],
    tier: Tier,
    now_ms: int,
) -> Tuple[int, int, bool, Optional[str], str]:
    """
    Compute TTL using the TTL policy engine.
    
    Returns (ttl_applied_ms, expires_at_ms, was_clamped, error_code, reason_code).
    """
    # Convert requested TTL ms to TTL class
    requested_ttl_class = _ms_to_ttl_class(requested_ttl_ms)
    
    # Resolve via policy engine
    decision = resolve_ttl(
        plan_tier=tier.value,
        requested_ttl_class=requested_ttl_class,
        now_ms=now_ms,
    )
    
    # Map effective TTL class back to ms
    ttl_class_to_ms = {
        TTLClass.TTL_1H.value: TTL_1H,
        TTLClass.TTL_1D.value: TTL_1D,
        TTLClass.TTL_10D.value: TTL_10D,
    }
    ttl_applied_ms = ttl_class_to_ms.get(decision.effective_ttl, TTL_1H)
    
    # Check for errors
    if not decision.ok:
        if decision.reason_code == TTLReasonCode.INVALID_NOW:
            return (0, 0, False, "NOW_MS_INVALID", decision.reason_code)
        elif decision.reason_code == TTLReasonCode.INVALID_TTL:
            return (0, 0, False, "TTL_INVALID", decision.reason_code)
        # For INVALID_PLAN, we still get a fallback decision
        # Continue with the fallback values
    
    return (
        ttl_applied_ms,
        decision.expires_at_ms,
        decision.was_clamped,
        None,
        decision.reason_code,
    )


# ============================================================================
# MAIN ENTRYPOINT
# ============================================================================

def write_memory(
    req: MemoryWriteRequest,
    store: Optional[MemoryStore] = None,
) -> WriteResult:
    """
    Single entrypoint for all memory writes.
    
    Deterministic, fail-closed, stable ordering.
    
    Args:
        req: Memory write request
        store: Optional store (uses default if None)
    
    Returns:
        WriteResult with acceptance status and details
    """
    try:
        # Use default store if not provided
        if store is None:
            store = _default_store
        
        all_errors: List[str] = []
        
        # ================================================================
        # 1) Validate request-level fields
        # ================================================================
        request_errors = _validate_request(req)
        if request_errors:
            return WriteResult(
                accepted=False,
                reason_code=ReasonCode.REQUEST_INVALID.value,
                accepted_count=0,
                rejected_count=len(req.facts) if req.facts else 0,
                ttl_applied_ms=None,
                fact_ids_written=[],
                errors=request_errors[:MAX_ERRORS_RETURNED],
            )
        
        # Parse tier (already validated above)
        tier, _ = _parse_tier(req.tier)
        if tier is None:
            return WriteResult(
                accepted=False,
                reason_code=ReasonCode.POLICY_DISABLED.value,
                accepted_count=0,
                rejected_count=len(req.facts) if req.facts else 0,
                ttl_applied_ms=None,
                fact_ids_written=[],
                errors=["INVALID_TIER"],
            )
        
        # ================================================================
        # 2) Validate facts count
        # ================================================================
        effective_max = min(req.max_facts_per_write, HARD_MAX_FACTS_PER_WRITE)
        
        if len(req.facts) > effective_max:
            return WriteResult(
                accepted=False,
                reason_code=ReasonCode.TOO_MANY_FACTS.value,
                accepted_count=0,
                rejected_count=len(req.facts),
                ttl_applied_ms=None,
                fact_ids_written=[],
                errors=[f"FACTS_COUNT_{len(req.facts)}_EXCEEDS_MAX_{effective_max}"],
            )
        
        if len(req.facts) == 0:
            return WriteResult(
                accepted=False,
                reason_code=ReasonCode.REQUEST_INVALID.value,
                accepted_count=0,
                rejected_count=0,
                ttl_applied_ms=None,
                fact_ids_written=[],
                errors=["FACTS_EMPTY"],
            )
        
        # ================================================================
        # 3) Compute TTL via policy engine
        # ================================================================
        ttl_applied_ms, expires_at_ms, was_clamped, ttl_error, ttl_reason = _compute_ttl_via_policy(
            req.requested_ttl_ms, tier, req.now_ms
        )
        
        if ttl_error:
            return WriteResult(
                accepted=False,
                reason_code=ReasonCode.TTL_INVALID.value,
                accepted_count=0,
                rejected_count=len(req.facts),
                ttl_applied_ms=None,
                fact_ids_written=[],
                errors=[ttl_error],
            )
        
        # ================================================================
        # 4) Validate each fact
        # ================================================================
        validated_facts: List[MemoryFact] = []
        fact_errors: List[str] = []
        category_errors: List[str] = []
        provenance_errors: List[str] = []
        validation_errors: List[str] = []
        
        for i, fact in enumerate(req.facts):
            prefix = f"FACT_{i}"
            
            # Category check
            cat_error = _validate_category(fact)
            if cat_error:
                category_errors.append(f"{prefix}_{cat_error}")
                continue
            
            # Provenance check
            prov_errors = _validate_provenance(fact, req.provenance_required)
            if prov_errors:
                for pe in prov_errors:
                    provenance_errors.append(f"{prefix}_{pe}")
                continue
            
            # Schema validation (sanitize + validate)
            sanitized_fact, schema_errors = sanitize_and_validate_fact(fact)
            if sanitized_fact is None:
                for se in schema_errors:
                    # Truncate error to avoid leaking text
                    short_error = se.split(":")[0] if ":" in se else se
                    validation_errors.append(f"{prefix}_{short_error}")
                continue
            
            validated_facts.append(sanitized_fact)
        
        # ================================================================
        # 5) Determine result based on errors (priority order)
        # ================================================================
        
        # Check for category errors first
        if category_errors:
            all_errors.extend(sorted(category_errors))
            return WriteResult(
                accepted=False,
                reason_code=ReasonCode.FORBIDDEN_CATEGORY.value,
                accepted_count=0,
                rejected_count=len(req.facts),
                ttl_applied_ms=None,
                fact_ids_written=[],
                errors=sorted(all_errors)[:MAX_ERRORS_RETURNED],
            )
        
        # Check for provenance errors
        if provenance_errors:
            all_errors.extend(sorted(provenance_errors))
            return WriteResult(
                accepted=False,
                reason_code=ReasonCode.PROVENANCE_INVALID.value,
                accepted_count=0,
                rejected_count=len(req.facts),
                ttl_applied_ms=None,
                fact_ids_written=[],
                errors=sorted(all_errors)[:MAX_ERRORS_RETURNED],
            )
        
        # Check for validation errors
        if validation_errors:
            all_errors.extend(sorted(validation_errors))
            return WriteResult(
                accepted=False,
                reason_code=ReasonCode.VALIDATION_FAIL.value,
                accepted_count=0,
                rejected_count=len(req.facts),
                ttl_applied_ms=None,
                fact_ids_written=[],
                errors=sorted(all_errors)[:MAX_ERRORS_RETURNED],
            )
        
        # ================================================================
        # 6) Safety filter check (after validation, before store write)
        # ================================================================
        safety_result = scan_facts_forbidden(validated_facts)
        if safety_result.forbidden:
            # Map forbidden reason to error code
            safety_error = f"SAFETY_FILTER_{safety_result.top_reason.value if safety_result.top_reason else 'UNKNOWN'}"
            
            return WriteResult(
                accepted=False,
                reason_code=ReasonCode.FORBIDDEN_CONTENT_DETECTED.value,
                accepted_count=0,
                rejected_count=len(req.facts),
                ttl_applied_ms=None,
                fact_ids_written=[],
                errors=[safety_error],
            )
        
        # ================================================================
        # 7) Write to store (using bucketed expiry from policy engine)
        # ================================================================
        fact_ids_written = store.write_facts_with_expiry(validated_facts, expires_at_ms)
        
        # Determine final reason code
        reason_code = ReasonCode.TTL_CLAMPED.value if was_clamped else ReasonCode.OK.value
        
        return WriteResult(
            accepted=True,
            reason_code=reason_code,
            accepted_count=len(validated_facts),
            rejected_count=len(req.facts) - len(validated_facts),
            ttl_applied_ms=ttl_applied_ms,
            fact_ids_written=fact_ids_written,
            errors=[],
        )
    
    except Exception:
        # Fail-closed
        return WriteResult(
            accepted=False,
            reason_code=ReasonCode.INTERNAL_INCONSISTENCY.value,
            accepted_count=0,
            rejected_count=len(req.facts) if req and req.facts else 0,
            ttl_applied_ms=None,
            fact_ids_written=[],
            errors=["INTERNAL_ERROR"],
        )


def create_store() -> MemoryStore:
    """Create a new memory store instance."""
    return MemoryStore()
