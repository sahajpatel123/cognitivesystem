"""
Phase 20 Step 4: Retention + Deletion Policy (Tiered, Enforced)

Implements deterministic retention windows and deletion workflows across:
- audit logs (Phase 20)
- telemetry (Phase 18/19/20)
- memory logs (Phase 19 TTL-driven)
- research cache (Phase 18 cache TTL-driven)

All operations are structure-only, deterministic, and fail-closed.
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

# Bounds
MAX_CANDIDATES_PROCESSED = 512
MAX_TARGETS_RETURNED = 256
MAX_OPS_PER_RUN = 256
MAX_DICT_KEYS = 64
MAX_LIST_LENGTH = 64
MAX_STRING_LENGTH = 100

# Time constants (milliseconds)
HOUR_MS = 60 * 60 * 1000
DAY_MS = 24 * HOUR_MS
WEEK_MS = 7 * DAY_MS

# Safety margin for memory TTL interlock
MEMORY_SAFETY_MARGIN_MS = HOUR_MS  # 1 hour safety buffer

# Default bucket size for time bucketing
DEFAULT_BUCKET_MS = HOUR_MS

# Forbidden keys for sanitization (similar to audit patterns)
FORBIDDEN_KEY_PATTERNS = frozenset([
    "user", "prompt", "message", "text", "content", "body", "snippet", "excerpt",
    "quote", "tool_output", "response", "answer", "memory_value", "raw", "transcript"
])

# TTL label to milliseconds mapping (from Phase 19 concepts)
TTL_LABEL_TO_MS = {
    "TTL_1H": HOUR_MS,
    "TTL_1D": DAY_MS,
    "TTL_10D": 10 * DAY_MS,
}

# Shortest retention windows (fail-closed defaults)
SHORTEST_RETENTION_MS = {
    "AUDIT_LOG": 7 * DAY_MS,      # 7 days
    "TELEMETRY": 3 * DAY_MS,      # 3 days
    "MEMORY_EVENT_LOG": DAY_MS,   # 1 day
    "RESEARCH_CACHE": HOUR_MS,    # 1 hour
}


# ============================================================================
# ENUMS
# ============================================================================

class ArtifactType(Enum):
    """Governed artifact types for retention policy."""
    AUDIT_LOG = "AUDIT_LOG"
    TELEMETRY = "TELEMETRY"
    MEMORY_EVENT_LOG = "MEMORY_EVENT_LOG"
    RESEARCH_CACHE = "RESEARCH_CACHE"


class RetentionReasonCode(Enum):
    """Exhaustive list of retention decision reason codes. NO OTHER."""
    OK = "OK"
    POLICY_DISABLED = "POLICY_DISABLED"
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_TENANT = "INVALID_TENANT"
    UNKNOWN_ARTIFACT_TYPE = "UNKNOWN_ARTIFACT_TYPE"
    POLICY_MISSING_FAIL_CLOSED = "POLICY_MISSING_FAIL_CLOSED"
    LIMIT_CLAMPED = "LIMIT_CLAMPED"
    INTERNAL_INCONSISTENCY = "INTERNAL_INCONSISTENCY"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass(frozen=True)
class DeletionTarget:
    """Structure-only identifier for deletion target."""
    artifact_type: ArtifactType
    tenant_hash: str  # SHA256 of tenant_id for privacy
    eligible_bucket_ms: int
    target_key_hash: str  # SHA256 of target identifier
    
    def sort_key(self) -> Tuple[str, str, int, str]:
        """Deterministic sort key for stable ordering."""
        return (
            self.artifact_type.value,
            self.tenant_hash,
            self.eligible_bucket_ms,
            self.target_key_hash
        )


@dataclass(frozen=True)
class DeletionPlan:
    """Deterministic deletion plan with structure-only fields."""
    allowed: bool
    reason: RetentionReasonCode
    targets: List[DeletionTarget]
    counts_by_type: Dict[str, int]
    effective_retention_windows: Dict[str, int]  # artifact_type -> retention_ms
    bucket_start_ms: int
    max_ops_per_run: int
    signature: str
    
    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with stable ordering."""
        return {
            "allowed": self.allowed,
            "reason": self.reason.value,
            "targets": [
                {
                    "artifact_type": target.artifact_type.value,
                    "tenant_hash": target.tenant_hash,
                    "eligible_bucket_ms": target.eligible_bucket_ms,
                    "target_key_hash": target.target_key_hash,
                }
                for target in sorted(self.targets, key=lambda t: t.sort_key())
            ],
            "counts_by_type": dict(sorted(self.counts_by_type.items())),
            "effective_retention_windows": dict(sorted(self.effective_retention_windows.items())),
            "bucket_start_ms": self.bucket_start_ms,
            "max_ops_per_run": self.max_ops_per_run,
            "signature": self.signature,
        }


