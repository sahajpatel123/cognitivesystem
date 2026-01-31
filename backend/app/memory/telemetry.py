"""
Phase 19 Step 7: Memory Observability + Replay Pack (NO USER TEXT)

Memory telemetry system for debugging memory behavior without leaking any memory
values or user content. Deterministic, bounded, and fail-closed.

HARD RULES:
- NO TEXT LEAKAGE: No memory fact keys, values, tags, fact_ids, user strings
- STRUCTURE-ONLY SIGNATURE: SHA256 over sanitized structure-only pack
- DETERMINISTIC: Sorted keys JSON, stable ordering, no timestamps
- BOUNDED: Counts/histograms with bounded size, clamp deterministically
- FAIL-CLOSED: Sanitize unexpected inputs, never crash
"""

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================================
# CONSTANTS
# ============================================================================

MEMORY_TELEMETRY_VERSION = "19.7.0"

# Forbidden key substrings that must be removed from dict keys only (not values)
FORBIDDEN_KEY_SUBSTRINGS = frozenset([
    "key", "value", "value_str", "value_num", "value_bool", "value_str_list", "tags",
    "fact_id", "fact", "facts", "raw", "text", "prompt", "message", "messages", "user",
    "assistant", "content", "quote", "excerpt", "snippet", "provenance", "source_id",
    "citation_ids", "title", "url", "domain", "body", "summary", "description",
    "name", "label", "comment", "note", "memo", "details", "info", "data",
    "input", "output", "response", "request", "query", "search", "term",
    "phrase", "sentence", "paragraph", "document", "file", "path", "filename",
    "forbidden", "forbidden_field", "malicious", "sensitive", "secret", "private",
    "transcript", "answer", "conversation", "chat", "dialog", "dialogue",
])

# Allowed TTL class labels
ALLOWED_TTL_LABELS = frozenset(["TTL_1H", "TTL_1D", "TTL_10D", "UNKNOWN"])

# Allowed reason code pattern (uppercase letters, digits, underscore, max 40 chars for safety)
REASON_CODE_PATTERN = re.compile(r"^[A-Z0-9_]{1,40}$")

# Known bucket labels
KNOWN_BUCKET_LABELS = frozenset([
    "0", "1-4", "5-8", "9-16", "17+", 
    "1-400", "401-800", "801-1200", "1201+"
])

# Bounds
MAX_DICT_KEYS = 64
MAX_LIST_ITEMS = 64
MAX_REASON_CODES = 32
MAX_STRING_LENGTH = 100


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class MemoryTelemetryInput:
    """
    Input record for building memory telemetry events.
    Contains only structure fields, no memory text.
    """
    writes_attempted: int = 0
    writes_accepted: int = 0
    writes_rejected: int = 0
    rejection_reason_codes: List[str] = None
    ttl_classes: List[str] = None
    reads_attempted: int = 0
    bundle_sizes: List[int] = None
    bundle_chars: List[int] = None
    caps_snapshot: Dict[str, int] = None
    
    def __post_init__(self):
        """Initialize empty lists/dicts if None."""
        if self.rejection_reason_codes is None:
            self.rejection_reason_codes = []
        if self.ttl_classes is None:
            self.ttl_classes = []
        if self.bundle_sizes is None:
            self.bundle_sizes = []
        if self.bundle_chars is None:
            self.bundle_chars = []
        if self.caps_snapshot is None:
            self.caps_snapshot = {}


@dataclass
class MemoryTelemetryEvent:
    """
    Memory telemetry event with structure-only fields.
    Deterministic, bounded, and safe from text leakage.
    """
    version: str
    writes_attempted: int
    writes_accepted: int
    writes_rejected: int
    rejection_reason_hist: Dict[str, int]
    ttl_class_hist: Dict[str, int]
    reads_attempted: int
    bundle_size_hist: Dict[str, int]
    bundle_chars_hist: Dict[str, int]
    caps_snapshot: Dict[str, int]
    memory_signature: str
    had_forbidden_keys: bool
    dropped_keys_count: int


# ============================================================================
# VALUE TOKEN SANITIZATION
# ============================================================================

