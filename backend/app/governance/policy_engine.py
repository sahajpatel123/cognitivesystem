"""
Phase 20 Step 2: Policy Engine (Single Chokepoint)

Implements deterministic policy decisions with fail-closed behavior.
Every sensitive action gets an explicit policy decision with structure-only output.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Union, Any
import json
import hashlib
import re

from .tenant import (
    TenantConfig, RequestHints, ResolvedTenantCaps, ToolKind, TTLClassLabel,
    resolve_tenant_caps, validate_tenant_config, PlanTier, FeatureFlag
)


# ============================================================================
# ENUMS
# ============================================================================

class OperationType(Enum):
    """Exhaustive list of operations requiring policy decisions."""
    TOOL_CALL = "TOOL_CALL"
    MEMORY_READ = "MEMORY_READ"
    MEMORY_WRITE_PHASE17 = "MEMORY_WRITE_PHASE17"
    MEMORY_WRITE_PHASE18 = "MEMORY_WRITE_PHASE18"
    LOGGING = "LOGGING"
    EXPORT_REQUEST = "EXPORT_REQUEST"
    ADMIN_ACTION = "ADMIN_ACTION"


class PolicyDecisionReason(Enum):
    """Exhaustive list of policy decision reasons. NO OTHER."""
    POLICY_PACK_MISSING = "POLICY_PACK_MISSING"
    TENANT_INVALID = "TENANT_INVALID"
    CAPS_RESOLUTION_FAILED = "CAPS_RESOLUTION_FAILED"
    OPERATION_UNKNOWN = "OPERATION_UNKNOWN"
    FEATURE_DISABLED = "FEATURE_DISABLED"
    PLAN_DISALLOWS_OPERATION = "PLAN_DISALLOWS_OPERATION"
    REGION_DISALLOWS_OPERATION = "REGION_DISALLOWS_OPERATION"
    TOOL_NOT_ALLOWED = "TOOL_NOT_ALLOWED"
    MEMORY_READ_NOT_ALLOWED = "MEMORY_READ_NOT_ALLOWED"
    MEMORY_WRITE_NOT_ALLOWED = "MEMORY_WRITE_NOT_ALLOWED"
    EXPORT_NOT_ALLOWED = "EXPORT_NOT_ALLOWED"
    ADMIN_NOT_ALLOWED = "ADMIN_NOT_ALLOWED"
    LIMITS_CLAMPED = "LIMITS_CLAMPED"
    REQUEST_INVALID = "REQUEST_INVALID"
    INTERNAL_INCONSISTENCY = "INTERNAL_INCONSISTENCY"
    ALLOWED = "ALLOWED"


class LoggingLevel(Enum):
    """Allowed logging verbosity levels."""
    MINIMAL = "MINIMAL"
    STANDARD = "STANDARD"
    VERBOSE = "VERBOSE"


class EnvMode(Enum):
    """Environment modes for policy decisions."""
    PROD = "prod"
    STAGING = "staging"
    DEV = "dev"


# ============================================================================
# CONSTANTS AND BOUNDS
# ============================================================================

# Forbidden keys that indicate user text leakage
FORBIDDEN_KEYS = frozenset([
    "user_text", "prompt", "answer", "rationale", "message", "content",
    "quote", "snippet", "transcript", "input", "output", "response",
    "request", "query", "search", "term", "phrase", "sentence",
    "paragraph", "document", "file", "path", "filename", "forbidden",
    "forbidden_field", "malicious", "sensitive", "secret", "private",
    "conversation", "chat", "dialog", "dialogue"
])

# Forbidden substrings that indicate sentinel patterns
FORBIDDEN_SUBSTRINGS = ["SENSITIVE_", "SECRET_", "PRIVATE_"]

# Bounds
MAX_TOOLS = 8
MAX_TOOL_CALLS = 32
MAX_DEEPTHINK_PASSES = 8
MAX_MEMORY_FACTS = 64
MAX_MEMORY_CHARS = 8192
MAX_EXPORT_SCOPES = 16
MAX_ADMIN_ACTIONS = 16
MAX_REGIONS = 8
MAX_CLAMP_NOTES = 10
MAX_STRING_LENGTH = 128

# Default timeouts and limits
DEFAULT_TOOL_TIMEOUT_MS = 30000
DEFAULT_MEMORY_READ_MAX_FACTS = 32
DEFAULT_MEMORY_READ_MAX_CHARS = 4096


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class RequestedParams:
    """Optional requested parameters (advisory only - can be clamped down)."""
    tool_kind: Optional[ToolKind] = None
    ttl_label: Optional[TTLClassLabel] = None
    logging_verbosity: Optional[LoggingLevel] = None
    export_scope: Optional[List[str]] = None
    admin_action: Optional[str] = None
    max_tool_calls: Optional[int] = None
    max_facts: Optional[int] = None
    region: Optional[str] = None


@dataclass
class PolicyRequest:
    """Policy decision request with structure-only fields."""
    tenant_config: Union[TenantConfig, Dict[str, Any]]
    operation: OperationType
    request_hints: Optional[Union[RequestHints, Dict[str, Any]]] = None
    requested: Optional[Union[RequestedParams, Dict[str, Any]]] = None
    env_mode: EnvMode = EnvMode.PROD
    now_ms: Optional[int] = None


@dataclass
class DerivedLimits:
    """Derived limits from policy decision with deterministic structure."""
    allowed_tools: List[ToolKind] = field(default_factory=list)
    tool_call_max_calls: int = 0
    tool_call_timeout_ms: int = DEFAULT_TOOL_TIMEOUT_MS
    deepthink_passes_allowed: int = 0
    memory_read_allowed: bool = False
    memory_write_phase17_allowed: bool = False
    memory_write_phase18_allowed: bool = False
    memory_ttl_cap: TTLClassLabel = TTLClassLabel.TTL_1H
    memory_max_facts_per_request: int = 0
    memory_read_max_facts: int = DEFAULT_MEMORY_READ_MAX_FACTS
    memory_read_max_chars: int = DEFAULT_MEMORY_READ_MAX_CHARS
    export_allowed: bool = False
    export_scope_allowlist: List[str] = field(default_factory=list)
    logging_level: LoggingLevel = LoggingLevel.MINIMAL
    admin_actions_allowlist: List[str] = field(default_factory=list)
    regions_allowed: List[str] = field(default_factory=list)
    clamp_notes: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with stable ordering."""
        return {
            "allowed_tools": [tool.value for tool in sorted(self.allowed_tools, key=lambda x: x.value)],
            "tool_call_max_calls": self.tool_call_max_calls,
            "tool_call_timeout_ms": self.tool_call_timeout_ms,
            "deepthink_passes_allowed": self.deepthink_passes_allowed,
            "memory_read_allowed": self.memory_read_allowed,
            "memory_write_phase17_allowed": self.memory_write_phase17_allowed,
            "memory_write_phase18_allowed": self.memory_write_phase18_allowed,
            "memory_ttl_cap": self.memory_ttl_cap.value,
            "memory_max_facts_per_request": self.memory_max_facts_per_request,
            "memory_read_max_facts": self.memory_read_max_facts,
            "memory_read_max_chars": self.memory_read_max_chars,
            "export_allowed": self.export_allowed,
            "export_scope_allowlist": sorted(self.export_scope_allowlist),
            "logging_level": self.logging_level.value,
            "admin_actions_allowlist": sorted(self.admin_actions_allowlist),
            "regions_allowed": sorted(self.regions_allowed),
            "clamp_notes": sorted(self.clamp_notes),
        }


