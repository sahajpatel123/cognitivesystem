"""
Phase 20 Step 5: Export & Audit Package Generator (Redacted + Versioned)

Implements enterprise export bundle that enables auditing/debugging without
exporting raw user text or memory/research content. All exports are verifiably
text-free, deterministic, and versioned.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
import json
import hashlib
import re
from copy import deepcopy

# Import existing governance components
from .tenant import TenantConfig, PlanTier, resolve_tenant_caps


# ============================================================================
# CONSTANTS
# ============================================================================

EXPORT_VERSION = "20.5.0"

# Bounds
MAX_BUNDLE_SIZE_KB = 40
MAX_AUDIT_EVENTS = 200
MAX_DOMAINS = 64
MAX_SIGNATURES = 128
MAX_HISTOGRAM_KEYS = 32
MAX_STRING_LENGTH = 100
MAX_LIST_LENGTH = 64
MAX_DICT_KEYS = 64

# Time constants
HOUR_MS = 60 * 60 * 1000
DEFAULT_BUCKET_MS = HOUR_MS

# Forbidden keys for sanitization
FORBIDDEN_KEY_PATTERNS = frozenset([
    "user", "prompt", "message", "content", "snippet", "quote", "raw", "text", 
    "body", "email", "phone", "address", "token", "secret", "tool_output",
    "response", "answer", "memory_value", "transcript", "excerpt"
])

# Forbidden value patterns
FORBIDDEN_VALUE_PATTERNS = [
    r"SENSITIVE_",
    r"SECRET_", 
    r"PRIVATE_",
    r"ignore previous instructions",
    r"^>.*",  # Markdown quotes
    r"^From:",
    r"^Subject:",
]

# Allowed patterns
ENUM_PATTERN = re.compile(r"^[A-Z0-9_]{1,40}$")
DOMAIN_PATTERN = re.compile(r"^[a-z0-9.-]{1,50}$")
HASH_PATTERN = re.compile(r"^[a-f0-9]{64}$")


# ============================================================================
# ENUMS
# ============================================================================

class ExportReasonCode(Enum):
    """Exhaustive list of export reason codes. NO OTHER."""
    OK = "OK"
    EXPORT_DISABLED = "EXPORT_DISABLED"
    TENANT_INVALID = "TENANT_INVALID"
    AUDIT_UNAVAILABLE = "AUDIT_UNAVAILABLE"
    POLICY_UNAVAILABLE = "POLICY_UNAVAILABLE"
    SANITIZE_FAILED = "SANITIZE_FAILED"
    BUNDLE_TOO_LARGE = "BUNDLE_TOO_LARGE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass(frozen=True)
class ExportBundle:
    """Structure-only export bundle with versioned schema."""
    export_version: str
    generated_at_bucket_ms: int
    tenant_hash: str
    policy_versions: Dict[str, str]
    tenant_snapshot: Dict[str, Any]
    audit_events: List[Dict[str, Any]]
    signatures: Dict[str, List[str]]
    metrics: Dict[str, Any]
    export_signature: str
    diagnostics: Dict[str, Any]
    encryption: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with stable ordering."""
        return {
            "export_version": self.export_version,
            "generated_at_bucket_ms": self.generated_at_bucket_ms,
            "tenant_hash": self.tenant_hash,
            "policy_versions": dict(sorted(self.policy_versions.items())),
            "tenant_snapshot": _sort_dict_recursively(self.tenant_snapshot),
            "audit_events": [_sort_dict_recursively(event) for event in self.audit_events],
            "signatures": {k: sorted(v) for k, v in sorted(self.signatures.items())},
            "metrics": _sort_dict_recursively(self.metrics),
            "export_signature": self.export_signature,
            "diagnostics": _sort_dict_recursively(self.diagnostics),
            "encryption": _sort_dict_recursively(self.encryption),
        }


@dataclass(frozen=True)
class ExportOutcome:
    """Result of export bundle generation."""
    ok: bool
    reason_code: ExportReasonCode
    bundle: Optional[ExportBundle]
    signature: str
    telemetry: Dict[str, Any]


