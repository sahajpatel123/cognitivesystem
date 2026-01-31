#!/usr/bin/env python3
"""
Phase 20 Step 6: Change Control Module

Governed policy change workflow requiring version bump + validation + audit.
All outputs are structure-only and deterministic.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional, Union

from .tenant import TenantConfig
from .rbac import Role, AdminOperation, authorize_admin_action
from .audit import AuditLog, AuditOperationType, AuditDecision, AuditReasonCode, record_audit_event


# ============================================================================
# ENUMS
# ============================================================================

class ChangeType(Enum):
    """Types of governance changes requiring version control."""
    POLICY_PACK = "POLICY_PACK"
    TENANT_CAPS = "TENANT_CAPS"
    RETENTION_POLICY = "RETENTION_POLICY"
    EXPORT_POLICY = "EXPORT_POLICY"
    GOVERNANCE_CONTRACT = "GOVERNANCE_CONTRACT"


class ChangeReason(Enum):
    """Exhaustive reason codes for change control decisions."""
    OK = "OK"
    POLICY_DISABLED = "POLICY_DISABLED"
    ROLE_NOT_ALLOWED = "ROLE_NOT_ALLOWED"
    INVALID_REQUEST = "INVALID_REQUEST"
    VERSION_NOT_BUMPED = "VERSION_NOT_BUMPED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    AUDIT_WRITE_FAILED = "AUDIT_WRITE_FAILED"
    TENANT_CAPS_DENY = "TENANT_CAPS_DENY"
    INTERNAL_INCONSISTENCY = "INTERNAL_INCONSISTENCY"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class ChangeRequest:
    """Structure-only change control request."""
    tenant_id: str
    actor_role: Union[Role, str]
    change_type: Union[ChangeType, str]
    from_version: str
    to_version: str
    diff_hash: Optional[str] = None
    diff_summary: Optional[Dict[str, Any]] = None
    now_ms: Optional[int] = None


@dataclass
class ChangeDecision:
    """Structure-only change control decision."""
    allow: bool
    reason: ChangeReason
    applied_version: str
    clamp_notes: List[str]
    audit_event_signature: Optional[str]
    signature: str


# ============================================================================
# CONSTANTS
# ============================================================================

# Bounds
MAX_VERSION_LENGTH = 16
MAX_DIFF_SUMMARY_ITEMS = 16
MAX_CLAMP_NOTES = 10
MAX_CLAMP_NOTE_LENGTH = 48

# Safe token pattern
SAFE_TOKEN_PATTERN = re.compile(r'^[A-Z0-9_./:-]{1,48}$')

# Version pattern (simple semver: major.minor.patch)
VERSION_PATTERN = re.compile(r'^(\d+)\.(\d+)\.(\d+)$')

# Change type to required admin operation mapping
CHANGE_TYPE_TO_OPERATION = {
    ChangeType.POLICY_PACK: AdminOperation.CHANGE_POLICY_PACK,
    ChangeType.TENANT_CAPS: AdminOperation.CHANGE_TENANT_CONFIG,
    ChangeType.RETENTION_POLICY: AdminOperation.CHANGE_RETENTION,
    ChangeType.EXPORT_POLICY: AdminOperation.CHANGE_POLICY_PACK,
    ChangeType.GOVERNANCE_CONTRACT: AdminOperation.CHANGE_POLICY_PACK,
}

# Minimum version bump requirements
MIN_VERSION_BUMP = {
    ChangeType.GOVERNANCE_CONTRACT: "patch",  # At least patch bump
    ChangeType.POLICY_PACK: "minor",         # At least minor bump
    ChangeType.TENANT_CAPS: "patch",
    ChangeType.RETENTION_POLICY: "patch",
    ChangeType.EXPORT_POLICY: "minor",
}


# ============================================================================
# HELPERS
# ============================================================================

def _compute_tenant_hash(tenant_id: str) -> str:
    """Compute privacy-preserving tenant hash."""
    if not tenant_id:
        return "EMPTY_TENANT"
    
    hash_obj = hashlib.sha256(tenant_id.encode('utf-8'))
    return hash_obj.hexdigest()[:12]


def _canonical_json(obj: Any) -> str:
    """Generate canonical JSON string for signatures."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))


