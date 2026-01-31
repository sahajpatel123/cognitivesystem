#!/usr/bin/env python3
"""
Phase 20 Step 7: Compliance Region Modes

Deterministic, enforceable region compliance modes that clamp capabilities
across tools, telemetry, and export with fail-closed behavior.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional, Union, Set

from .tenant import ToolKind, ResolvedTenantCaps


# ============================================================================
# ENUMS
# ============================================================================

class RegionMode(Enum):
    """Region compliance modes with deterministic capability mappings."""
    IN = "IN"
    EU = "EU"
    US = "US"
    STRICT = "STRICT"


class TelemetryLevel(Enum):
    """Telemetry collection levels with hierarchical ordering."""
    OFF = "OFF"
    MINIMAL = "MINIMAL"
    STANDARD = "STANDARD"
    DEBUG = "DEBUG"


class RegionReasonCode(Enum):
    """Reason codes for region capability resolution."""
    OK = "OK"
    REGION_UNKNOWN_FAIL_CLOSED = "REGION_UNKNOWN_FAIL_CLOSED"
    REGION_INVALID_FAIL_CLOSED = "REGION_INVALID_FAIL_CLOSED"
    TOOLS_CLAMPED_BY_REGION = "TOOLS_CLAMPED_BY_REGION"
    TELEMETRY_CLAMPED_BY_REGION = "TELEMETRY_CLAMPED_BY_REGION"
    EXPORT_DENIED_BY_REGION = "EXPORT_DENIED_BY_REGION"
    DOMAINS_SANITIZED = "DOMAINS_SANITIZED"
    INTERNAL_INCONSISTENCY_FAIL_CLOSED = "INTERNAL_INCONSISTENCY_FAIL_CLOSED"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class RegionCaps:
    """Region capability policy specification."""
    allowed_tools: Set[ToolKind]
    telemetry_level_cap: TelemetryLevel
    export_allowed: bool
    domain_policy: str  # "ANY", "RESTRICTED", "DENY"
    allowed_domains: Set[str]


@dataclass
class ResolvedRegionCaps:
    """Structure-only resolved region capabilities."""
    region_mode: RegionMode
    effective_allowed_tools: List[str]
    telemetry_level_cap: TelemetryLevel
    export_allowed: bool
    allowed_domains: List[str]
    clamp_notes: List[str]
    signature: str


# ============================================================================
# CONSTANTS
# ============================================================================

# Bounds
MAX_DOMAINS = 64
MAX_CLAMP_NOTES = 16
MAX_TOOLS = 8
MAX_STRING_LENGTH = 64

# Forbidden patterns for sanitization
FORBIDDEN_KEY_PATTERNS = frozenset([
    "user", "prompt", "message", "text", "content", "body", "snippet", "excerpt",
    "quote", "tool_output", "response", "answer", "memory_value", "raw", "transcript",
    "email", "subject", "phone", "address", "token", "secret"
])

SENTINEL_PATTERNS = ["SENSITIVE_", "SECRET_", "PRIVATE_"]

# Domain validation pattern
DOMAIN_PATTERN = re.compile(r'^[a-z0-9.-]+\.[a-z]{2,}$')

# Telemetry level hierarchy (lower index = more restrictive)
TELEMETRY_HIERARCHY = [TelemetryLevel.OFF, TelemetryLevel.MINIMAL, TelemetryLevel.STANDARD, TelemetryLevel.DEBUG]

# Region capability mappings
REGION_CAPS_MAP = {
    RegionMode.STRICT: RegionCaps(
        allowed_tools=set(),  # No external tools
        telemetry_level_cap=TelemetryLevel.OFF,
        export_allowed=False,
        domain_policy="DENY",
        allowed_domains=set()
    ),
    RegionMode.EU: RegionCaps(
        allowed_tools={ToolKind.DOCS},  # Only docs, no web
        telemetry_level_cap=TelemetryLevel.MINIMAL,
        export_allowed=False,  # GDPR compliance
        domain_policy="RESTRICTED",
        allowed_domains={"docs.example.com", "help.example.com"}
    ),
    RegionMode.IN: RegionCaps(
        allowed_tools={ToolKind.DOCS, ToolKind.WEB},
        telemetry_level_cap=TelemetryLevel.STANDARD,
        export_allowed=True,
        domain_policy="RESTRICTED",
        allowed_domains={"docs.example.com", "help.example.com", "api.example.com"}
    ),
    RegionMode.US: RegionCaps(
        allowed_tools={ToolKind.DOCS, ToolKind.WEB},
        telemetry_level_cap=TelemetryLevel.DEBUG,
        export_allowed=True,
        domain_policy="ANY",
        allowed_domains=set()  # No restrictions
    ),
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _is_safe_string(value: str) -> bool:
    """Check if string is safe (no forbidden patterns)."""
    if not isinstance(value, str):
        return False
    
    # Check sentinel patterns
    for pattern in SENTINEL_PATTERNS:
        if pattern in value:
            return False
    
    # Check length
    if len(value) > MAX_STRING_LENGTH:
        return False
    
    return True


def _sanitize_string(value: str) -> str:
    """Sanitize string by removing forbidden patterns."""
    if not _is_safe_string(value):
        return "REDACTED_TOKEN"
    
    return value[:MAX_STRING_LENGTH]


def parse_region_mode(region_input: Union[RegionMode, str, None]) -> tuple[RegionMode, Optional[str]]:
    """
    Parse region mode input with fail-closed behavior.
    
    Returns:
        (RegionMode, reason_code_or_none)
    """
    if isinstance(region_input, RegionMode):
        return region_input, None
    
    if region_input is None or region_input == "":
        return RegionMode.STRICT, RegionReasonCode.REGION_UNKNOWN_FAIL_CLOSED.value
    
    if not isinstance(region_input, str):
        return RegionMode.STRICT, RegionReasonCode.REGION_INVALID_FAIL_CLOSED.value
    
    # Check for sentinel patterns in input
    if not _is_safe_string(region_input):
        return RegionMode.STRICT, RegionReasonCode.REGION_INVALID_FAIL_CLOSED.value
    
    try:
        return RegionMode(region_input.upper().strip()), None
    except ValueError:
        return RegionMode.STRICT, RegionReasonCode.REGION_UNKNOWN_FAIL_CLOSED.value


def canonicalize_domain(domain: str) -> Optional[str]:
    """
    Canonicalize domain string to safe format.
    
    Returns:
        Canonicalized domain or None if invalid
    """
    if not isinstance(domain, str):
        return None
    
    # Check for sentinel patterns
    if not _is_safe_string(domain):
        return None
    
    # Basic cleanup
    domain = domain.lower().strip()
    
    # Remove www. prefix
    if domain.startswith("www."):
        domain = domain[4:]
    
    # Reject URLs (must be domain only)
    if "://" in domain or "/" in domain or "?" in domain or "#" in domain:
        return None
    
    # Validate domain pattern
    if not DOMAIN_PATTERN.match(domain):
        return None
    
    # Bound length
    if len(domain) > MAX_STRING_LENGTH:
        return None
    
    return domain


def clamp_tools(tenant_tools: Set[ToolKind], region_tools: Set[ToolKind]) -> List[str]:
    """
    Clamp tools to intersection of tenant and region allowed tools.
    
    Returns:
        Sorted list of allowed tool names
    """
    # Intersection: only tools allowed by BOTH tenant and region
    effective_tools = tenant_tools & region_tools
    
    # Convert to sorted list of strings, bounded
    tool_names = sorted([tool.value for tool in effective_tools])
    return tool_names[:MAX_TOOLS]


def clamp_telemetry(requested_level: Optional[TelemetryLevel],
                   tenant_cap: Optional[TelemetryLevel],
                   region_cap: TelemetryLevel) -> TelemetryLevel:
    """
    Clamp telemetry level to most restrictive of requested/tenant/region.
    
    Returns:
        Most restrictive telemetry level
    """
    # Start with region cap as baseline
    effective_level = region_cap
    
    # Apply tenant cap (more restrictive wins)
    if tenant_cap is not None:
        tenant_index = TELEMETRY_HIERARCHY.index(tenant_cap)
        region_index = TELEMETRY_HIERARCHY.index(region_cap)
        if tenant_index < region_index:  # More restrictive
            effective_level = tenant_cap
    
    # Apply requested level (can only make it more restrictive)
    if requested_level is not None:
        requested_index = TELEMETRY_HIERARCHY.index(requested_level)
        effective_index = TELEMETRY_HIERARCHY.index(effective_level)
        if requested_index < effective_index:  # More restrictive
            effective_level = requested_level
    
    return effective_level


def clamp_domains(tenant_domains: Set[str], region_caps: RegionCaps) -> List[str]:
    """
    Clamp domains based on region policy.
    
    Returns:
        Sorted list of allowed domains
    """
    if region_caps.domain_policy == "DENY":
        return []
    elif region_caps.domain_policy == "ANY":
        # Allow all tenant domains, canonicalized and bounded
        canonicalized = []
        for domain in tenant_domains:
            canonical = canonicalize_domain(domain)
            if canonical:
                canonicalized.append(canonical)
        return sorted(list(set(canonicalized)))[:MAX_DOMAINS]
    elif region_caps.domain_policy == "RESTRICTED":
        # Only allow intersection of tenant and region allowed domains
        allowed = tenant_domains & region_caps.allowed_domains
        canonicalized = []
        for domain in allowed:
            canonical = canonicalize_domain(domain)
            if canonical:
                canonicalized.append(canonical)
        return sorted(list(set(canonicalized)))[:MAX_DOMAINS]
    else:
        # Unknown policy -> deny all (fail-closed)
        return []


def _canonical_json(obj: Any) -> str:
    """Generate canonical JSON string for signatures."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))