# ============================================================================
# SANITIZATION AND REDACTION
# ============================================================================

def _is_forbidden_key(key: str) -> bool:
    """Check if key contains forbidden patterns."""
    if not isinstance(key, str):
        return True
    
    key_lower = key.lower()
    for pattern in FORBIDDEN_KEY_PATTERNS:
        if pattern in key_lower:
            return True
    
    return False


def _is_forbidden_value(value: str) -> bool:
    """Check if value contains forbidden patterns."""
    if not isinstance(value, str):
        return False
    
    for pattern in FORBIDDEN_VALUE_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            return True
    
    return False


def _is_safe_string(value: str) -> bool:
    """Check if string is safe for export."""
    if not isinstance(value, str):
        return False
    
    if len(value) == 0:
        return True
    
    # Check forbidden patterns first
    if _is_forbidden_value(value):
        return False
    
    # Check allowed patterns
    if ENUM_PATTERN.match(value):
        return True
    if DOMAIN_PATTERN.match(value):
        return True
    if HASH_PATTERN.match(value):
        return True
    
    # Allow simple alphanumeric strings
    if re.match(r'^[a-zA-Z0-9_-]+$', value) and len(value) <= MAX_STRING_LENGTH:
        return True
    
    return False


def _sanitize_string(value: str) -> str:
    """Sanitize string value for export."""
    if not isinstance(value, str):
        return "REDACTED_TOKEN"
    
    # Truncate if too long
    if len(value) > MAX_STRING_LENGTH:
        value = value[:MAX_STRING_LENGTH]
    
    # Check if safe
    if _is_safe_string(value):
        return value
    
    return "REDACTED_TOKEN"


def _extract_domain_from_url(url: str) -> str:
    """Extract domain from URL for safe export."""
    if not isinstance(url, str):
        return "REDACTED_DOMAIN"
    
    # Simple domain extraction
    if "://" in url:
        try:
            domain_part = url.split("://")[1].split("/")[0].split("?")[0]
            if ":" in domain_part:
                domain_part = domain_part.split(":")[0]
            if DOMAIN_PATTERN.match(domain_part.lower()):
                return domain_part.lower()
        except (IndexError, AttributeError):
            pass
    
    return "REDACTED_DOMAIN"


def _sanitize_export_payload(data: Any, depth: int = 0) -> Tuple[Any, int, int, bool]:
    """
    Sanitize payload recursively for export.
    Returns: (sanitized_data, dropped_keys_count, redacted_values_count, had_forbidden_keys)
    """
    dropped_keys = 0
    redacted_values = 0
    had_forbidden = False
    
    if depth > 6:  # Max nesting depth
        return "DEPTH_EXCEEDED", dropped_keys, redacted_values + 1, had_forbidden
    
    if isinstance(data, dict):
        sanitized = {}
        keys_processed = 0
        
        for key, value in data.items():
            if keys_processed >= MAX_DICT_KEYS:
                dropped_keys += len(data) - keys_processed
                break
            
            # Check for forbidden keys
            if _is_forbidden_key(key):
                had_forbidden = True
                dropped_keys += 1
                continue
            
            # Sanitize key
            safe_key = _sanitize_string(str(key))
            if safe_key == "REDACTED_TOKEN":
                dropped_keys += 1
                continue
            
            # Recursively sanitize value
            sanitized_value, sub_dropped, sub_redacted, sub_forbidden = _sanitize_export_payload(value, depth + 1)
            dropped_keys += sub_dropped
            redacted_values += sub_redacted
            had_forbidden = had_forbidden or sub_forbidden
            
            sanitized[safe_key] = sanitized_value
            keys_processed += 1
        
        return sanitized, dropped_keys, redacted_values, had_forbidden
    
    elif isinstance(data, list):
        sanitized = []
        for i, item in enumerate(data):
            if i >= MAX_LIST_LENGTH:
                dropped_keys += len(data) - i
                break
            
            sanitized_item, sub_dropped, sub_redacted, sub_forbidden = _sanitize_export_payload(item, depth + 1)
            dropped_keys += sub_dropped
            redacted_values += sub_redacted
            had_forbidden = had_forbidden or sub_forbidden
            sanitized.append(sanitized_item)
        
        return sanitized, dropped_keys, redacted_values, had_forbidden
    
    elif isinstance(data, str):
        # Special handling for URLs
        if "://" in data:
            domain = _extract_domain_from_url(data)
            if domain != "REDACTED_DOMAIN":
                return domain, dropped_keys, redacted_values, had_forbidden
            else:
                return "REDACTED_TOKEN", dropped_keys, redacted_values + 1, had_forbidden
        
        sanitized_str = _sanitize_string(data)
        if sanitized_str == "REDACTED_TOKEN" and data != "REDACTED_TOKEN":
            redacted_values += 1
        return sanitized_str, dropped_keys, redacted_values, had_forbidden
    
    elif isinstance(data, (int, bool)):
        return data, dropped_keys, redacted_values, had_forbidden
    
    elif isinstance(data, float):
        # Round floats deterministically
        try:
            return int(round(data)), dropped_keys, redacted_values, had_forbidden
        except (ValueError, OverflowError):
            return 0, dropped_keys, redacted_values + 1, had_forbidden
    
    elif data is None:
        return None, dropped_keys, redacted_values, had_forbidden
    
    else:
        # Unknown type
        return "REDACTED_TOKEN", dropped_keys, redacted_values + 1, had_forbidden