@dataclass
class CandidateRecord:
    """Structure-only candidate record for retention evaluation."""
    artifact_type: ArtifactType
    tenant_id: str
    record_id: str
    timestamp_ms: int
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# SANITIZATION AND REDACTION
# ============================================================================

def _has_forbidden_key(key: str) -> bool:
    """Check if key contains forbidden patterns."""
    if not isinstance(key, str):
        return True
    
    key_lower = key.lower()
    for pattern in FORBIDDEN_KEY_PATTERNS:
        if pattern in key_lower:
            return True
    
    return False


def _is_safe_string(value: str) -> bool:
    """Check if string is safe (no sensitive patterns)."""
    if not isinstance(value, str):
        return False
    
    if len(value) == 0:
        return True
    
    # Check for sentinel patterns (must be rejected)
    if "SENSITIVE_" in value or "SECRET_" in value or "PRIVATE_" in value:
        return False
    
    # Allow simple alphanumeric strings with underscores and hyphens
    if re.match(r'^[a-zA-Z0-9_-]+$', value) and len(value) <= MAX_STRING_LENGTH:
        return True
    
    return False


def _sanitize_string(value: str) -> str:
    """Sanitize string value."""
    if not isinstance(value, str):
        return "REDACTED_TOKEN"
    
    # Truncate if too long
    if len(value) > MAX_STRING_LENGTH:
        value = value[:MAX_STRING_LENGTH]
    
    # Check if safe
    if _is_safe_string(value):
        return value
    
    return "REDACTED_TOKEN"


def _sanitize_dict_recursively(data: Any, depth: int = 0) -> Tuple[Any, int, int]:
    """
    Sanitize dictionary recursively.
    Returns: (sanitized_data, dropped_keys_count, redacted_values_count)
    """
    dropped_keys = 0
    redacted_values = 0
    
    if depth > 6:  # Max nesting depth
        return "DEPTH_EXCEEDED", dropped_keys, redacted_values + 1
    
    if isinstance(data, dict):
        sanitized = {}
        keys_processed = 0
        
        for key, value in data.items():
            if keys_processed >= MAX_DICT_KEYS:
                dropped_keys += len(data) - keys_processed
                break
            
            # Check for forbidden keys
            if _has_forbidden_key(key):
                dropped_keys += 1
                continue
            
            # Sanitize key
            safe_key = _sanitize_string(str(key))
            if safe_key == "REDACTED_TOKEN":
                dropped_keys += 1
                continue
            
            # Recursively sanitize value
            sanitized_value, sub_dropped, sub_redacted = _sanitize_dict_recursively(value, depth + 1)
            dropped_keys += sub_dropped
            redacted_values += sub_redacted
            
            sanitized[safe_key] = sanitized_value
            keys_processed += 1
        
        return sanitized, dropped_keys, redacted_values
    
    elif isinstance(data, list):
        sanitized = []
        for i, item in enumerate(data):
            if i >= MAX_LIST_LENGTH:
                dropped_keys += len(data) - i
                break
            
            sanitized_item, sub_dropped, sub_redacted = _sanitize_dict_recursively(item, depth + 1)
            dropped_keys += sub_dropped
            redacted_values += sub_redacted
            sanitized.append(sanitized_item)
        
        return sanitized, dropped_keys, redacted_values
    
    elif isinstance(data, str):
        sanitized_str = _sanitize_string(data)
        if sanitized_str == "REDACTED_TOKEN" and data != "REDACTED_TOKEN":
            redacted_values += 1
        return sanitized_str, dropped_keys, redacted_values
    
    elif isinstance(data, (int, bool)):
        return data, dropped_keys, redacted_values
    
    elif isinstance(data, float):
        # Round floats deterministically
        try:
            return int(round(data)), dropped_keys, redacted_values
        except (ValueError, OverflowError):
            return 0, dropped_keys, redacted_values + 1
    
    elif data is None:
        return None, dropped_keys, redacted_values
    
    else:
        # Unknown type
        return "REDACTED_TOKEN", dropped_keys, redacted_values + 1


