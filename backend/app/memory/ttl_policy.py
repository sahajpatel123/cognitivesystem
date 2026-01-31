"""
Phase 19 Step 3: TTL Policy Engine (Deterministic Tiered TTL)

Implements deterministic TTL computation with:
- Plan-based caps (FREE/PRO/MAX)
- Time bucketing for deterministic expiry
- No wall-clock usage (all time from now_ms)
- Fail-closed behavior for invalid inputs
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ============================================================================
# CONSTANTS
# ============================================================================

TTL_POLICY_VERSION = "19.3.0"

REQUEST_TIME_BUCKET_MS = 60_000  # 1 minute bucket for deterministic expiries

# Duration mapping in milliseconds
TTL_1H = 3_600_000      # 1 hour
TTL_1D = 86_400_000     # 1 day
TTL_10D = 864_000_000   # 10 days


# ============================================================================
# ENUMS
# ============================================================================

class TTLClass(Enum):
    """TTL duration classes."""
    TTL_1H = "TTL_1H"
    TTL_1D = "TTL_1D"
    TTL_10D = "TTL_10D"


class PlanTier(Enum):
    """Plan tiers with TTL caps."""
    FREE = "FREE"
    PRO = "PRO"
    MAX = "MAX"


# ============================================================================
# REASON CODES (fixed set)
# ============================================================================

class ReasonCode:
    """Fixed set of reason codes for TTL decisions."""
    OK = "OK"
    CLAMPED_TO_PLAN_CAP = "CLAMPED_TO_PLAN_CAP"
    DEFAULT_APPLIED = "DEFAULT_APPLIED"
    INVALID_PLAN = "INVALID_PLAN"
    INVALID_TTL = "INVALID_TTL"
    INVALID_NOW = "INVALID_NOW"


# ============================================================================
# PLAN POLICY
# ============================================================================

# TTL class to duration mapping
TTL_DURATION_MS = {
    TTLClass.TTL_1H: TTL_1H,
    TTLClass.TTL_1D: TTL_1D,
    TTLClass.TTL_10D: TTL_10D,
}

# Plan caps (max allowed TTL class per plan)
PLAN_CAPS = {
    PlanTier.FREE: TTLClass.TTL_1H,
    PlanTier.PRO: TTLClass.TTL_1D,
    PlanTier.MAX: TTLClass.TTL_10D,
}

# Plan defaults (default TTL class per plan)
PLAN_DEFAULTS = {
    PlanTier.FREE: TTLClass.TTL_1H,
    PlanTier.PRO: TTLClass.TTL_1D,
    PlanTier.MAX: TTLClass.TTL_1D,  # NOT TTL_10D - default is not max
}

# TTL class ordering for comparison
TTL_ORDER = {
    TTLClass.TTL_1H: 0,
    TTLClass.TTL_1D: 1,
    TTLClass.TTL_10D: 2,
}


# ============================================================================
# TTL DECISION DATACLASS
# ============================================================================

@dataclass(frozen=True)
class TTLDecision:
    """
    Result of TTL policy resolution.
    
    Structure-only; no raw text.
    """
    ok: bool
    plan: str
    requested_ttl: Optional[str]
    effective_ttl: str
    expires_at_ms: int
    bucket_start_ms: int
    was_clamped: bool
    reason_code: str
    policy_version: str


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _parse_plan_tier(plan_str: str) -> Optional[PlanTier]:
    """Parse plan tier string to enum. Returns None if invalid."""
    if plan_str is None:
        return None
    try:
        return PlanTier(plan_str.upper())
    except (ValueError, AttributeError):
        return None


def _parse_ttl_class(ttl_str: Optional[str]) -> Optional[TTLClass]:
    """Parse TTL class string to enum. Returns None if invalid or None input."""
    if ttl_str is None:
        return None
    try:
        return TTLClass(ttl_str.upper())
    except (ValueError, AttributeError):
        return None


def _ttl_exceeds_cap(requested: TTLClass, cap: TTLClass) -> bool:
    """Check if requested TTL exceeds the cap."""
    return TTL_ORDER[requested] > TTL_ORDER[cap]


def _compute_bucket_start(now_ms: int) -> int:
    """Compute bucket start time (deterministic bucketing)."""
    if now_ms < 0:
        return 0
    return (now_ms // REQUEST_TIME_BUCKET_MS) * REQUEST_TIME_BUCKET_MS


# ============================================================================
# PRIMARY FUNCTION
# ============================================================================

def resolve_ttl(
    plan_tier: str,
    requested_ttl_class: Optional[str],
    now_ms: int,
) -> TTLDecision:
    """
    Resolve TTL based on plan tier and requested TTL class.
    
    Deterministic: same inputs => identical outputs.
    Fail-closed: invalid inputs produce deterministic fallback decisions.
    
    Args:
        plan_tier: Plan tier string (FREE/PRO/MAX)
        requested_ttl_class: Requested TTL class string (TTL_1H/TTL_1D/TTL_10D) or None
        now_ms: Current time in milliseconds (must be >= 0)
    
    Returns:
        TTLDecision with resolved TTL and expiry
    """
    # Validate now_ms
    if not isinstance(now_ms, int) or now_ms < 0:
        # Fail-closed: use deterministic fallback
        bucket_start = 0
        plan = PlanTier.FREE
        effective = PLAN_DEFAULTS[plan]
        expires_at = bucket_start + TTL_DURATION_MS[effective]
        
        return TTLDecision(
            ok=False,
            plan=plan.value,
            requested_ttl=requested_ttl_class,
            effective_ttl=effective.value,
            expires_at_ms=expires_at,
            bucket_start_ms=bucket_start,
            was_clamped=False,
            reason_code=ReasonCode.INVALID_NOW,
            policy_version=TTL_POLICY_VERSION,
        )
    
    # Compute bucket start
    bucket_start = _compute_bucket_start(now_ms)
    
    # Parse and validate plan tier
    plan = _parse_plan_tier(plan_tier)
    plan_invalid = plan is None
    
    if plan_invalid:
        # Fallback to FREE plan
        plan = PlanTier.FREE
    
    # Get plan cap and default
    plan_cap = PLAN_CAPS[plan]
    plan_default = PLAN_DEFAULTS[plan]
    
    # Parse requested TTL
    requested = _parse_ttl_class(requested_ttl_class)
    requested_invalid = requested_ttl_class is not None and requested is None
    
    # Determine effective TTL and reason
    was_clamped = False
    reason_code = ReasonCode.OK
    
    if plan_invalid:
        # Invalid plan takes priority
        effective = plan_default
        reason_code = ReasonCode.INVALID_PLAN
        ok = False
    elif requested_invalid:
        # Invalid TTL requested
        effective = plan_default
        reason_code = ReasonCode.INVALID_TTL
        ok = False
    elif requested is None:
        # No TTL requested, use default
        effective = plan_default
        reason_code = ReasonCode.DEFAULT_APPLIED
        ok = True
    elif _ttl_exceeds_cap(requested, plan_cap):
        # Requested exceeds cap, clamp
        effective = plan_cap
        was_clamped = True
        reason_code = ReasonCode.CLAMPED_TO_PLAN_CAP
        ok = True
    else:
        # Requested is within cap
        effective = requested
        ok = True
    
    # Compute expiry
    expires_at = bucket_start + TTL_DURATION_MS[effective]
    
    return TTLDecision(
        ok=ok,
        plan=plan.value,
        requested_ttl=requested_ttl_class,
        effective_ttl=effective.value,
        expires_at_ms=expires_at,
        bucket_start_ms=bucket_start,
        was_clamped=was_clamped,
        reason_code=reason_code,
        policy_version=TTL_POLICY_VERSION,
    )