def sanitize_export_payload(obj: Any) -> Dict[str, Any]:
    """Sanitize payload for export with structure-only guarantees."""
    try:
        sanitized_obj, dropped_keys, redacted_values, had_forbidden = _sanitize_export_payload(obj)
        
        if not isinstance(sanitized_obj, dict):
            sanitized_obj = {"sanitized_root": sanitized_obj}
        
        # Add diagnostics
        sanitized_obj["_sanitize_stats"] = {
            "dropped_keys_count": dropped_keys,
            "redacted_values_count": redacted_values,
            "had_forbidden_keys": had_forbidden
        }
        
        return sanitized_obj
    
    except Exception:
        # Fail-closed: return minimal safe structure
        return {
            "sanitize_error": True,
            "_sanitize_stats": {
                "dropped_keys_count": 0,
                "redacted_values_count": 0,
                "had_forbidden_keys": False
            }
        }


# ============================================================================
# CANONICALIZATION AND SIGNING
# ============================================================================

def _sort_dict_recursively(obj: Any) -> Any:
    """Sort dictionary keys recursively for canonical representation."""
    if isinstance(obj, dict):
        return {key: _sort_dict_recursively(value) for key, value in sorted(obj.items())}
    elif isinstance(obj, list):
        return [_sort_dict_recursively(item) for item in obj]
    else:
        return obj


def canonical_json(obj: Any) -> str:
    """Create canonical JSON representation."""
    sorted_obj = _sort_dict_recursively(obj)
    return json.dumps(sorted_obj, sort_keys=True, separators=(',', ':'))


def canonical_json_bytes(obj: Any) -> bytes:
    """Create canonical JSON as bytes."""
    return canonical_json(obj).encode('utf-8')


def compute_export_signature(bundle_struct: Dict[str, Any]) -> str:
    """Compute deterministic signature for export bundle."""
    # Exclude signature field itself
    bundle_for_signing = {k: v for k, v in bundle_struct.items() if k != "export_signature"}
    canonical = canonical_json(bundle_for_signing)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def compute_tenant_hash(tenant_id: str) -> str:
    """Compute SHA256 hash of tenant_id for privacy."""
    if not isinstance(tenant_id, str):
        tenant_id = str(tenant_id)
    return hashlib.sha256(tenant_id.encode('utf-8')).hexdigest()