def _compute_change_signature(decision_data: Dict[str, Any]) -> str:
    """Compute deterministic signature for change decision."""
    # Create signature pack without the signature field itself
    signature_pack = {
        "allow": decision_data["allow"],
        "reason": decision_data["reason"],
        "applied_version": decision_data["applied_version"],
        "clamp_notes": decision_data["clamp_notes"],
        "audit_event_signature": decision_data.get("audit_event_signature"),
    }
    
    canonical = _canonical_json(signature_pack)
    hash_obj = hashlib.sha256(canonical.encode('utf-8'))
    return hash_obj.hexdigest()


def _parse_version(version: str) -> Optional[tuple]:
    """Parse semantic version string, fail-closed."""
    if not isinstance(version, str) or len(version) > MAX_VERSION_LENGTH:
        return None
    
    match = VERSION_PATTERN.match(version.strip())
    if not match:
        return None
    
    try:
        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3))
        return (major, minor, patch)
    except ValueError:
        return None


def _compare_versions(from_version: str, to_version: str) -> Optional[str]:
    """
    Compare versions and return bump type if valid.
    Returns None if invalid or no bump.
    """
    from_parsed = _parse_version(from_version)
    to_parsed = _parse_version(to_version)
    
    if from_parsed is None or to_parsed is None:
        return None
    
    from_major, from_minor, from_patch = from_parsed
    to_major, to_minor, to_patch = to_parsed
    
    # Check if to_version > from_version
    if (to_major, to_minor, to_patch) <= (from_major, from_minor, from_patch):
        return None
    
    # Determine bump type
    if to_major > from_major:
        return "major"
    elif to_minor > from_minor:
        return "minor"
    elif to_patch > from_patch:
        return "patch"
    else:
        return None


def _validate_version_bump(change_type: ChangeType, from_version: str, to_version: str) -> bool:
    """Validate that version bump meets minimum requirements."""
    bump_type = _compare_versions(from_version, to_version)
    if bump_type is None:
        return False
    
    required_bump = MIN_VERSION_BUMP.get(change_type, "patch")
    
    # Define bump hierarchy
    bump_hierarchy = {"patch": 1, "minor": 2, "major": 3}
    
    actual_level = bump_hierarchy.get(bump_type, 0)
    required_level = bump_hierarchy.get(required_bump, 1)
    
    return actual_level >= required_level


def _parse_change_type(change_type_input: Union[ChangeType, str]) -> Optional[ChangeType]:
    """Parse change type input to ChangeType enum, fail-closed."""
    if isinstance(change_type_input, ChangeType):
        return change_type_input
    
    if not isinstance(change_type_input, str):
        return None
    
    try:
        return ChangeType(change_type_input.upper())
    except ValueError:
        return None


