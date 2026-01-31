#!/usr/bin/env python3
"""
Phase 20 Step 6: RBAC Module

Strict role-based access control for admin operations with fail-closed behavior.
All outputs are structure-only and deterministic.
"""

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any, List, Optional, Union

from .tenant import TenantConfig, resolve_tenant_caps


# ============================================================================
# ENUMS
# ============================================================================

class Role(Enum):
    """Admin roles with strict hierarchy."""
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"
    DEVELOPER = "DEVELOPER"
    BILLING = "BILLING"


class AdminOperation(Enum):
    """Admin operations requiring RBAC authorization."""
    ENABLE_TOOL = "ENABLE_TOOL"
    DISABLE_TOOL = "DISABLE_TOOL"
    CHANGE_RETENTION = "CHANGE_RETENTION"
    REQUEST_EXPORT = "REQUEST_EXPORT"
    VIEW_AUDIT_SUMMARY = "VIEW_AUDIT_SUMMARY"
    CHANGE_TENANT_CONFIG = "CHANGE_TENANT_CONFIG"
    CHANGE_POLICY_PACK = "CHANGE_POLICY_PACK"


class RBACReason(Enum):
    """Exhaustive reason codes for RBAC decisions."""
    OK = "OK"
    ROLE_MISSING = "ROLE_MISSING"
    ROLE_UNKNOWN = "ROLE_UNKNOWN"
    OP_UNKNOWN = "OP_UNKNOWN"
    OP_NOT_ALLOWED = "OP_NOT_ALLOWED"
    TENANT_CAPS_DENY = "TENANT_CAPS_DENY"
    INVALID_REQUEST = "INVALID_REQUEST"
    INTERNAL_INCONSISTENCY = "INTERNAL_INCONSISTENCY"
    BOUNDS_CLAMPED = "BOUNDS_CLAMPED"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class RBACRequest:
    """Structure-only RBAC request."""
    tenant_id: str
    actor_role: Union[Role, str]
    operation: Union[AdminOperation, str]
    request_hints: Optional[Dict[str, Any]] = None
    now_ms: Optional[int] = None


@dataclass
class RBACDecision:
    """Structure-only RBAC decision."""
    allow: bool
    reason: RBACReason
    derived_limits: Dict[str, Union[int, str, bool]]
    clamp_notes: List[str]
    signature: str


# ============================================================================
# CONSTANTS
# ============================================================================

# Bounds
MAX_CLAMP_NOTES = 10
MAX_CLAMP_NOTE_LENGTH = 48
MAX_REQUEST_HINTS_KEYS = 32
MAX_REQUEST_HINTS_KEY_LENGTH = 40
MAX_REQUEST_HINTS_STRING_LENGTH = 80

# Safe token pattern for clamp notes
SAFE_TOKEN_PATTERN = re.compile(r'^[A-Z0-9_./:-]{1,48}$')

# Forbidden keys in request hints
FORBIDDEN_KEYS = {
    "prompt", "content", "message", "snippet", "raw", "user_text", "email", 
    "address", "phone", "token", "secret", "tool_output", "response", "answer",
    "memory_value", "transcript", "excerpt", "body", "quote"
}

# Forbidden value patterns
FORBIDDEN_PATTERNS = [
    "SENSITIVE_", "SECRET_", "PRIVATE_",
    "ignore previous instructions", "disregard", "override",
    "From:", "To:", "Subject:", "Content-Type:",
    "> ", "```", "<!--", "-->"
]

# Role to operations mapping
ROLE_PERMISSIONS = {
    Role.OWNER: {
        AdminOperation.ENABLE_TOOL,
        AdminOperation.DISABLE_TOOL,
        AdminOperation.CHANGE_RETENTION,
        AdminOperation.REQUEST_EXPORT,
        AdminOperation.VIEW_AUDIT_SUMMARY,
        AdminOperation.CHANGE_TENANT_CONFIG,
        AdminOperation.CHANGE_POLICY_PACK,
    },
    Role.ADMIN: {
        AdminOperation.ENABLE_TOOL,
        AdminOperation.DISABLE_TOOL,
        AdminOperation.CHANGE_RETENTION,
        AdminOperation.REQUEST_EXPORT,
        AdminOperation.VIEW_AUDIT_SUMMARY,
    },
    Role.AUDITOR: {
        AdminOperation.VIEW_AUDIT_SUMMARY,
        AdminOperation.REQUEST_EXPORT,
    },
    Role.DEVELOPER: {
        AdminOperation.VIEW_AUDIT_SUMMARY,
    },
    Role.BILLING: {
        AdminOperation.REQUEST_EXPORT,
    },
}


# ============================================================================
# SANITIZATION HELPERS
# ============================================================================

def _is_safe_string(value: str) -> bool:
    """Check if string is safe (no forbidden patterns)."""
    if not isinstance(value, str):
        return False
    
    # Check forbidden patterns
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in value:
            return False
    
    # Check length
    if len(value) > MAX_REQUEST_HINTS_STRING_LENGTH:
        return False
    
    return True