def compute_region_signature(caps: ResolvedRegionCaps) -> str:
    """
    Compute deterministic signature for resolved region capabilities.
    
    Returns:
        SHA256 hex digest
    """
    # Create signature pack without the signature field itself
    signature_pack = {
        "region_mode": caps.region_mode.value,
        "effective_allowed_tools": caps.effective_allowed_tools,
        "telemetry_level_cap": caps.telemetry_level_cap.value,
        "export_allowed": caps.export_allowed,
        "allowed_domains": caps.allowed_domains,
        "clamp_notes": caps.clamp_notes,
    }
    
    canonical = _canonical_json(signature_pack)
    hash_obj = hashlib.sha256(canonical.encode('utf-8'))
    return hash_obj.hexdigest()


def assert_no_text_leakage(obj: Any, sentinels: List[str]) -> None:
    """Assert that no sentinel strings appear in object."""
    serialized = json.dumps(obj) if not isinstance(obj, str) else obj
    
    for sentinel in sentinels:
        if sentinel in serialized:
            raise AssertionError(f"Sentinel string '{sentinel}' found in: {serialized}")


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def resolve_region_caps(tenant_caps: ResolvedTenantCaps,
                       region_mode: Union[RegionMode, str, None],
                       request_hints: Optional[Dict[str, Any]] = None) -> ResolvedRegionCaps:
    """
    Resolve region capabilities with fail-closed behavior.
    
    Args:
        tenant_caps: Resolved tenant capabilities
        region_mode: Region mode (parsed with fail-closed behavior)
        request_hints: Optional request hints (structure-only)
    
    Returns:
        ResolvedRegionCaps with deterministic signature
    """
    try:
        clamp_notes = []
        
        # Parse region mode (fail-closed to STRICT)
        parsed_region, region_reason = parse_region_mode(region_mode)
        if region_reason:
            clamp_notes.append(region_reason)
        
        # Get region capability policy
        region_caps = REGION_CAPS_MAP[parsed_region]
        
        # Clamp tools (intersection of tenant and region)
        tenant_tools = set(tenant_caps.allowed_tools) if tenant_caps.allowed_tools else set()
        effective_tools = clamp_tools(tenant_tools, region_caps.allowed_tools)
        if len(effective_tools) < len(tenant_tools):
            clamp_notes.append(RegionReasonCode.TOOLS_CLAMPED_BY_REGION.value)
        
        # Clamp telemetry level
        requested_telemetry = None
        if request_hints and "telemetry_level" in request_hints:
            try:
                requested_telemetry = TelemetryLevel(request_hints["telemetry_level"])
            except (ValueError, TypeError):
                pass  # Invalid request ignored
        
        # Assume tenant has no telemetry cap for now (can be extended)
        tenant_telemetry_cap = None
        effective_telemetry = clamp_telemetry(requested_telemetry, tenant_telemetry_cap, region_caps.telemetry_level_cap)
        
        if requested_telemetry and effective_telemetry != requested_telemetry:
            clamp_notes.append(RegionReasonCode.TELEMETRY_CLAMPED_BY_REGION.value)
        
        # Clamp export capability
        effective_export = tenant_caps.export_allowed and region_caps.export_allowed
        if tenant_caps.export_allowed and not effective_export:
            clamp_notes.append(RegionReasonCode.EXPORT_DENIED_BY_REGION.value)
        
        # Clamp domains (simplified - assume tenant has no domain restrictions for now)
        tenant_domains = set()  # Could be extended to read from tenant_caps
        effective_domains = clamp_domains(tenant_domains, region_caps)
        
        # Sanitize and bound clamp notes
        safe_notes = []
        for note in clamp_notes[:MAX_CLAMP_NOTES]:
            if isinstance(note, str) and _is_safe_string(note):
                safe_notes.append(_sanitize_string(note))
        
        # Sort for determinism
        safe_notes.sort()
        
        # Create resolved caps
        resolved = ResolvedRegionCaps(
            region_mode=parsed_region,
            effective_allowed_tools=effective_tools,
            telemetry_level_cap=effective_telemetry,
            export_allowed=effective_export,
            allowed_domains=effective_domains,
            clamp_notes=safe_notes,
            signature=""  # Will be computed
        )
        
        # Compute signature
        resolved.signature = compute_region_signature(resolved)
        
        return resolved
        
    except Exception:
        # Fail-closed: return STRICT minimal caps
        return ResolvedRegionCaps(
            region_mode=RegionMode.STRICT,
            effective_allowed_tools=[],
            telemetry_level_cap=TelemetryLevel.OFF,
            export_allowed=False,
            allowed_domains=[],
            clamp_notes=[RegionReasonCode.INTERNAL_INCONSISTENCY_FAIL_CLOSED.value],
            signature=compute_region_signature(ResolvedRegionCaps(
                region_mode=RegionMode.STRICT,
                effective_allowed_tools=[],
                telemetry_level_cap=TelemetryLevel.OFF,
                export_allowed=False,
                allowed_domains=[],
                clamp_notes=[RegionReasonCode.INTERNAL_INCONSISTENCY_FAIL_CLOSED.value],
                signature=""
            ))
        )