def _sanitize_diff_summary(diff_summary: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Sanitize diff summary to structure-only safe format."""
    if not diff_summary or not isinstance(diff_summary, dict):
        return {}
    
    sanitized = {}
    
    # Limit number of items
    items_processed = 0
    for key, value in diff_summary.items():
        if items_processed >= MAX_DIFF_SUMMARY_ITEMS:
            break
        
        # Only allow safe keys and values
        if (isinstance(key, str) and len(key) <= 40 and 
            key.lower() not in {"prompt", "content", "message", "snippet", "raw", "user_text"}):
            
            if isinstance(value, (int, bool)):
                sanitized[key] = value
            elif isinstance(value, str) and len(value) <= 80:
                # Check for forbidden patterns
                if not any(pattern in value for pattern in ["SENSITIVE_", "SECRET_", "PRIVATE_"]):
                    sanitized[key] = value
                else:
                    sanitized[key] = "REDACTED_TOKEN"
            elif isinstance(value, list) and len(value) <= 10:
                # Sanitize list items
                safe_list = []
                for item in value[:10]:
                    if isinstance(item, str) and len(item) <= 40:
                        if not any(pattern in item for pattern in ["SENSITIVE_", "SECRET_", "PRIVATE_"]):
                            safe_list.append(item)
                        else:
                            safe_list.append("REDACTED_TOKEN")
                    elif isinstance(item, (int, bool)):
                        safe_list.append(item)
                sanitized[key] = safe_list
            else:
                sanitized[key] = "REDACTED_TOKEN"
        
        items_processed += 1
    
    return sanitized


def _generate_change_clamp_notes(sanitized_summary: Dict[str, Any], 
                                rbac_notes: List[str] = None) -> List[str]:
    """Generate bounded clamp notes for change control."""
    notes = []
    
    if rbac_notes:
        notes.extend(rbac_notes[:5])  # Limit RBAC notes
    
    if "REDACTED_TOKEN" in str(sanitized_summary):
        notes.append("DIFF_SUMMARY_REDACTED")
    
    if len(sanitized_summary) >= MAX_DIFF_SUMMARY_ITEMS:
        notes.append("DIFF_SUMMARY_TRUNCATED")
    
    # Ensure notes are safe tokens and bounded
    safe_notes = []
    for note in notes[:MAX_CLAMP_NOTES]:
        if isinstance(note, str) and SAFE_TOKEN_PATTERN.match(note):
            safe_notes.append(note[:MAX_CLAMP_NOTE_LENGTH])
    
    return safe_notes


# ============================================================================
# CHANGE CONTROL API
# ============================================================================

def apply_change_control(tenant_config: TenantConfig,
                        change_req: ChangeRequest,
                        audit_log: AuditLog) -> ChangeDecision:
    """
    Apply change control with RBAC authorization, version validation, and audit recording.
    
    Args:
        tenant_config: Tenant configuration
        change_req: Change control request
        audit_log: Audit log for recording events
    
    Returns:
        ChangeDecision with allow/deny and structured metadata
    """
    try:
        # Validate required fields
        if change_req.now_ms is None:
            return ChangeDecision(
                allow=False,
                reason=ChangeReason.INVALID_REQUEST,
                applied_version="",
                clamp_notes=["MISSING_TIMESTAMP"],
                audit_event_signature=None,
                signature=_compute_change_signature({
                    "allow": False,
                    "reason": ChangeReason.INVALID_REQUEST.value,
                    "applied_version": "",
                    "clamp_notes": ["MISSING_TIMESTAMP"],
                    "audit_event_signature": None,
                })
            )
        
        # Parse change type (fail-closed)
        parsed_change_type = _parse_change_type(change_req.change_type)
        if parsed_change_type is None:
            return ChangeDecision(
                allow=False,
                reason=ChangeReason.INVALID_REQUEST,
                applied_version="",
                clamp_notes=["INVALID_CHANGE_TYPE"],
                audit_event_signature=None,
                signature=_compute_change_signature({
                    "allow": False,
                    "reason": ChangeReason.INVALID_REQUEST.value,
                    "applied_version": "",
                    "clamp_notes": ["INVALID_CHANGE_TYPE"],
                    "audit_event_signature": None,
                })
            )
        
        # Validate version bump
        if not _validate_version_bump(parsed_change_type, change_req.from_version, change_req.to_version):
            return ChangeDecision(
                allow=False,
                reason=ChangeReason.VERSION_NOT_BUMPED,
                applied_version="",
                clamp_notes=["VERSION_BUMP_INVALID"],
                audit_event_signature=None,
                signature=_compute_change_signature({
                    "allow": False,
                    "reason": ChangeReason.VERSION_NOT_BUMPED.value,
                    "applied_version": "",
                    "clamp_notes": ["VERSION_BUMP_INVALID"],
                    "audit_event_signature": None,
                })
            )
        
        # Get required admin operation for this change type
        required_operation = CHANGE_TYPE_TO_OPERATION.get(parsed_change_type)
        if required_operation is None:
            return ChangeDecision(
                allow=False,
                reason=ChangeReason.INTERNAL_INCONSISTENCY,
                applied_version="",
                clamp_notes=["UNKNOWN_OPERATION_MAPPING"],
                audit_event_signature=None,
                signature=_compute_change_signature({
                    "allow": False,
                    "reason": ChangeReason.INTERNAL_INCONSISTENCY.value,
                    "applied_version": "",
                    "clamp_notes": ["UNKNOWN_OPERATION_MAPPING"],
                    "audit_event_signature": None,
                })
            )
        
        # Check RBAC authorization first
        rbac_decision = authorize_admin_action(
            tenant_config=tenant_config,
            actor_role=change_req.actor_role,
            operation=required_operation,
            request_hints=None,  # No hints for change control
            now_ms=change_req.now_ms
        )
        
        if not rbac_decision.allow:
            # Map RBAC reason to change control reason
            if rbac_decision.reason.value in ["TENANT_CAPS_DENY"]:
                change_reason = ChangeReason.TENANT_CAPS_DENY
            else:
                change_reason = ChangeReason.ROLE_NOT_ALLOWED
            
            return ChangeDecision(
                allow=False,
                reason=change_reason,
                applied_version="",
                clamp_notes=rbac_decision.clamp_notes[:MAX_CLAMP_NOTES],
                audit_event_signature=None,
                signature=_compute_change_signature({
                    "allow": False,
                    "reason": change_reason.value,
                    "applied_version": "",
                    "clamp_notes": rbac_decision.clamp_notes[:MAX_CLAMP_NOTES],
                    "audit_event_signature": None,
                })
            )
        
        # Sanitize diff summary
        sanitized_summary = _sanitize_diff_summary(change_req.diff_summary)
        
        # Record audit event (structure-only)
        audit_payload = {
            "tenant_hash": _compute_tenant_hash(change_req.tenant_id),
            "change_type": parsed_change_type.value,
            "from_version": change_req.from_version[:MAX_VERSION_LENGTH],
            "to_version": change_req.to_version[:MAX_VERSION_LENGTH],
            "diff_hash": change_req.diff_hash[:64] if change_req.diff_hash else None,
            "diff_summary": sanitized_summary,
            "actor_role": rbac_decision.derived_limits.get("plan_tier", "UNKNOWN"),  # Use plan tier instead of raw role
        }
        
        try:
            # Record audit event using the proper audit interface
            audit_event = record_audit_event(
                tenant_id=change_req.tenant_id,
                operation=AuditOperationType.GOVERNANCE_OP,  # Use GOVERNANCE_OP instead of non-existent CHANGE_CONTROL
                decision=AuditDecision.ALLOW,
                reason=AuditReasonCode.INTERNAL_INCONSISTENCY,  # Use a valid reason code (will be overridden by payload)
                payload=audit_payload,
                now_ms=change_req.now_ms,
                log=audit_log
            )
            
            audit_event_signature = audit_event.signature
            
        except Exception:
            # Fail-closed if audit write fails
            return ChangeDecision(
                allow=False,
                reason=ChangeReason.AUDIT_WRITE_FAILED,
                applied_version="",
                clamp_notes=["AUDIT_APPEND_FAILED"],
                audit_event_signature=None,
                signature=_compute_change_signature({
                    "allow": False,
                    "reason": ChangeReason.AUDIT_WRITE_FAILED.value,
                    "applied_version": "",
                    "clamp_notes": ["AUDIT_APPEND_FAILED"],
                    "audit_event_signature": None,
                })
            )
        
        # Success case
        clamp_notes = _generate_change_clamp_notes(sanitized_summary, rbac_decision.clamp_notes)
        
        decision_data = {
            "allow": True,
            "reason": ChangeReason.OK.value,
            "applied_version": change_req.to_version[:MAX_VERSION_LENGTH],
            "clamp_notes": clamp_notes,
            "audit_event_signature": audit_event_signature,
        }
        
        return ChangeDecision(
            allow=True,
            reason=ChangeReason.OK,
            applied_version=change_req.to_version[:MAX_VERSION_LENGTH],
            clamp_notes=clamp_notes,
            audit_event_signature=audit_event_signature,
            signature=_compute_change_signature(decision_data)
        )
        
    except Exception:
        # Fail-closed on any unexpected error
        return ChangeDecision(
            allow=False,
            reason=ChangeReason.INTERNAL_INCONSISTENCY,
            applied_version="",
            clamp_notes=["EXCEPTION_CAUGHT"],
            audit_event_signature=None,
            signature=_compute_change_signature({
                "allow": False,
                "reason": ChangeReason.INTERNAL_INCONSISTENCY.value,
                "applied_version": "",
                "clamp_notes": ["EXCEPTION_CAUGHT"],
                "audit_event_signature": None,
            })
        )