@dataclass
class PolicyDecision:
    """Policy decision with deterministic signature."""
    allowed: bool
    reason: PolicyDecisionReason
    limits: DerivedLimits
    decision_signature: str
    model_version: str = "20.2.0"

    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with stable ordering."""
        return {
            "allowed": self.allowed,
            "reason": self.reason.value,
            "limits": self.limits.as_dict(),
            "decision_signature": self.decision_signature,
            "model_version": self.model_version,
        }


# ============================================================================
# SANITIZATION AND VALIDATION
# ============================================================================

def _sanitize_dict(data: Dict[str, Any], context: str) -> bool:
    """
    Check if dict contains forbidden keys or sentinel patterns.
    Returns True if safe, False if contains forbidden content.
    """
    if not isinstance(data, dict):
        return True
    
    # Check for forbidden keys
    for key in data.keys():
        if isinstance(key, str) and key.lower() in FORBIDDEN_KEYS:
            return False
    
    # Check for forbidden substrings in values
    for value in data.values():
        if isinstance(value, str):
            for forbidden in FORBIDDEN_SUBSTRINGS:
                if forbidden in value:
                    return False
        elif isinstance(value, dict):
            if not _sanitize_dict(value, context):
                return False
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    for forbidden in FORBIDDEN_SUBSTRINGS:
                        if forbidden in item:
                            return False
                elif isinstance(item, dict):
                    if not _sanitize_dict(item, context):
                        return False
    
    return True


def _normalize_tenant_config(tenant_config: Union[TenantConfig, Dict[str, Any]]) -> Optional[TenantConfig]:
    """Normalize tenant config from dict or TenantConfig. Returns None if invalid."""
    if isinstance(tenant_config, TenantConfig):
        return tenant_config
    
    if not isinstance(tenant_config, dict):
        return None
    
    # Sanitize input
    if not _sanitize_dict(tenant_config, "tenant_config"):
        return None
    
    try:
        # Extract required fields
        tenant_id = tenant_config.get("tenant_id")
        plan_str = tenant_config.get("plan")
        regions = tenant_config.get("regions", [])
        enabled_features_list = tenant_config.get("enabled_features", [])
        
        if not tenant_id or not plan_str:
            return None
        
        # Parse plan
        try:
            plan = PlanTier(plan_str) if isinstance(plan_str, str) else plan_str
        except (ValueError, TypeError):
            return None
        
        # Parse enabled features
        enabled_features = set()
        if isinstance(enabled_features_list, list):
            for feature in enabled_features_list:
                try:
                    if isinstance(feature, str):
                        enabled_features.add(FeatureFlag(feature))
                    elif isinstance(feature, FeatureFlag):
                        enabled_features.add(feature)
                except ValueError:
                    continue
        
        return TenantConfig(
            tenant_id=str(tenant_id)[:80],  # Bound length
            plan=plan,
            regions=regions[:MAX_REGIONS] if isinstance(regions, list) else [],
            enabled_features=enabled_features
        )
    
    except Exception:
        return None


def _normalize_request_hints(request_hints: Union[RequestHints, Dict[str, Any], None]) -> Optional[RequestHints]:
    """Normalize request hints from dict or RequestHints. Returns None if invalid."""
    if request_hints is None:
        return None
    
    if isinstance(request_hints, RequestHints):
        return request_hints
    
    if not isinstance(request_hints, dict):
        return None
    
    # Sanitize input
    if not _sanitize_dict(request_hints, "request_hints"):
        return None
    
    try:
        return RequestHints(
            requested_research=bool(request_hints.get("requested_research", False)),
            requested_tools=[ToolKind(t) for t in request_hints.get("requested_tools", []) 
                           if isinstance(t, str) and t in [tk.value for tk in ToolKind]][:MAX_TOOLS],
            requested_deepthink_passes=request_hints.get("requested_deepthink_passes"),
            requested_ttl_class=TTLClassLabel(request_hints.get("requested_ttl_class")) 
                               if request_hints.get("requested_ttl_class") else None,
            requested_export=bool(request_hints.get("requested_export", False))
        )
    except Exception:
        return None


def _normalize_requested_params(requested: Union[RequestedParams, Dict[str, Any], None]) -> Optional[RequestedParams]:
    """Normalize requested params from dict or RequestedParams. Returns None if invalid."""
    if requested is None:
        return None
    
    if isinstance(requested, RequestedParams):
        return requested
    
    if not isinstance(requested, dict):
        return None
    
    # Sanitize input
    if not _sanitize_dict(requested, "requested"):
        return None
    
    try:
        tool_kind = None
        if requested.get("tool_kind"):
            try:
                tool_kind = ToolKind(requested["tool_kind"])
            except ValueError:
                pass
        
        ttl_label = None
        if requested.get("ttl_label"):
            try:
                ttl_label = TTLClassLabel(requested["ttl_label"])
            except ValueError:
                pass
        
        logging_verbosity = None
        if requested.get("logging_verbosity"):
            try:
                logging_verbosity = LoggingLevel(requested["logging_verbosity"])
            except ValueError:
                pass
        
        export_scope = requested.get("export_scope")
        if isinstance(export_scope, list):
            export_scope = [str(s)[:MAX_STRING_LENGTH] for s in export_scope[:MAX_EXPORT_SCOPES]]
        else:
            export_scope = None
        
        admin_action = None
        if requested.get("admin_action"):
            admin_action = str(requested["admin_action"])[:MAX_STRING_LENGTH]
        
        max_tool_calls = requested.get("max_tool_calls")
        if isinstance(max_tool_calls, int) and max_tool_calls >= 0:
            max_tool_calls = min(max_tool_calls, MAX_TOOL_CALLS)
        else:
            max_tool_calls = None
        
        max_facts = requested.get("max_facts")
        if isinstance(max_facts, int) and max_facts >= 0:
            max_facts = min(max_facts, MAX_MEMORY_FACTS)
        else:
            max_facts = None
        
        region = None
        if requested.get("region"):
            region = str(requested["region"])[:MAX_STRING_LENGTH]
        
        return RequestedParams(
            tool_kind=tool_kind,
            ttl_label=ttl_label,
            logging_verbosity=logging_verbosity,
            export_scope=export_scope,
            admin_action=admin_action,
            max_tool_calls=max_tool_calls,
            max_facts=max_facts,
            region=region
        )
    except Exception:
        return None


# ============================================================================
# CANONICALIZATION AND SIGNATURE
# ============================================================================

def _canonicalize_decision_data(decision: PolicyDecision) -> str:
    """Create canonical JSON representation for signature generation."""
    # Create structure-only data (no tenant_id or sensitive fields)
    canonical_data = {
        "allowed": decision.allowed,
        "reason": decision.reason.value,
        "limits": decision.limits.as_dict(),
        "model_version": decision.model_version,
    }
    
    # Sort keys and use compact representation
    return json.dumps(canonical_data, sort_keys=True, separators=(',', ':'))


def _generate_decision_signature(decision: PolicyDecision) -> str:
    """Generate SHA256 signature of canonical decision data."""
    canonical_json = _canonicalize_decision_data(decision)
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()


# ============================================================================
# CORE POLICY ENGINE
# ============================================================================

def decide_policy(req: PolicyRequest) -> PolicyDecision:
    """
    Make policy decision with fail-closed behavior.
    
    Critical: requested flags can only clamp down, never expand tenant caps.
    """
    clamp_notes = []
    
    try:
        # Validate tenant config
        if req.tenant_config is None:
            return _fail_closed_decision(PolicyDecisionReason.POLICY_PACK_MISSING)
        
        tenant_config = _normalize_tenant_config(req.tenant_config)
        if tenant_config is None:
            return _fail_closed_decision(PolicyDecisionReason.TENANT_INVALID)
        
        # Validate tenant config structure
        config_valid, _ = validate_tenant_config(tenant_config)
        if not config_valid:
            return _fail_closed_decision(PolicyDecisionReason.TENANT_INVALID)
        
        # Resolve tenant capabilities
        request_hints = _normalize_request_hints(req.request_hints)
        try:
            caps = resolve_tenant_caps(tenant_config, request_hints)
        except Exception:
            return _fail_closed_decision(PolicyDecisionReason.CAPS_RESOLUTION_FAILED)
        
        # Validate operation type
        if not isinstance(req.operation, OperationType):
            return _fail_closed_decision(PolicyDecisionReason.OPERATION_UNKNOWN)
        
        # Normalize requested params
        requested = _normalize_requested_params(req.requested)
        
        # Check region constraints
        if requested and requested.region:
            if requested.region not in tenant_config.regions:
                return _fail_closed_decision(PolicyDecisionReason.REGION_DISALLOWS_OPERATION)
        
        # Create base derived limits from tenant caps
        limits = DerivedLimits(
            allowed_tools=list(caps.allowed_tools),
            tool_call_max_calls=min(caps.deepthink_max_passes * 2, MAX_TOOL_CALLS),  # Heuristic
            tool_call_timeout_ms=DEFAULT_TOOL_TIMEOUT_MS,
            deepthink_passes_allowed=caps.deepthink_max_passes,
            memory_read_allowed=caps.memory_max_facts_per_request > 0,
            memory_write_phase17_allowed=caps.memory_max_facts_per_request > 0 and FeatureFlag.MEMORY_ENABLED in tenant_config.enabled_features,
            memory_write_phase18_allowed=caps.memory_max_facts_per_request > 0 and FeatureFlag.MEMORY_ENABLED in tenant_config.enabled_features,
            memory_ttl_cap=caps.memory_ttl_cap,
            memory_max_facts_per_request=caps.memory_max_facts_per_request,
            memory_read_max_facts=min(caps.memory_max_facts_per_request, DEFAULT_MEMORY_READ_MAX_FACTS),
            memory_read_max_chars=DEFAULT_MEMORY_READ_MAX_CHARS,
            export_allowed=caps.export_allowed,
            export_scope_allowlist=["basic"] if caps.export_allowed else [],
            logging_level=LoggingLevel.STANDARD,
            admin_actions_allowlist=[],
            regions_allowed=tenant_config.regions,
            clamp_notes=list(caps.clamp_notes)
        )
        
        # Apply operation-specific checks and clamping
        decision_reason = _check_operation_allowed(req.operation, caps, limits, requested, clamp_notes)
        if decision_reason != PolicyDecisionReason.ALLOWED:
            return _create_decision(False, decision_reason, limits)
        
        # Apply requested parameter clamping
        _apply_requested_clamping(limits, requested, caps, clamp_notes)
        
        # Add clamp notes to limits
        limits.clamp_notes.extend(clamp_notes)
        
        # Ensure bounds and stable ordering
        _enforce_bounds_and_ordering(limits)
        
        # Create successful decision
        decision = _create_decision(True, PolicyDecisionReason.ALLOWED, limits)
        return decision
        
    except Exception:
        return _fail_closed_decision(PolicyDecisionReason.INTERNAL_INCONSISTENCY)


def _check_operation_allowed(operation: OperationType, caps: ResolvedTenantCaps, 
                           limits: DerivedLimits, requested: Optional[RequestedParams],
                           clamp_notes: List[str]) -> PolicyDecisionReason:
    """Check if operation is allowed based on tenant caps."""
    
    if operation == OperationType.TOOL_CALL:
        if not caps.research_allowed:
            return PolicyDecisionReason.FEATURE_DISABLED
        if requested and requested.tool_kind:
            if requested.tool_kind not in caps.allowed_tools:
                return PolicyDecisionReason.TOOL_NOT_ALLOWED
    
    elif operation == OperationType.MEMORY_READ:
        if not limits.memory_read_allowed:
            return PolicyDecisionReason.MEMORY_READ_NOT_ALLOWED
    
    elif operation == OperationType.MEMORY_WRITE_PHASE17:
        if not limits.memory_write_phase17_allowed:
            return PolicyDecisionReason.MEMORY_WRITE_NOT_ALLOWED
    
    elif operation == OperationType.MEMORY_WRITE_PHASE18:
        if not limits.memory_write_phase18_allowed:
            return PolicyDecisionReason.MEMORY_WRITE_NOT_ALLOWED
    
    elif operation == OperationType.EXPORT_REQUEST:
        if not caps.export_allowed:
            return PolicyDecisionReason.EXPORT_NOT_ALLOWED
    
    elif operation == OperationType.ADMIN_ACTION:
        if requested and requested.admin_action:
            # For now, no admin actions are allowed by default
            return PolicyDecisionReason.ADMIN_NOT_ALLOWED
    
    elif operation == OperationType.LOGGING:
        # Logging is generally allowed but may be clamped
        pass
    
    return PolicyDecisionReason.ALLOWED


def _apply_requested_clamping(limits: DerivedLimits, requested: Optional[RequestedParams],
                            caps: ResolvedTenantCaps, clamp_notes: List[str]) -> None:
    """Apply requested parameter clamping (can only reduce, never expand)."""
    if not requested:
        return
    
    # Clamp tool calls
    if requested.max_tool_calls is not None:
        if requested.max_tool_calls < limits.tool_call_max_calls:
            limits.tool_call_max_calls = requested.max_tool_calls
            clamp_notes.append("TOOL_CALLS_CLAMPED")
    
    # Clamp memory facts
    if requested.max_facts is not None:
        if requested.max_facts < limits.memory_max_facts_per_request:
            limits.memory_max_facts_per_request = requested.max_facts
            clamp_notes.append("MEMORY_FACTS_CLAMPED")
        if requested.max_facts < limits.memory_read_max_facts:
            limits.memory_read_max_facts = requested.max_facts
            clamp_notes.append("MEMORY_READ_FACTS_CLAMPED")
    
    # Clamp TTL (can only be more restrictive)
    if requested.ttl_label is not None:
        ttl_hierarchy = [TTLClassLabel.TTL_1H, TTLClassLabel.TTL_1D, TTLClassLabel.TTL_10D]
        current_idx = ttl_hierarchy.index(limits.memory_ttl_cap)
        requested_idx = ttl_hierarchy.index(requested.ttl_label)
        if requested_idx > current_idx:
            # Requested TTL is less restrictive than allowed, clamp to current cap
            clamp_notes.append("TTL_CLAMPED")
        elif requested_idx < current_idx:
            # Requested TTL is more restrictive, allow it
            limits.memory_ttl_cap = requested.ttl_label
    
    # Clamp logging level (can only be more restrictive)
    if requested.logging_verbosity is not None:
        log_hierarchy = [LoggingLevel.MINIMAL, LoggingLevel.STANDARD, LoggingLevel.VERBOSE]
        current_idx = log_hierarchy.index(limits.logging_level)
        requested_idx = log_hierarchy.index(requested.logging_verbosity)
        if requested_idx < current_idx:
            limits.logging_level = requested.logging_verbosity
            clamp_notes.append("LOG_LEVEL_CLAMPED")
    
    # Clamp export scope (can only be more restrictive)
    if requested.export_scope is not None and limits.export_allowed:
        # Only keep scopes that are both requested and allowed
        allowed_scopes = set(limits.export_scope_allowlist)
        requested_scopes = set(requested.export_scope)
        intersection = allowed_scopes.intersection(requested_scopes)
        if len(intersection) < len(allowed_scopes):
            limits.export_scope_allowlist = sorted(list(intersection))
            clamp_notes.append("EXPORT_SCOPE_CLAMPED")


def _enforce_bounds_and_ordering(limits: DerivedLimits) -> None:
    """Enforce bounds and stable ordering on all limits."""
    # Bound and sort tools
    limits.allowed_tools = sorted(limits.allowed_tools[:MAX_TOOLS], key=lambda x: x.value)
    
    # Bound numeric values
    limits.tool_call_max_calls = max(0, min(limits.tool_call_max_calls, MAX_TOOL_CALLS))
    limits.deepthink_passes_allowed = max(0, min(limits.deepthink_passes_allowed, MAX_DEEPTHINK_PASSES))
    limits.memory_max_facts_per_request = max(0, min(limits.memory_max_facts_per_request, MAX_MEMORY_FACTS))
    limits.memory_read_max_facts = max(0, min(limits.memory_read_max_facts, MAX_MEMORY_FACTS))
    limits.memory_read_max_chars = max(0, min(limits.memory_read_max_chars, MAX_MEMORY_CHARS))
    
    # Bound and sort lists
    limits.export_scope_allowlist = sorted(limits.export_scope_allowlist[:MAX_EXPORT_SCOPES])
    limits.admin_actions_allowlist = sorted(limits.admin_actions_allowlist[:MAX_ADMIN_ACTIONS])
    limits.regions_allowed = sorted(limits.regions_allowed[:MAX_REGIONS])
    limits.clamp_notes = sorted(list(set(limits.clamp_notes))[:MAX_CLAMP_NOTES])


def _create_decision(allowed: bool, reason: PolicyDecisionReason, limits: DerivedLimits) -> PolicyDecision:
    """Create policy decision with signature."""
    decision = PolicyDecision(
        allowed=allowed,
        reason=reason,
        limits=limits,
        decision_signature="",  # Will be set below
        model_version="20.2.0"
    )
    
    # Generate signature
    decision.decision_signature = _generate_decision_signature(decision)
    return decision


def _fail_closed_decision(reason: PolicyDecisionReason) -> PolicyDecision:
    """Create fail-closed decision with minimal safe limits."""
    limits = DerivedLimits(
        allowed_tools=[],
        tool_call_max_calls=0,
        tool_call_timeout_ms=DEFAULT_TOOL_TIMEOUT_MS,
        deepthink_passes_allowed=0,
        memory_read_allowed=False,
        memory_write_phase17_allowed=False,
        memory_write_phase18_allowed=False,
        memory_ttl_cap=TTLClassLabel.TTL_1H,
        memory_max_facts_per_request=0,
        memory_read_max_facts=0,
        memory_read_max_chars=0,
        export_allowed=False,
        export_scope_allowlist=[],
        logging_level=LoggingLevel.MINIMAL,
        admin_actions_allowlist=[],
        regions_allowed=[],
        clamp_notes=[]
    )
    
    return _create_decision(False, reason, limits)