def sanitize_candidate_record(record: CandidateRecord) -> CandidateRecord:
    """Sanitize candidate record to remove forbidden content."""
    try:
        sanitized_metadata, _, _ = _sanitize_dict_recursively(record.metadata)
        
        return CandidateRecord(
            artifact_type=record.artifact_type,
            tenant_id=record.tenant_id,  # Will be hashed later
            record_id=_sanitize_string(record.record_id),
            timestamp_ms=record.timestamp_ms,
            metadata=sanitized_metadata if isinstance(sanitized_metadata, dict) else {}
        )
    except Exception:
        # Fail-closed: return minimal safe record
        return CandidateRecord(
            artifact_type=record.artifact_type,
            tenant_id=record.tenant_id,
            record_id="SANITIZE_ERROR",
            timestamp_ms=record.timestamp_ms,
            metadata={"sanitize_error": True}
        )


def assert_no_text_leakage(data: Any, context: str = ""):
    """Assert that no sentinel strings appear in data."""
    sentinel_strings = ["SENSITIVE_USER_TEXT_123", "SENSITIVE_USER_TEXT_456"]
    serialized = json.dumps(data) if not isinstance(data, str) else data
    
    for sentinel in sentinel_strings:
        if sentinel in serialized:
            raise AssertionError(f"Sentinel string '{sentinel}' found in {context}: {serialized}")


# ============================================================================
# RETENTION WINDOWS
# ============================================================================

def compute_tenant_hash(tenant_id: str) -> str:
    """Compute SHA256 hash of tenant_id for privacy."""
    if not isinstance(tenant_id, str):
        tenant_id = str(tenant_id)
    return hashlib.sha256(tenant_id.encode('utf-8')).hexdigest()