def compute_bucket_start(now_ms: int, bucket_ms: int = DEFAULT_BUCKET_MS) -> int:
    """Compute bucket start time for deterministic bucketing."""
    return (now_ms // bucket_ms) * bucket_ms


# ============================================================================
# EXPORT BUILDER
# ============================================================================

def build_export_bundle(
    tenant_config: TenantConfig,
    request_flags: Optional[Dict[str, Any]] = None,
    audit_events: Optional[List[Dict[str, Any]]] = None,
    policy_decisions: Optional[List[Dict[str, Any]]] = None,
    memory_telemetry_events: Optional[List[Dict[str, Any]]] = None,
    research_telemetry_events: Optional[List[Dict[str, Any]]] = None,
    now_ms: int = 0,
    export_version: str = EXPORT_VERSION,
    encryption: Optional[Dict[str, Any]] = None
) -> ExportOutcome:
    """
    Build export bundle with fail-closed behavior.
    
    Args:
        tenant_config: Tenant configuration
        request_flags: Optional request flags (structure-only)
        audit_events: Optional audit events from governance/audit.py
        policy_decisions: Optional policy decisions
        memory_telemetry_events: Optional memory telemetry
        research_telemetry_events: Optional research telemetry
        now_ms: Current timestamp in milliseconds
        export_version: Export version string
        encryption: Optional encryption metadata (stub)
    
    Returns:
        ExportOutcome with bundle or failure reason
    """
    try:
        # Validate tenant config
        if tenant_config is None:
            return _create_fail_outcome(ExportReasonCode.TENANT_INVALID, now_ms)
        
        # Check export eligibility
        try:
            caps = resolve_tenant_caps(tenant_config)
            if not caps.export_allowed:
                return _create_fail_outcome(ExportReasonCode.EXPORT_DISABLED, now_ms)
        except Exception:
            return _create_fail_outcome(ExportReasonCode.TENANT_INVALID, now_ms)
        
        # Compute privacy-preserving fields
        tenant_hash = compute_tenant_hash(tenant_config.tenant_id)
        generated_at_bucket_ms = compute_bucket_start(now_ms)
        
        # Build policy versions
        policy_versions = {
            "phase16": "UNKNOWN",
            "phase18": "UNKNOWN", 
            "phase19": "UNKNOWN",
            "phase20": "20.0.0"
        }
        
        # Build tenant snapshot (structure-only)
        tenant_snapshot = {
            "plan": tenant_config.plan.value,
            "regions": sorted(tenant_config.regions[:MAX_DOMAINS]),
            "enabled_features": sorted([f.value for f in tenant_config.enabled_features]),
            "resolved_caps": {
                "allowed_tools": sorted([t.value for t in caps.allowed_tools]),
                "deepthink_max_passes": caps.deepthink_max_passes,
                "memory_ttl_cap": caps.memory_ttl_cap.value if hasattr(caps.memory_ttl_cap, 'value') else str(caps.memory_ttl_cap),
                "memory_max_facts_per_request": caps.memory_max_facts_per_request,
                "export_allowed": caps.export_allowed
            }
        }
        
        # Process audit events (structure-only)
        processed_audit_events = []
        if audit_events:
            # Sort events deterministically before processing
            sorted_events = sorted(audit_events, key=lambda e: (
                e.get("timestamp_ms", 0),
                e.get("event_id", ""),
                e.get("operation", ""),
                str(e)  # Fallback for complete determinism
            ))
            
            for event in sorted_events[:MAX_AUDIT_EVENTS]:
                safe_event, _, _, _ = _sanitize_export_payload(event)
                if isinstance(safe_event, dict):
                    # Keep only allowlisted fields
                    filtered_event = {}
                    for key in ["timestamp_ms", "operation", "decision", "reason", "signature", "event_id"]:
                        if key in safe_event:
                            filtered_event[key] = safe_event[key]
                    if filtered_event:
                        processed_audit_events.append(filtered_event)
        
        # Collect signatures (hashes only)
        signatures = {
            "decision_signatures": [],
            "research_signatures": [],
            "memory_signatures": []
        }
        
        if policy_decisions:
            for decision in policy_decisions[:MAX_SIGNATURES]:
                if isinstance(decision, dict) and "signature" in decision:
                    sig = str(decision["signature"])
                    if HASH_PATTERN.match(sig):
                        signatures["decision_signatures"].append(sig)
        
        # Build metrics (bounded histograms/tallies)
        metrics = {
            "tool_calls_count": 0,
            "domains_used": [],
            "grade_histogram": {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "UNKNOWN": 0},
            "stop_reason_histogram": {},
            "memory_write_counts": {"attempted": 0, "accepted": 0, "rejected": 0},
            "rejection_reason_histogram": {},
            "ttl_class_histogram": {"TTL_1H": 0, "TTL_1D": 0, "TTL_10D": 0},
            "bundle_size_bucket": "0"
        }
        
        # Process telemetry events for metrics
        if memory_telemetry_events:
            for event in memory_telemetry_events:
                if isinstance(event, dict):
                    if event.get("operation") == "write":
                        metrics["memory_write_counts"]["attempted"] += 1
                        if event.get("success"):
                            metrics["memory_write_counts"]["accepted"] += 1
                        else:
                            metrics["memory_write_counts"]["rejected"] += 1
        
        # Build encryption metadata (stub)
        encryption_meta = {
            "enabled": False,
            "algorithm": "NONE",
            "key_id_hash": "",
            "encrypted_payload_hash": ""
        }
        if encryption:
            safe_encryption, _, _, _ = _sanitize_export_payload(encryption)
            if isinstance(safe_encryption, dict):
                encryption_meta.update(safe_encryption)
        
        # Build diagnostics
        diagnostics = {
            "dropped_fields_count": 0,
            "had_forbidden_keys": False,
            "sanitize_reason_codes": [],
            "failure_reasons": []
        }
        
        # Create bundle structure for signing
        bundle_struct = {
            "export_version": export_version,
            "generated_at_bucket_ms": generated_at_bucket_ms,
            "tenant_hash": tenant_hash,
            "policy_versions": policy_versions,
            "tenant_snapshot": tenant_snapshot,
            "audit_events": processed_audit_events,
            "signatures": signatures,
            "metrics": metrics,
            "diagnostics": diagnostics,
            "encryption": encryption_meta
        }
        
        # Compute signature
        export_signature = compute_export_signature(bundle_struct)
        
        # Create final bundle
        bundle = ExportBundle(
            export_version=export_version,
            generated_at_bucket_ms=generated_at_bucket_ms,
            tenant_hash=tenant_hash,
            policy_versions=policy_versions,
            tenant_snapshot=tenant_snapshot,
            audit_events=processed_audit_events,
            signatures=signatures,
            metrics=metrics,
            export_signature=export_signature,
            diagnostics=diagnostics,
            encryption=encryption_meta
        )
        
        # Check bundle size
        bundle_json = canonical_json(bundle.as_dict())
        bundle_size_kb = len(bundle_json.encode('utf-8')) / 1024
        
        if bundle_size_kb > MAX_BUNDLE_SIZE_KB:
            return _create_fail_outcome(ExportReasonCode.BUNDLE_TOO_LARGE, now_ms)
        
        # Create telemetry
        telemetry = {
            "bundle_size_kb": int(bundle_size_kb),
            "audit_events_count": len(processed_audit_events),
            "signatures_count": sum(len(sigs) for sigs in signatures.values()),
            "generation_time_bucket_ms": generated_at_bucket_ms
        }
        
        return ExportOutcome(
            ok=True,
            reason_code=ExportReasonCode.OK,
            bundle=bundle,
            signature=export_signature,
            telemetry=telemetry
        )
    
    except Exception:
        # Fail-closed: return safe error outcome
        return _create_fail_outcome(ExportReasonCode.INTERNAL_ERROR, now_ms)


def _create_fail_outcome(reason: ExportReasonCode, now_ms: int) -> ExportOutcome:
    """Create fail-closed export outcome."""
    bucket_ms = compute_bucket_start(now_ms)
    
    telemetry = {
        "bundle_size_kb": 0,
        "audit_events_count": 0,
        "signatures_count": 0,
        "generation_time_bucket_ms": bucket_ms,
        "failure_reason": reason.value
    }
    
    return ExportOutcome(
        ok=False,
        reason_code=reason,
        bundle=None,
        signature="",
        telemetry=telemetry
    )