def sanitize_value_token(s: str, kind: str) -> str:
    """
    Sanitize string values based on their expected type/context.
    
    Args:
        s: The string value to sanitize
        kind: Type of token - "reason_code", "ttl_class", "bucket_label", "generic_token"
    
    Returns:
        Sanitized string value
    """
    if not isinstance(s, str):
        return "REDACTED_TOKEN"
    
    if len(s) > MAX_STRING_LENGTH:
        return "REDACTED_TOKEN"
    
    # Check for obvious sentinel patterns that should never be allowed
    s_lower = s.lower()
    forbidden_patterns = ["sensitive_", "user_text", "memory_value", "user said", "i have", "personal information"]
    if any(pattern in s_lower for pattern in forbidden_patterns):
        if kind == "reason_code":
            return "INVALID_REASON"
        elif kind == "ttl_class":
            return "UNKNOWN"
        elif kind == "bucket_label":
            return "UNKNOWN_BUCKET"
        else:
            return "REDACTED_TOKEN"
    
    if kind == "reason_code":
        if REASON_CODE_PATTERN.match(s):
            return s
        else:
            return "INVALID_REASON"
    
    elif kind == "ttl_class":
        if s in ALLOWED_TTL_LABELS:
            return s
        else:
            return "UNKNOWN"
    
    elif kind == "bucket_label":
        if s in KNOWN_BUCKET_LABELS:
            return s
        else:
            return "UNKNOWN_BUCKET"
    
    elif kind == "generic_token":
        if REASON_CODE_PATTERN.match(s):
            return s
        else:
            return "REDACTED_TOKEN"
    
    else:
        return "REDACTED_TOKEN"


# ============================================================================
# SANITIZATION FUNCTIONS
# ============================================================================

def sanitize_structure(obj: Any) -> Tuple[Any, bool, int]:
    """
    Recursively sanitize object to remove forbidden keys and unsafe content.
    
    Returns:
        (sanitized_obj, had_forbidden_keys, dropped_keys_count)
    """
    had_forbidden = False
    dropped_count = 0
    
    def _sanitize_recursive(item: Any) -> Tuple[Any, bool, int]:
        nonlocal had_forbidden, dropped_count
        
        if item is None or isinstance(item, (bool, int)):
            return item, False, 0
        
        elif isinstance(item, float):
            # Convert float to stable int representation to avoid precision issues
            return int(round(item * 1000)) / 1000, False, 0
        
        elif isinstance(item, str):
            # Sanitize string values using allowlist rules (no forbidden substring checks on values)
            if len(item) > MAX_STRING_LENGTH:
                had_forbidden = True
                dropped_count += 1
                return "REDACTED_TOKEN", True, 1
            
            # Always use generic token sanitization for all strings to ensure forbidden patterns are caught
            sanitized = sanitize_value_token(item, "generic_token")
            if sanitized != item:
                had_forbidden = True
                dropped_count += 1
            return sanitized, sanitized != item, 1 if sanitized != item else 0
        
        elif isinstance(item, list):
            # Bound list size
            bounded_list = item[:MAX_LIST_ITEMS]
            sanitized_list = []
            list_had_forbidden = False
            list_dropped = 0
            
            for list_item in bounded_list:
                sanitized_item, item_forbidden, item_dropped = _sanitize_recursive(list_item)
                if sanitized_item is not None:  # Only add non-None items
                    sanitized_list.append(sanitized_item)
                if item_forbidden:
                    list_had_forbidden = True
                    list_dropped += item_dropped
            
            return sanitized_list, list_had_forbidden, list_dropped
        
        elif isinstance(item, dict):
            sanitized_dict = {}
            dict_had_forbidden = False
            dict_dropped = 0
            
            # Remove forbidden keys and bound dict size
            allowed_keys = []
            for key in item.keys():
                if isinstance(key, str):
                    key_lower = key.lower()
                    # Check if key itself is forbidden
                    if key_lower in FORBIDDEN_KEY_SUBSTRINGS:
                        dict_had_forbidden = True
                        dict_dropped += 1
                        continue
                    # Check if key contains forbidden substrings (but allow safe prefixes)
                    # Allow keys like "max_facts", "total_facts" etc. that have safe prefixes
                    safe_prefixes = ["max_", "total_", "count_", "num_", "size_"]
                    is_safe_prefixed = any(key_lower.startswith(prefix) for prefix in safe_prefixes)
                    
                    if not is_safe_prefixed:
                        has_forbidden_substring = any(forbidden in key_lower for forbidden in FORBIDDEN_KEY_SUBSTRINGS)
                        if has_forbidden_substring:
                            dict_had_forbidden = True
                            dict_dropped += 1
                            continue
                    
                    # Bound key length
                    if len(key) > 64:
                        dict_had_forbidden = True
                        dict_dropped += 1
                        continue
                    
                    allowed_keys.append(key)
                else:
                    dict_had_forbidden = True
                    dict_dropped += 1
            
            # Sort keys for deterministic ordering and apply bound
            allowed_keys.sort()
            bounded_keys = allowed_keys[:MAX_DICT_KEYS]
            
            for key in bounded_keys:
                sanitized_value, value_forbidden, value_dropped = _sanitize_recursive(item[key])
                sanitized_dict[key] = sanitized_value
                if value_forbidden:
                    dict_had_forbidden = True
                    dict_dropped += value_dropped
            
            return sanitized_dict, dict_had_forbidden, dict_dropped
        
        else:
            # Unknown type, drop it
            had_forbidden = True
            dropped_count += 1
            return None, True, 1
    
    sanitized, had_forbidden, dropped_count = _sanitize_recursive(obj)
    return sanitized, had_forbidden, dropped_count


