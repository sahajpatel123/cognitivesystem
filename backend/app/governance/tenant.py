"""
Phase 20 Step 1: Tenant Boundary + Capability Matrix

Implements tenant configuration, capability resolution, and request hint validation
with fail-closed behavior and deterministic clamping.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Set, Tuple
import re


# ============================================================================
# ENUMS
# ============================================================================

class PlanTier(Enum):
    """Tenant plan tiers with explicit capability mappings."""
    FREE = "FREE"
    PRO = "PRO"
    MAX = "MAX"
    ENTERPRISE = "ENTERPRISE"


class FeatureFlag(Enum):
    """Feature flags that can be enabled/disabled per tenant."""
    RESEARCH_ENABLED = "RESEARCH_ENABLED"
    DEEPTHINK_ENABLED = "DEEPTHINK_ENABLED"
    MEMORY_ENABLED = "MEMORY_ENABLED"
    EXPORT_ENABLED = "EXPORT_ENABLED"
    AUDIT_ENABLED = "AUDIT_ENABLED"


class ToolKind(Enum):
    """Available tool types for research operations."""
    WEB = "WEB"
    DOCS = "DOCS"
    NONE = "NONE"


class TTLClassLabel(Enum):
    """Memory TTL class labels aligned with Phase 19 policy."""
    TTL_1H = "TTL_1H"
    TTL_1D = "TTL_1D"
    TTL_10D = "TTL_10D"


class TenantStopReason(Enum):
    """Exhaustive list of tenant capability stop reasons."""
    TENANT_INVALID_CONFIG = "TENANT_INVALID_CONFIG"
    TENANT_FEATURE_DISABLED = "TENANT_FEATURE_DISABLED"
    TENANT_TOOL_NOT_ALLOWED = "TENANT_TOOL_NOT_ALLOWED"
    TENANT_DEEPTHINK_NOT_ALLOWED = "TENANT_DEEPTHINK_NOT_ALLOWED"
    TENANT_EXPORT_NOT_ALLOWED = "TENANT_EXPORT_NOT_ALLOWED"
    TENANT_TTL_CLAMPED = "TENANT_TTL_CLAMPED"
    TENANT_PASSES_CLAMPED = "TENANT_PASSES_CLAMPED"
    TENANT_REQUEST_IGNORED = "TENANT_REQUEST_IGNORED"


# ============================================================================
# POLICY CONSTANTS
# ============================================================================

# Tools allowed by plan tier
PLAN_TOOLS = {
    PlanTier.FREE: (),
    PlanTier.PRO: (ToolKind.DOCS,),
    PlanTier.MAX: (ToolKind.DOCS, ToolKind.WEB),
    PlanTier.ENTERPRISE: (ToolKind.DOCS, ToolKind.WEB),
}

# DeepThink max passes by plan tier
PLAN_DEEPTHINK_PASSES = {
    PlanTier.FREE: 0,
    PlanTier.PRO: 1,
    PlanTier.MAX: 3,
    PlanTier.ENTERPRISE: 4,
}

# Memory TTL caps by plan tier (aligned with Phase 19)
PLAN_MEMORY_TTL_CAP = {
    PlanTier.FREE: TTLClassLabel.TTL_1H,
    PlanTier.PRO: TTLClassLabel.TTL_1D,
    PlanTier.MAX: TTLClassLabel.TTL_10D,
    PlanTier.ENTERPRISE: TTLClassLabel.TTL_10D,
}

# Memory max facts per request by plan tier
PLAN_MEMORY_MAX_FACTS = {
    PlanTier.FREE: 8,
    PlanTier.PRO: 16,
    PlanTier.MAX: 24,
    PlanTier.ENTERPRISE: 32,
}

# Export eligibility by plan tier
PLAN_EXPORT_DEFAULT = {
    PlanTier.FREE: False,
    PlanTier.PRO: False,
    PlanTier.MAX: False,
    PlanTier.ENTERPRISE: True,  # Still requires EXPORT_ENABLED feature flag
}

# TTL class hierarchy for clamping (lower index = more restrictive)
TTL_HIERARCHY = [TTLClassLabel.TTL_1H, TTLClassLabel.TTL_1D, TTLClassLabel.TTL_10D]

# Validation patterns
TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,80}$")
REGION_PATTERN = re.compile(r"^[a-z0-9_-]{2,32}$")

# Bounds
MAX_REGIONS = 8
MAX_FEATURES = 16
MAX_TOOLS = 8
MAX_STOP_REASONS = 10
MAX_CLAMP_NOTES = 10


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class TenantConfig:
    """Tenant configuration with plan, regions, and feature flags."""
    tenant_id: str
    plan: PlanTier
    regions: List[str] = field(default_factory=list)
    enabled_features: Set[FeatureFlag] = field(default_factory=set)


@dataclass
class RequestHints:
    """Request hints that must NOT override tenant caps."""
    requested_research: bool = False
    requested_tools: List[ToolKind] = field(default_factory=list)
    requested_deepthink_passes: Optional[int] = None
    requested_ttl_class: Optional[TTLClassLabel] = None
    requested_export: bool = False


@dataclass
class ResolvedTenantCaps:
    """Resolved tenant capabilities with deterministic structure-only fields."""
    tenant_id: str
    plan: PlanTier
    research_allowed: bool
    allowed_tools: Tuple[ToolKind, ...]
    deepthink_max_passes: int
    memory_ttl_cap: TTLClassLabel
    memory_max_facts_per_request: int
    export_allowed: bool
    stop_reasons: Tuple[str, ...]
    clamp_notes: Tuple[str, ...]

    def as_dict(self) -> dict:
        """Convert to dictionary with stable key ordering."""
        return {
            "tenant_id": self.tenant_id,
            "plan": self.plan.value,
            "research_allowed": self.research_allowed,
            "allowed_tools": [tool.value for tool in sorted(self.allowed_tools, key=lambda x: x.value)],
            "deepthink_max_passes": self.deepthink_max_passes,
            "memory_ttl_cap": self.memory_ttl_cap.value,
            "memory_max_facts_per_request": self.memory_max_facts_per_request,
            "export_allowed": self.export_allowed,
            "stop_reasons": sorted(self.stop_reasons),
            "clamp_notes": sorted(self.clamp_notes),
        }


# ============================================================================
# VALIDATION AND NORMALIZATION
# ============================================================================

def validate_tenant_config(cfg: TenantConfig) -> Tuple[bool, List[str]]:
    """Validate tenant configuration with deterministic error ordering."""
    errors = []
    
    # Validate tenant_id
    if not cfg.tenant_id:
        errors.append("tenant_id cannot be empty")
    elif not TENANT_ID_PATTERN.match(cfg.tenant_id):
        errors.append("tenant_id must be 1-80 chars, alphanumeric, underscore, or dash")
    
    # Validate plan
    if not isinstance(cfg.plan, PlanTier):
        errors.append("plan must be a valid PlanTier")
    
    # Validate regions
    if len(cfg.regions) > MAX_REGIONS:
        errors.append(f"regions cannot exceed {MAX_REGIONS}")
    
    for region in cfg.regions:
        if not isinstance(region, str):
            errors.append("all regions must be strings")
            break
        if not REGION_PATTERN.match(region):
            errors.append(f"region '{region}' must be 2-32 chars, lowercase alphanumeric, underscore, or dash")
    
    # Validate enabled_features
    if len(cfg.enabled_features) > MAX_FEATURES:
        errors.append(f"enabled_features cannot exceed {MAX_FEATURES}")
    
    for feature in cfg.enabled_features:
        if not isinstance(feature, FeatureFlag):
            errors.append("all enabled_features must be valid FeatureFlag")
            break
    
    return len(errors) == 0, sorted(errors)


def normalize_tenant_config(cfg: TenantConfig) -> TenantConfig:
    """Normalize tenant configuration with deterministic ordering."""
    # Normalize regions: lowercase, dedupe, sort
    normalized_regions = sorted(list(set(region.lower().strip() for region in cfg.regions if region.strip())))
    
    # Ensure enabled_features is a set (already deterministic when iterated in sorted order)
    normalized_features = set(cfg.enabled_features)
    
    return TenantConfig(
        tenant_id=cfg.tenant_id.strip(),
        plan=cfg.plan,
        regions=normalized_regions,
        enabled_features=normalized_features
    )


def validate_request_hints(hints: RequestHints) -> Tuple[bool, List[str]]:
    """Validate request hints with deterministic error ordering."""
    errors = []
    
    # Validate requested_tools
    if len(hints.requested_tools) > MAX_TOOLS:
        errors.append(f"requested_tools cannot exceed {MAX_TOOLS}")
    
    for tool in hints.requested_tools:
        if not isinstance(tool, ToolKind):
            errors.append("all requested_tools must be valid ToolKind")
            break
    
    # Validate requested_deepthink_passes
    if hints.requested_deepthink_passes is not None:
        if not isinstance(hints.requested_deepthink_passes, int) or hints.requested_deepthink_passes < 0:
            errors.append("requested_deepthink_passes must be non-negative integer")
        elif hints.requested_deepthink_passes > 100:  # Reasonable upper bound
            errors.append("requested_deepthink_passes exceeds reasonable limit")
    
    # Validate requested_ttl_class
    if hints.requested_ttl_class is not None and not isinstance(hints.requested_ttl_class, TTLClassLabel):
        errors.append("requested_ttl_class must be valid TTLClassLabel")
    
    return len(errors) == 0, sorted(errors)


# ============================================================================
# CAPABILITY RESOLUTION
# ============================================================================

def _clamp_ttl_class(requested: Optional[TTLClassLabel], cap: TTLClassLabel) -> Tuple[TTLClassLabel, bool]:
    """Clamp requested TTL class to plan cap. Returns (clamped_value, was_clamped)."""
    if requested is None:
        return cap, False
    
    requested_idx = TTL_HIERARCHY.index(requested)
    cap_idx = TTL_HIERARCHY.index(cap)
    
    if requested_idx > cap_idx:
        return cap, True
    return requested, False


def _filter_allowed_tools(requested: List[ToolKind], allowed: Tuple[ToolKind, ...]) -> Tuple[Tuple[ToolKind, ...], bool]:
    """Filter requested tools to only allowed ones. Returns (filtered_tools, had_disallowed)."""
    allowed_set = set(allowed)
    filtered = tuple(sorted((tool for tool in requested if tool in allowed_set), key=lambda x: x.value))
    had_disallowed = len(requested) > len(filtered)
    return filtered, had_disallowed


def resolve_tenant_caps(cfg: TenantConfig, hints: Optional[RequestHints] = None) -> ResolvedTenantCaps:
    """
    Resolve tenant capabilities with fail-closed behavior and request hint clamping.
    
    Critical: requested flags must NEVER override tenant caps.
    """
    stop_reasons = []
    clamp_notes = []
    
    # Validate and normalize config
    config_valid, config_errors = validate_tenant_config(cfg)
    if not config_valid:
        # Fail-closed: return minimal caps with sanitized output (no user data leakage)
        safe_tenant_id = "INVALID"
        if cfg.tenant_id and isinstance(cfg.tenant_id, str) and len(cfg.tenant_id) <= 80:
            # Only include tenant_id if it's reasonable length and doesn't contain sentinel patterns
            has_sentinel = any(sentinel in cfg.tenant_id for sentinel in ["SENSITIVE_", "SECRET_", "PRIVATE_"])
            if not has_sentinel:
                safe_tenant_id = cfg.tenant_id
        
        # Sanitize error messages to remove any potential user data
        safe_errors = []
        for error in config_errors[:MAX_CLAMP_NOTES]:
            # Replace any potential sensitive data with generic messages
            if any(sentinel in error for sentinel in ["SENSITIVE_", "SECRET_", "PRIVATE_"]):
                safe_errors.append("VALIDATION_ERROR")
            else:
                safe_errors.append(error)
        
        return ResolvedTenantCaps(
            tenant_id=safe_tenant_id,
            plan=cfg.plan if isinstance(cfg.plan, PlanTier) else PlanTier.FREE,
            research_allowed=False,
            allowed_tools=(),
            deepthink_max_passes=0,
            memory_ttl_cap=TTLClassLabel.TTL_1H,
            memory_max_facts_per_request=0,
            export_allowed=False,
            stop_reasons=(TenantStopReason.TENANT_INVALID_CONFIG.value,),
            clamp_notes=tuple(safe_errors)
        )
    
    cfg = normalize_tenant_config(cfg)
    
    # Validate hints if provided
    if hints is not None:
        hints_valid, hints_errors = validate_request_hints(hints)
        if not hints_valid:
            stop_reasons.extend([TenantStopReason.TENANT_REQUEST_IGNORED.value])
            clamp_notes.extend(hints_errors[:MAX_CLAMP_NOTES])
            hints = None  # Ignore invalid hints
    
    # Get base capabilities from plan
    plan_tools = PLAN_TOOLS[cfg.plan]
    plan_deepthink_passes = PLAN_DEEPTHINK_PASSES[cfg.plan]
    plan_ttl_cap = PLAN_MEMORY_TTL_CAP[cfg.plan]
    plan_max_facts = PLAN_MEMORY_MAX_FACTS[cfg.plan]
    plan_export_default = PLAN_EXPORT_DEFAULT[cfg.plan]
    
    # Apply feature flag gating
    research_allowed = FeatureFlag.RESEARCH_ENABLED in cfg.enabled_features
    deepthink_allowed = FeatureFlag.DEEPTHINK_ENABLED in cfg.enabled_features
    memory_allowed = FeatureFlag.MEMORY_ENABLED in cfg.enabled_features
    export_feature_enabled = FeatureFlag.EXPORT_ENABLED in cfg.enabled_features
    
    # Resolve capabilities
    if not research_allowed:
        allowed_tools = ()
        if hints and (hints.requested_research or hints.requested_tools):
            stop_reasons.append(TenantStopReason.TENANT_FEATURE_DISABLED.value)
    else:
        allowed_tools = plan_tools
    
    if not deepthink_allowed:
        deepthink_max_passes = 0
        if hints and hints.requested_deepthink_passes and hints.requested_deepthink_passes > 0:
            stop_reasons.append(TenantStopReason.TENANT_DEEPTHINK_NOT_ALLOWED.value)
    else:
        deepthink_max_passes = plan_deepthink_passes
    
    if not memory_allowed:
        memory_max_facts_per_request = 0
        # TTL cap still returned for consistency, but integration layer will deny
    else:
        memory_max_facts_per_request = plan_max_facts
    
    export_allowed = plan_export_default and export_feature_enabled
    
    # Process request hints (clamping only, never expanding)
    if hints is not None:
        # Handle tool requests
        if hints.requested_tools and research_allowed:
            filtered_tools, had_disallowed = _filter_allowed_tools(hints.requested_tools, allowed_tools)
            if had_disallowed:
                stop_reasons.append(TenantStopReason.TENANT_TOOL_NOT_ALLOWED.value)
            # Note: We keep plan-based allowed_tools, not filtered requested tools
            # This ensures tenant caps are never expanded by requests
        
        # Handle deepthink pass requests
        if hints.requested_deepthink_passes is not None and deepthink_allowed:
            if hints.requested_deepthink_passes > deepthink_max_passes:
                stop_reasons.append(TenantStopReason.TENANT_PASSES_CLAMPED.value)
                clamp_notes.append("DEEPTHINK_CLAMPED")
        
        # Handle TTL requests
        if hints.requested_ttl_class is not None:
            clamped_ttl, was_clamped = _clamp_ttl_class(hints.requested_ttl_class, plan_ttl_cap)
            if was_clamped:
                stop_reasons.append(TenantStopReason.TENANT_TTL_CLAMPED.value)
                clamp_notes.append("TTL_CLAMPED")
        
        # Handle export requests
        if hints.requested_export and not export_allowed:
            stop_reasons.append(TenantStopReason.TENANT_EXPORT_NOT_ALLOWED.value)
    
    # Ensure deterministic ordering and bounds
    stop_reasons = tuple(sorted(set(stop_reasons))[:MAX_STOP_REASONS])
    clamp_notes = tuple(sorted(set(clamp_notes))[:MAX_CLAMP_NOTES])
    allowed_tools = tuple(sorted(allowed_tools, key=lambda x: x.value))
    
    return ResolvedTenantCaps(
        tenant_id=cfg.tenant_id,
        plan=cfg.plan,
        research_allowed=research_allowed,
        allowed_tools=allowed_tools,
        deepthink_max_passes=deepthink_max_passes,
        memory_ttl_cap=plan_ttl_cap,
        memory_max_facts_per_request=memory_max_facts_per_request,
        export_allowed=export_allowed,
        stop_reasons=stop_reasons,
        clamp_notes=clamp_notes
    )