def _sanitize_request_hints(hints: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Sanitize request hints by removing forbidden keys and values."""
    if not hints or not isinstance(hints, dict):
        return {}
    
    sanitized = {}
    dropped_keys = 0
    redacted_values = 0
    
    # Limit number of keys
    keys_to_process = list(hints.keys())[:MAX_REQUEST_HINTS_KEYS]
    
    for key in keys_to_process:
        # Check key length and forbidden status
        if (len(key) > MAX_REQUEST_HINTS_KEY_LENGTH or 
            key.lower() in FORBIDDEN_KEYS):
            dropped_keys += 1
            continue
        
        value = hints[key]
        
        # Sanitize value based on type
        if isinstance(value, str):
            if not _is_safe_string(value):
                sanitized[key] = "REDACTED_TOKEN"
                redacted_values += 1
            else:
                # Truncate if too long
                sanitized[key] = value[:MAX_REQUEST_HINTS_STRING_LENGTH]
        elif isinstance(value, (int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, (list, dict)):
            # Recursively sanitize nested structures (bounded)
            if isinstance(value, list) and len(value) <= 10:
                sanitized_list = []
                for item in value[:10]:  # Limit list size
                    if isinstance(item, str) and _is_safe_string(item):
                        sanitized_list.append(item[:MAX_REQUEST_HINTS_STRING_LENGTH])
                    elif isinstance(item, (int, float, bool)):
                        sanitized_list.append(item)
                    else:
                        sanitized_list.append("REDACTED_TOKEN")
                        redacted_values += 1
                sanitized[key] = sanitized_list
            elif isinstance(value, dict) and len(value) <= 10:
                sanitized[key] = _sanitize_request_hints(value)
            else:
                sanitized[key] = "REDACTED_TOKEN"
                redacted_values += 1
        else:
            sanitized[key] = "REDACTED_TOKEN"
            redacted_values += 1
    
    # Add sanitization stats
    sanitized["_sanitize_stats"] = {
        "dropped_keys_count": dropped_keys,
        "redacted_values_count": redacted_values,
        "had_forbidden_keys": dropped_keys > 0,
        "had_forbidden_values": redacted_values > 0,
    }
    
    return sanitized


def _compute_tenant_hash(tenant_id: str) -> str:
    """Compute privacy-preserving tenant hash."""
    if not tenant_id:
        return "EMPTY_TENANT"
    
    hash_obj = hashlib.sha256(tenant_id.encode('utf-8'))
    return hash_obj.hexdigest()[:12]  # 12-char prefix


def _canonical_json(obj: Any) -> str:
    """Generate canonical JSON string for signatures."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))


def _compute_rbac_signature(decision_data: Dict[str, Any]) -> str:
    """Compute deterministic signature for RBAC decision."""
    # Create signature pack without the signature field itself
    signature_pack = {
        "allow": decision_data["allow"],
        "reason": decision_data["reason"],
        "derived_limits": decision_data["derived_limits"],
        "clamp_notes": decision_data["clamp_notes"],
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
# RBAC LOGIC
# ============================================================================

def _parse_role(role_input: Union[Role, str]) -> Optional[Role]:
    """Parse role input to Role enum, fail-closed."""
    if isinstance(role_input, Role):
        return role_input
    
    if not isinstance(role_input, str):
        return None
    
    try:
        # Only accept exact case matches - no case conversion
        return Role(role_input)
    except ValueError:
        return None


def _parse_operation(op_input: Union[AdminOperation, str]) -> Optional[AdminOperation]:
    """Parse operation input to AdminOperation enum, fail-closed."""
    if isinstance(op_input, AdminOperation):
        return op_input
    
    if not isinstance(op_input, str):
        return None
    
    try:
        # Only accept exact case matches - no case conversion
        return AdminOperation(op_input)
    except ValueError:
        return None


def _check_role_permission(role: Role, operation: AdminOperation) -> bool:
    """Check if role has permission for operation."""
    allowed_ops = ROLE_PERMISSIONS.get(role, set())
    return operation in allowed_ops


def _generate_clamp_notes(sanitized_hints: Dict[str, Any], 
                         caps_applied: bool = False) -> List[str]:
    """Generate bounded clamp notes from sanitization stats."""
    notes = []
    
    if "_sanitize_stats" in sanitized_hints:
        stats = sanitized_hints["_sanitize_stats"]
        if stats.get("dropped_keys_count", 0) > 0:
            notes.append("HINTS_KEYS_DROPPED")
        if stats.get("redacted_values_count", 0) > 0:
            notes.append("HINTS_VALUES_REDACTED")
    
    if caps_applied:
        notes.append("TENANT_CAPS_APPLIED")
    
    # Ensure notes are safe tokens and bounded
    safe_notes = []
    for note in notes[:MAX_CLAMP_NOTES]:
        if SAFE_TOKEN_PATTERN.match(note):
            safe_notes.append(note[:MAX_CLAMP_NOTE_LENGTH])
    
    return safe_notes


def authorize_admin_action(tenant_config: TenantConfig,
                          actor_role: Union[Role, str],
                          operation: Union[AdminOperation, str],
                          request_hints: Optional[Dict[str, Any]] = None,
                          now_ms: Optional[int] = None) -> RBACDecision:
    """
    Authorize admin action with strict RBAC and fail-closed behavior.
    
    Args:
        tenant_config: Tenant configuration from governance/tenant.py
        actor_role: Role of the actor requesting the operation
        operation: Admin operation being requested
        request_hints: Optional structure-only hints (sanitized)
        now_ms: Optional timestamp for audit (not used in RBAC logic)
    
    Returns:
        RBACDecision with allow/deny and structured metadata
    """
    try:
        # Sanitize request hints first
        sanitized_hints = _sanitize_request_hints(request_hints)
        
        # Parse role (fail-closed)
        parsed_role = _parse_role(actor_role)
        if parsed_role is None:
            return RBACDecision(
                allow=False,
                reason=RBACReason.ROLE_MISSING if actor_role is None else RBACReason.ROLE_UNKNOWN,
                derived_limits={},
                clamp_notes=_generate_clamp_notes(sanitized_hints),
                signature=_compute_rbac_signature({
                    "allow": False,
                    "reason": RBACReason.ROLE_MISSING.value if actor_role is None else RBACReason.ROLE_UNKNOWN.value,
                    "derived_limits": {},
                    "clamp_notes": _generate_clamp_notes(sanitized_hints),
                })
            )
        
        # Parse operation (fail-closed)
        parsed_operation = _parse_operation(operation)
        if parsed_operation is None:
            return RBACDecision(
                allow=False,
                reason=RBACReason.OP_UNKNOWN,
                derived_limits={},
                clamp_notes=_generate_clamp_notes(sanitized_hints),
                signature=_compute_rbac_signature({
                    "allow": False,
                    "reason": RBACReason.OP_UNKNOWN.value,
                    "derived_limits": {},
                    "clamp_notes": _generate_clamp_notes(sanitized_hints),
                })
            )
        
        # Check role permission
        if not _check_role_permission(parsed_role, parsed_operation):
            return RBACDecision(
                allow=False,
                reason=RBACReason.OP_NOT_ALLOWED,
                derived_limits={},
                clamp_notes=_generate_clamp_notes(sanitized_hints),
                signature=_compute_rbac_signature({
                    "allow": False,
                    "reason": RBACReason.OP_NOT_ALLOWED.value,
                    "derived_limits": {},
                    "clamp_notes": _generate_clamp_notes(sanitized_hints),
                })
            )
        
        # Resolve tenant caps to check constraints
        try:
            caps = resolve_tenant_caps(tenant_config, request_hints)
        except Exception:
            # Fail-closed on caps resolution error
            return RBACDecision(
                allow=False,
                reason=RBACReason.INTERNAL_INCONSISTENCY,
                derived_limits={},
                clamp_notes=_generate_clamp_notes(sanitized_hints),
                signature=_compute_rbac_signature({
                    "allow": False,
                    "reason": RBACReason.INTERNAL_INCONSISTENCY.value,
                    "derived_limits": {},
                    "clamp_notes": _generate_clamp_notes(sanitized_hints),
                })
            )
        
        # Check tenant caps constraints for specific operations
        caps_deny = False
        if parsed_operation == AdminOperation.REQUEST_EXPORT and not caps.export_allowed:
            caps_deny = True
        
        if caps_deny:
            return RBACDecision(
                allow=False,
                reason=RBACReason.TENANT_CAPS_DENY,
                derived_limits={},
                clamp_notes=_generate_clamp_notes(sanitized_hints, caps_applied=True),
                signature=_compute_rbac_signature({
                    "allow": False,
                    "reason": RBACReason.TENANT_CAPS_DENY.value,
                    "derived_limits": {},
                    "clamp_notes": _generate_clamp_notes(sanitized_hints, caps_applied=True),
                })
            )
        
        # Generate derived limits from tenant caps (structure-only)
        derived_limits = {
            "tenant_hash": _compute_tenant_hash(tenant_config.tenant_id),
            "plan_tier": tenant_config.plan.value,
            "export_allowed": caps.export_allowed,
            "allowed_tools_count": len(caps.allowed_tools),
            "max_memory_facts": caps.memory_max_facts_per_request,
            "deepthink_max_passes": caps.deepthink_max_passes,
        }
        
        # Success case
        decision_data = {
            "allow": True,
            "reason": RBACReason.OK.value,
            "derived_limits": derived_limits,
            "clamp_notes": _generate_clamp_notes(sanitized_hints, caps_applied=True),
        }
        
        return RBACDecision(
            allow=True,
            reason=RBACReason.OK,
            derived_limits=derived_limits,
            clamp_notes=_generate_clamp_notes(sanitized_hints, caps_applied=True),
            signature=_compute_rbac_signature(decision_data)
        )
        
    except Exception:
        # Fail-closed on any unexpected error
        return RBACDecision(
            allow=False,
            reason=RBACReason.INTERNAL_INCONSISTENCY,
            derived_limits={},
            clamp_notes=[],
            signature=_compute_rbac_signature({
                "allow": False,
                "reason": RBACReason.INTERNAL_INCONSISTENCY.value,
                "derived_limits": {},
                "clamp_notes": [],
            })
        )