def canonical_json(obj: Any) -> str:
    """
    Convert object to canonical JSON string.
    Deterministic ordering with sorted keys.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_memory_signature(struct_pack: Dict[str, Any]) -> str:
    """
    Compute SHA256 signature of structure-only pack.
    Must not include any text fields, only counts/hists/caps/bucket labels.
    """
    # Create signature pack without the signature field itself
    sig_pack = {k: v for k, v in struct_pack.items() if k != "memory_signature"}
    canonical = canonical_json(sig_pack)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ============================================================================
# BUCKET LOGIC
# ============================================================================

def bucket_size(size: int) -> str:
    """Convert bundle size to bucket label."""
    if size == 0:
        return "0"
    elif 1 <= size <= 4:
        return "1-4"
    elif 5 <= size <= 8:
        return "5-8"
    elif 9 <= size <= 16:
        return "9-16"
    else:
        return "17+"


def bucket_chars(chars: int) -> str:
    """Convert bundle chars to bucket label."""
    if chars == 0:
        return "0"
    elif 1 <= chars <= 400:
        return "1-400"
    elif 401 <= chars <= 800:
        return "401-800"
    elif 801 <= chars <= 1200:
        return "801-1200"
    else:
        return "1201+"


def sanitize_reason_code(code: str) -> str:
    """Sanitize reason code to safe format."""
    return sanitize_value_token(code, "reason_code")


def sanitize_ttl_class(ttl_class: str) -> str:
    """Sanitize TTL class to allowed labels."""
    return sanitize_value_token(ttl_class, "ttl_class")


def build_histogram(items: List[str], max_keys: int = MAX_REASON_CODES) -> Dict[str, int]:
    """
    Build bounded histogram from list of items.
    Keep top items by count, then lexicographic order.
    """
    if not items:
        return {}
    
    # Filter out any items that are still unsafe (basic safety check)
    safe_items = []
    for item in items:
        if isinstance(item, str) and len(item) <= MAX_STRING_LENGTH:
            safe_items.append(item)
    
    # Count occurrences
    counts = {}
    for item in safe_items:
        counts[item] = counts.get(item, 0) + 1
    
    # Sort by count (desc) then by key (asc) for deterministic ordering
    sorted_items = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    
    # Keep only top max_keys
    bounded_items = sorted_items[:max_keys]
    
    # Convert back to dict with sorted keys for deterministic output
    result = {}
    for key, count in sorted(bounded_items, key=lambda x: x[0]):
        result[key] = count
    
    return result


# ============================================================================
# BUILDER FUNCTION
# ============================================================================

def build_memory_telemetry_event(input_data: MemoryTelemetryInput) -> MemoryTelemetryEvent:
    """
    Build memory telemetry event from input data.
    Applies all sanitization, bounding, and signature computation.
    """
    try:
        # Sanitize and bound reason codes
        bounded_reasons = input_data.rejection_reason_codes[:MAX_LIST_ITEMS]
        sanitized_reasons = []
        for code in bounded_reasons:
            sanitized_code = sanitize_reason_code(code)
            sanitized_reasons.append(sanitized_code)
        rejection_reason_hist = build_histogram(sanitized_reasons)
        
        # Sanitize and bound TTL classes
        bounded_ttl = input_data.ttl_classes[:MAX_LIST_ITEMS]
        sanitized_ttl = []
        for ttl in bounded_ttl:
            sanitized_ttl_class = sanitize_ttl_class(ttl)
            sanitized_ttl.append(sanitized_ttl_class)
        ttl_class_hist = build_histogram(sanitized_ttl)
        
        # Build bundle size histogram
        bounded_sizes = input_data.bundle_sizes[:MAX_LIST_ITEMS]
        size_buckets = [bucket_size(size) for size in bounded_sizes if isinstance(size, int) and size >= 0]
        bundle_size_hist = build_histogram(size_buckets)
        
        # Build bundle chars histogram
        bounded_chars = input_data.bundle_chars[:MAX_LIST_ITEMS]
        char_buckets = [bucket_chars(chars) for chars in bounded_chars if isinstance(chars, int) and chars >= 0]
        bundle_chars_hist = build_histogram(char_buckets)
        
        # Sanitize caps snapshot
        sanitized_caps, caps_had_forbidden, caps_dropped = sanitize_structure(input_data.caps_snapshot)
        if not isinstance(sanitized_caps, dict):
            sanitized_caps = {}
        
        # Create struct pack for signature computation
        struct_pack = {
            "version": MEMORY_TELEMETRY_VERSION,
            "writes_attempted": max(0, int(input_data.writes_attempted)),
            "writes_accepted": max(0, int(input_data.writes_accepted)),
            "writes_rejected": max(0, int(input_data.writes_rejected)),
            "rejection_reason_hist": rejection_reason_hist,
            "ttl_class_hist": ttl_class_hist,
            "reads_attempted": max(0, int(input_data.reads_attempted)),
            "bundle_size_hist": bundle_size_hist,
            "bundle_chars_hist": bundle_chars_hist,
            "caps_snapshot": sanitized_caps,
            "had_forbidden_keys": caps_had_forbidden,
            "dropped_keys_count": caps_dropped,
        }
        
        # Compute signature (struct_pack is already sanitized)
        memory_signature = compute_memory_signature(struct_pack)
        
        # Create final event
        return MemoryTelemetryEvent(
            version=MEMORY_TELEMETRY_VERSION,
            writes_attempted=struct_pack["writes_attempted"],
            writes_accepted=struct_pack["writes_accepted"],
            writes_rejected=struct_pack["writes_rejected"],
            rejection_reason_hist=struct_pack["rejection_reason_hist"],
            ttl_class_hist=struct_pack["ttl_class_hist"],
            reads_attempted=struct_pack["reads_attempted"],
            bundle_size_hist=struct_pack["bundle_size_hist"],
            bundle_chars_hist=struct_pack["bundle_chars_hist"],
            caps_snapshot=struct_pack["caps_snapshot"],
            memory_signature=memory_signature,
            had_forbidden_keys=caps_had_forbidden,
            dropped_keys_count=caps_dropped,
        )
    
    except Exception:
        # Fail-closed: return safe default event
        return MemoryTelemetryEvent(
            version=MEMORY_TELEMETRY_VERSION,
            writes_attempted=0,
            writes_accepted=0,
            writes_rejected=0,
            rejection_reason_hist={},
            ttl_class_hist={},
            reads_attempted=0,
            bundle_size_hist={},
            bundle_chars_hist={},
            caps_snapshot={},
            memory_signature=compute_memory_signature({"version": MEMORY_TELEMETRY_VERSION}),
            had_forbidden_keys=True,
            dropped_keys_count=1,
        )


# ============================================================================
# TEST HELPER
# ============================================================================

def assert_no_text_leakage(event_obj: Any, sentinels: List[str]) -> None:
    """
    Assert that none of the sentinel strings appear in the event JSON.
    Used in tests only; not for production runtime.
    """
    event_json = canonical_json(asdict(event_obj) if hasattr(event_obj, '__dataclass_fields__') else event_obj)
    
    for sentinel in sentinels:
        if sentinel in event_json:
            raise AssertionError(f"Text leakage detected: sentinel '{sentinel}' found in event JSON")
