"""
Phase 17 Step 1: Deterministic Pass Router

This module implements the deep-thinking pass router that decides:
- Whether deep-thinking runs
- How many passes (0-5)
- Which passes in what order
- Per-pass budget and timeout allocation

All decisions are deterministic based on allowed inputs only.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum


# Constants (deterministic)
MIN_PASS_TIMEOUT_MS = 250
MIN_BUDGET_PER_PASS = 50
MIN_PASSES_FOR_DEEPTHINK = 2
MAX_PASSES_EVER = 5

# Tier defaults
TIER_MAX_PASSES = {
    "FREE": 0,
    "PRO": 3,
    "MAX": 5,
}

TIER_DEFAULT_TIMEOUT_MS = {
    "PRO": 3000,
    "MAX": 6000,
}

TIER_DEFAULT_BUDGET = {
    "PRO": 300,
    "MAX": 600,
}

# Pass weight allocation (deterministic)
PASS_TIMEOUT_WEIGHTS = {
    "REFINE": 0.30,
    "COUNTERARG": 0.20,
    "STRESS_TEST": 0.20,
    "ALTERNATIVES": 0.15,
    "REGRET": 0.15,
}

PASS_BUDGET_WEIGHTS = {
    "REFINE": 0.30,
    "COUNTERARG": 0.20,
    "STRESS_TEST": 0.20,
    "ALTERNATIVES": 0.15,
    "REGRET": 0.15,
}

# Pass plan templates (ordered, fixed)
PASS_PLAN_TEMPLATES = {
    2: ["REFINE", "STRESS_TEST"],
    3: ["REFINE", "COUNTERARG", "STRESS_TEST"],
    4: ["REFINE", "COUNTERARG", "ALTERNATIVES", "STRESS_TEST"],
    5: ["REFINE", "COUNTERARG", "STRESS_TEST", "ALTERNATIVES", "REGRET"],
}


class StopReason(str, Enum):
    """Stop reasons from Phase 17 contract."""
    SUCCESS_COMPLETED = "SUCCESS_COMPLETED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    PASS_LIMIT_REACHED = "PASS_LIMIT_REACHED"
    TIMEOUT = "TIMEOUT"
    BREAKER_TRIPPED = "BREAKER_TRIPPED"
    ENTITLEMENT_CAP = "ENTITLEMENT_CAP"
    ABUSE = "ABUSE"
    VALIDATION_FAIL = "VALIDATION_FAIL"
    INTERNAL_INCONSISTENCY = "INTERNAL_INCONSISTENCY"


@dataclass(frozen=True)
class RouterInput:
    """
    Deterministic input to the router.
    Only allowed fields; no user text, no prompt content.
    """
    entitlement_tier: str  # FREE, PRO, MAX
    deepthink_enabled: bool  # Feature flag or tier support
    env_mode: str  # dev, staging, prod
    requested_mode: str  # "baseline" or "deep"
    breaker_tripped: bool = False
    total_budget_units: Optional[int] = None
    total_timeout_ms: Optional[int] = None
    abuse_blocked: bool = False


@dataclass
class Plan:
    """
    Router output: deterministic pass plan.
    """
    effective_pass_count: int
    pass_plan: List[str]
    per_pass_budget: List[int]
    per_pass_timeout_ms: List[int]
    stop_reason: Optional[str]  # None if deepthink enabled, set if disabled
    policy: Dict[str, Any] = field(default_factory=dict)


def build_plan(router_input: RouterInput) -> Plan:
    """
    Build a deterministic pass plan from router input.
    
    Returns Plan with:
    - effective_pass_count: 0 if disabled, 2-5 if enabled
    - pass_plan: ordered list of pass IDs
    - per_pass_budget: list aligned with pass_plan
    - per_pass_timeout_ms: list aligned with pass_plan
    - stop_reason: set if deepthink disabled, None if enabled
    - policy: safe diagnostics (no user text)
    """
    tier = router_input.entitlement_tier.upper()
    
    # HARD BLOCKS (fail-closed)
    
    # Block 1: deepthink not enabled or FREE tier
    if not router_input.deepthink_enabled or tier == "FREE":
        return _disabled_plan(StopReason.ENTITLEMENT_CAP, {"tier": tier, "deepthink_enabled": router_input.deepthink_enabled})
    
    # Block 2: breaker tripped
    if router_input.breaker_tripped:
        return _disabled_plan(StopReason.BREAKER_TRIPPED, {"breaker_tripped": True})
    
    # Block 3: abuse blocked
    if router_input.abuse_blocked:
        return _disabled_plan(StopReason.ABUSE, {"abuse_blocked": True})
    
    # Block 4: requested mode is not "deep"
    if router_input.requested_mode.lower() != "deep":
        # Per contract: we cannot invent new stop reasons.
        # Since user didn't request deep thinking, we treat this as entitlement cap
        # (conservative: deepthink only when explicitly requested)
        return _disabled_plan(StopReason.ENTITLEMENT_CAP, {"requested_mode": router_input.requested_mode})
    
    # Determine tier cap
    tier_cap = TIER_MAX_PASSES.get(tier, 0)
    if tier_cap == 0:
        return _disabled_plan(StopReason.ENTITLEMENT_CAP, {"tier": tier, "tier_cap": 0})
    
    # Determine total timeout
    total_timeout_ms = router_input.total_timeout_ms
    if total_timeout_ms is None:
        total_timeout_ms = TIER_DEFAULT_TIMEOUT_MS.get(tier, 3000)
    
    # Determine total budget
    total_budget_units = router_input.total_budget_units
    if total_budget_units is None:
        total_budget_units = TIER_DEFAULT_BUDGET.get(tier, 300)
    
    # Block 5: timeout too small for minimum passes
    if total_timeout_ms < MIN_PASSES_FOR_DEEPTHINK * MIN_PASS_TIMEOUT_MS:
        return _disabled_plan(StopReason.BUDGET_EXHAUSTED, {"total_timeout_ms": total_timeout_ms, "min_required": MIN_PASSES_FOR_DEEPTHINK * MIN_PASS_TIMEOUT_MS})
    
    # Block 6: budget too small
    if total_budget_units <= 0:
        return _disabled_plan(StopReason.BUDGET_EXHAUSTED, {"total_budget_units": total_budget_units})
    
    # Compute effective pass count with clamps
    effective_pass_count = tier_cap
    
    # Timeout clamp
    timeout_cap = total_timeout_ms // MIN_PASS_TIMEOUT_MS
    effective_pass_count = min(effective_pass_count, timeout_cap)
    
    # Budget clamp
    budget_cap = total_budget_units // MIN_BUDGET_PER_PASS
    effective_pass_count = min(effective_pass_count, budget_cap)
    
    # Enforce bounds
    if effective_pass_count < MIN_PASSES_FOR_DEEPTHINK:
        return _disabled_plan(StopReason.BUDGET_EXHAUSTED, {
            "effective_pass_count": effective_pass_count,
            "tier_cap": tier_cap,
            "timeout_cap": timeout_cap,
            "budget_cap": budget_cap,
        })
    
    # Clamp to max
    effective_pass_count = min(effective_pass_count, MAX_PASSES_EVER)
    
    # Select pass plan template
    pass_plan = PASS_PLAN_TEMPLATES.get(effective_pass_count, [])
    if not pass_plan:
        # Fallback for unexpected pass count
        return _disabled_plan(StopReason.INTERNAL_INCONSISTENCY, {"effective_pass_count": effective_pass_count})
    
    # Allocate per-pass timeouts
    per_pass_timeout_ms = _allocate_resource(
        pass_plan=pass_plan,
        total_resource=total_timeout_ms,
        weights=PASS_TIMEOUT_WEIGHTS,
        min_per_pass=MIN_PASS_TIMEOUT_MS,
    )
    
    # Allocate per-pass budgets
    per_pass_budget = _allocate_resource(
        pass_plan=pass_plan,
        total_resource=total_budget_units,
        weights=PASS_BUDGET_WEIGHTS,
        min_per_pass=MIN_BUDGET_PER_PASS,
    )
    
    # Build policy diagnostics
    policy = {
        "tier": tier,
        "tier_cap": tier_cap,
        "timeout_cap": timeout_cap,
        "budget_cap": budget_cap,
        "total_timeout_ms": total_timeout_ms,
        "total_budget_units": total_budget_units,
        "env_mode": router_input.env_mode,
    }
    
    return Plan(
        effective_pass_count=effective_pass_count,
        pass_plan=pass_plan,
        per_pass_budget=per_pass_budget,
        per_pass_timeout_ms=per_pass_timeout_ms,
        stop_reason=None,  # Deepthink enabled
        policy=policy,
    )


def _disabled_plan(stop_reason: StopReason, policy: Dict[str, Any]) -> Plan:
    """
    Return a disabled plan (effective_pass_count=0).
    """
    return Plan(
        effective_pass_count=0,
        pass_plan=[],
        per_pass_budget=[],
        per_pass_timeout_ms=[],
        stop_reason=stop_reason.value,
        policy=policy,
    )


def _allocate_resource(
    pass_plan: List[str],
    total_resource: int,
    weights: Dict[str, float],
    min_per_pass: int,
) -> List[int]:
    """
    Allocate resource (timeout or budget) deterministically across passes.
    
    Uses fixed weights, floor allocation, then distributes remainder in plan order.
    Ensures sum equals total_resource and each pass >= min_per_pass.
    """
    # Compute weighted allocation (floor)
    allocations = []
    total_weight = sum(weights.get(p, 0.0) for p in pass_plan)
    
    if total_weight == 0:
        # Fallback: equal distribution
        per_pass = total_resource // len(pass_plan)
        remainder = total_resource % len(pass_plan)
        allocations = [per_pass] * len(pass_plan)
        for i in range(remainder):
            allocations[i] += 1
        return allocations
    
    # Weighted allocation
    allocated = 0
    for pass_id in pass_plan:
        weight = weights.get(pass_id, 0.0)
        alloc = int((weight / total_weight) * total_resource)
        allocations.append(alloc)
        allocated += alloc
    
    # Distribute remainder in plan order (deterministic)
    remainder = total_resource - allocated
    for i in range(remainder):
        allocations[i % len(allocations)] += 1
    
    # Enforce minimum per pass
    for i, alloc in enumerate(allocations):
        if alloc < min_per_pass:
            # This should have been caught earlier by pass count reduction
            # But enforce here for safety
            allocations[i] = min_per_pass
    
    return allocations