def compute_bucket_start(now_ms: int, bucket_ms: int = DEFAULT_BUCKET_MS) -> int:
    """Compute bucket start time for deterministic bucketing."""
    return (now_ms // bucket_ms) * bucket_ms


def get_retention_windows(tenant_config: Optional[TenantConfig]) -> Dict[str, int]:
    """
    Get retention windows for all artifact types based on tenant configuration.
    Returns fail-closed shortest retention if tenant config is invalid.
    """
    if tenant_config is None:
        return SHORTEST_RETENTION_MS.copy()
    
    try:
        caps = resolve_tenant_caps(tenant_config)
        
        # Derive retention windows from tenant plan
        if tenant_config.plan == PlanTier.FREE:
            return {
                "AUDIT_LOG": 7 * DAY_MS,      # 7 days
                "TELEMETRY": 3 * DAY_MS,      # 3 days
                "MEMORY_EVENT_LOG": DAY_MS,   # 1 day
                "RESEARCH_CACHE": HOUR_MS,    # 1 hour
            }
        elif tenant_config.plan == PlanTier.PRO:
            return {
                "AUDIT_LOG": 30 * DAY_MS,     # 30 days
                "TELEMETRY": 14 * DAY_MS,     # 14 days
                "MEMORY_EVENT_LOG": 7 * DAY_MS,  # 7 days
                "RESEARCH_CACHE": 6 * HOUR_MS,   # 6 hours
            }
        elif tenant_config.plan == PlanTier.MAX:
            return {
                "AUDIT_LOG": 90 * DAY_MS,     # 90 days
                "TELEMETRY": 30 * DAY_MS,     # 30 days
                "MEMORY_EVENT_LOG": 14 * DAY_MS, # 14 days
                "RESEARCH_CACHE": 24 * HOUR_MS,  # 24 hours
            }
        elif tenant_config.plan == PlanTier.ENTERPRISE:
            return {
                "AUDIT_LOG": 365 * DAY_MS,    # 365 days
                "TELEMETRY": 90 * DAY_MS,     # 90 days
                "MEMORY_EVENT_LOG": 30 * DAY_MS, # 30 days
                "RESEARCH_CACHE": 7 * DAY_MS,    # 7 days
            }
        else:
            # Unknown plan - fail closed
            return SHORTEST_RETENTION_MS.copy()
    
    except Exception:
        # Fail-closed: use shortest retention
        return SHORTEST_RETENTION_MS.copy()


def get_memory_ttl_cutoff(tenant_config: Optional[TenantConfig], now_ms: int) -> int:
    """
    Get conservative cutoff for memory event pruning based on TTL policy.
    Returns timestamp_ms before which memory events can be safely pruned.
    """
    if tenant_config is None:
        # Fail-closed: very conservative cutoff
        return now_ms - (DAY_MS + MEMORY_SAFETY_MARGIN_MS)
    
    try:
        caps = resolve_tenant_caps(tenant_config)
        
        # Get maximum TTL for this tenant plan
        ttl_label = caps.memory_ttl_cap.value if hasattr(caps.memory_ttl_cap, 'value') else str(caps.memory_ttl_cap)
        max_ttl_ms = TTL_LABEL_TO_MS.get(ttl_label, DAY_MS)  # Default to 1 day if unknown
        
        # Conservative cutoff: now - (max_ttl + safety_margin)
        cutoff_ms = now_ms - (max_ttl_ms + MEMORY_SAFETY_MARGIN_MS)
        
        return cutoff_ms
    
    except Exception:
        # Fail-closed: very conservative cutoff
        return now_ms - (DAY_MS + MEMORY_SAFETY_MARGIN_MS)


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


def compute_plan_signature(plan_data: Dict[str, Any]) -> str:
    """Compute deterministic signature for deletion plan."""
    canonical = canonical_json(plan_data)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


# ============================================================================
# DELETION PLANNER
# ============================================================================

def create_deletion_plan(
    tenant_config: Optional[TenantConfig],
    artifact_type: ArtifactType,
    candidates: List[CandidateRecord],
    now_ms: int,
    bucket_ms: int = DEFAULT_BUCKET_MS,
    max_ops_per_run: Optional[int] = None
) -> DeletionPlan:
    """
    Create deterministic deletion plan for given artifact type and candidates.
    
    Args:
        tenant_config: Tenant configuration (None triggers fail-closed)
        artifact_type: Type of artifact to plan deletion for
        candidates: List of candidate records to evaluate
        now_ms: Current timestamp in milliseconds
        bucket_ms: Time bucket size for deterministic bucketing
        max_ops_per_run: Maximum operations per run (policy-derived)
    
    Returns:
        DeletionPlan with deterministic ordering and signature
    """
    try:
        # Validate inputs
        if not isinstance(artifact_type, ArtifactType):
            return _create_fail_closed_plan(
                RetentionReasonCode.UNKNOWN_ARTIFACT_TYPE,
                now_ms, bucket_ms, max_ops_per_run or MAX_OPS_PER_RUN
            )
        
        if tenant_config is None:
            return _create_fail_closed_plan(
                RetentionReasonCode.POLICY_MISSING_FAIL_CLOSED,
                now_ms, bucket_ms, max_ops_per_run or MAX_OPS_PER_RUN
            )
        
        # Get retention windows
        retention_windows = get_retention_windows(tenant_config)
        
        # Determine effective max_ops_per_run
        effective_max_ops = min(max_ops_per_run or MAX_OPS_PER_RUN, MAX_OPS_PER_RUN)
        
        # Compute bucket start
        bucket_start_ms = compute_bucket_start(now_ms, bucket_ms)
        
        # Get retention window for this artifact type
        artifact_key = artifact_type.value
        retention_ms = retention_windows.get(artifact_key, SHORTEST_RETENTION_MS[artifact_key])
        
        # Compute cutoff timestamp
        cutoff_ms = bucket_start_ms - retention_ms
        
        # Special handling for memory events (TTL interlock)
        if artifact_type == ArtifactType.MEMORY_EVENT_LOG:
            memory_cutoff_ms = get_memory_ttl_cutoff(tenant_config, now_ms)
            cutoff_ms = min(cutoff_ms, memory_cutoff_ms)  # More conservative
        
        # Process candidates (bounded)
        processed_candidates = candidates[:MAX_CANDIDATES_PROCESSED]
        eligible_targets = []
        
        for candidate in processed_candidates:
            # Sanitize candidate
            safe_candidate = sanitize_candidate_record(candidate)
            
            # Check if eligible for deletion
            if safe_candidate.timestamp_ms <= cutoff_ms:
                # Compute hashes for privacy
                tenant_hash = compute_tenant_hash(safe_candidate.tenant_id)
                target_key_hash = hashlib.sha256(safe_candidate.record_id.encode('utf-8')).hexdigest()
                
                # Compute eligible bucket
                eligible_bucket_ms = compute_bucket_start(safe_candidate.timestamp_ms, bucket_ms)
                
                target = DeletionTarget(
                    artifact_type=artifact_type,
                    tenant_hash=tenant_hash,
                    eligible_bucket_ms=eligible_bucket_ms,
                    target_key_hash=target_key_hash
                )
                
                eligible_targets.append(target)
        
        # Sort targets deterministically
        sorted_targets = sorted(eligible_targets, key=lambda t: t.sort_key())
        
        # Apply max_ops_per_run limit
        limited_targets = sorted_targets[:effective_max_ops]
        reason = RetentionReasonCode.LIMIT_CLAMPED if len(sorted_targets) > effective_max_ops else RetentionReasonCode.OK
        
        # Compute counts by type
        counts_by_type = {artifact_type.value: len(limited_targets)}
        
        # Create plan data for signature
        plan_data = {
            "allowed": True,
            "reason": reason.value,
            "artifact_type": artifact_type.value,
            "targets_count": len(limited_targets),
            "cutoff_ms": cutoff_ms,
            "bucket_start_ms": bucket_start_ms,
            "retention_ms": retention_ms,
            "max_ops_per_run": effective_max_ops,
        }
        
        # Compute signature
        signature = compute_plan_signature(plan_data)
        
        return DeletionPlan(
            allowed=True,
            reason=reason,
            targets=limited_targets,
            counts_by_type=counts_by_type,
            effective_retention_windows=retention_windows,
            bucket_start_ms=bucket_start_ms,
            max_ops_per_run=effective_max_ops,
            signature=signature
        )
    
    except Exception:
        # Fail-closed: return safe minimal plan
        return _create_fail_closed_plan(
            RetentionReasonCode.INTERNAL_INCONSISTENCY,
            now_ms, bucket_ms, max_ops_per_run or MAX_OPS_PER_RUN
        )


def _create_fail_closed_plan(
    reason: RetentionReasonCode,
    now_ms: int,
    bucket_ms: int,
    max_ops_per_run: int
) -> DeletionPlan:
    """Create fail-closed deletion plan with shortest retention."""
    bucket_start_ms = compute_bucket_start(now_ms, bucket_ms)
    
    plan_data = {
        "allowed": False,
        "reason": reason.value,
        "bucket_start_ms": bucket_start_ms,
        "max_ops_per_run": max_ops_per_run,
        "fail_closed": True,
    }
    
    signature = compute_plan_signature(plan_data)
    
    return DeletionPlan(
        allowed=False,
        reason=reason,
        targets=[],
        counts_by_type={},
        effective_retention_windows=SHORTEST_RETENTION_MS.copy(),
        bucket_start_ms=bucket_start_ms,
        max_ops_per_run=max_ops_per_run,
        signature=signature
    )


# ============================================================================
# DELETION EXECUTOR INTERFACE (STUB)
# ============================================================================

@dataclass
class DeletionResult:
    """Result of applying deletion plan."""
    success: bool
    deleted_count: int
    error_count: int
    reason: str


def apply_deletion_plan(plan: DeletionPlan, store_like: Any = None) -> DeletionResult:
    """
    Stub implementation of deletion executor.
    In real implementation, this would interact with actual storage systems.
    """
    if not plan.allowed:
        return DeletionResult(
            success=False,
            deleted_count=0,
            error_count=0,
            reason=f"Plan not allowed: {plan.reason.value}"
        )
    
    # Stub: simulate successful deletion
    total_targets = sum(plan.counts_by_type.values())
    
    return DeletionResult(
        success=True,
        deleted_count=total_targets,
        error_count=0,
        reason="Simulated deletion (stub implementation)"
    )
