"""
Phase 19 Step 1: Memory Schema + Redaction Rules

Strict schema for safe structured facts only.
Fail-closed: anything suspicious is rejected deterministically.

Contract guarantees:
- No raw user messages, no quotes, no "user said: ..."
- Provenance required, confidence within [0,1]
- Value types from enum only
- Deterministic: same input => same output/errors
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional, Tuple


# ============================================================================
# BOUNDS (explicit constants)
# ============================================================================

MAX_FACT_ID_LEN = 80
MAX_KEY_LEN = 48
MAX_VALUE_STR_LEN = 160
MAX_LIST_ITEMS = 12
MAX_LIST_ITEM_LEN = 64
MAX_SOURCE_ID_LEN = 64
MAX_CITATION_IDS = 8
MAX_CITATION_ID_LEN = 64
MAX_TAGS = 10
MAX_TAG_LEN = 32


# ============================================================================
# ENUMS
# ============================================================================

class MemoryValueType(Enum):
    """Allowed value types for memory facts."""
    STR = "STR"
    NUM = "NUM"
    BOOL = "BOOL"
    STR_LIST = "STR_LIST"


class MemoryCategory(Enum):
    """
    Strict allowlist of memory categories.
    
    Minimal safe allowlist - no identity, politics, health, religion, sexuality.
    """
    PREFERENCES_CONSTRAINTS = "PREFERENCES_CONSTRAINTS"
    USER_GOALS = "USER_GOALS"
    PROJECT_CONTEXT = "PROJECT_CONTEXT"
    WORKFLOW_STATE = "WORKFLOW_STATE"


class ProvenanceType(Enum):
    """Source type for memory provenance."""
    SYSTEM_KNOWN = "SYSTEM_KNOWN"
    USER_EXPLICIT = "USER_EXPLICIT"
    TOOL_CITED = "TOOL_CITED"
    DERIVED_SUMMARY = "DERIVED_SUMMARY"


# ============================================================================
# FORBIDDEN KEYS (deep-scan)
# ============================================================================

FORBIDDEN_KEYS = frozenset([
    "user_text",
    "rendered_text",
    "message",
    "content",
    "prompt",
    "transcript",
    "chat",
    "raw",
    "quote",
    "conversation",
    "answer",
    "rationale",
    "clarify_question",
])


# ============================================================================
# REDACTION PATTERNS (reject, don't clean)
# ============================================================================

REDACTION_PATTERNS = [
    re.compile(r"\buser\s+said\b", re.IGNORECASE),
    re.compile(r"\byou\s+said\b", re.IGNORECASE),
    re.compile(r"\bi\s+said\b", re.IGNORECASE),
    re.compile(r"\bhe\s+said\b", re.IGNORECASE),
    re.compile(r"\bshe\s+said\b", re.IGNORECASE),
    re.compile(r"\bthey\s+said\b", re.IGNORECASE),
    re.compile(r"^>", re.MULTILINE),  # Markdown quote
    re.compile(r'"{3,}'),  # Triple+ quotes
    re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"developer\s+message", re.IGNORECASE),
    re.compile(r"\bFrom:\s*.*\bSubject:", re.IGNORECASE | re.DOTALL),
    re.compile(r"Open\s+in\s+Gmail", re.IGNORECASE),
    re.compile(r"\|\|\|"),  # Delimiter pattern
    re.compile(r"^\s*2026-\d{2}-\d{2}", re.MULTILINE),  # Timestamp at start
]


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class Provenance:
    """
    Provenance for a memory fact.
    
    source_id must be structure-only ID, never raw text.
    """
    source_type: ProvenanceType
    source_id: str
    collected_at_ms: int
    citation_ids: List[str]
    
    def __post_init__(self):
        if self.citation_ids is None:
            self.citation_ids = []


@dataclass
class MemoryFact:
    """
    A single memory fact with strict schema.
    
    Exactly one of (value_str, value_num, value_bool, value_list_str) must be set.
    """
    fact_id: str
    category: MemoryCategory
    key: str
    value_type: MemoryValueType
    value_str: Optional[str]
    value_num: Optional[float]
    value_bool: Optional[bool]
    value_list_str: Optional[List[str]]
    confidence: float
    provenance: Provenance
    created_at_ms: int
    expires_at_ms: Optional[int]
    tags: List[str]
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.value_list_str is None and self.value_type == MemoryValueType.STR_LIST:
            self.value_list_str = []


# ============================================================================
# FORBIDDEN KEYS DEEP-SCAN
# ============================================================================

def _deep_scan_forbidden_keys(data: Any, path: str = "") -> List[str]:
    """
    Recursively scan for forbidden keys in dict-like structures.
    
    Returns list of error messages for any forbidden keys found.
    """
    errors = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            key_lower = str(key).lower()
            current_path = f"{path}.{key}" if path else key
            
            if key_lower in FORBIDDEN_KEYS:
                errors.append(f"FORBIDDEN_KEY: '{key}' at path '{current_path}'")
            
            # Recurse into value
            errors.extend(_deep_scan_forbidden_keys(value, current_path))
    
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"
            errors.extend(_deep_scan_forbidden_keys(item, current_path))
    
    return errors


# ============================================================================
# REDACTION VALIDATION
# ============================================================================

def _check_redaction_patterns(text: str) -> List[str]:
    """
    Check if text contains any forbidden redaction patterns.
    
    Returns list of error messages for any patterns found.
    """
    errors = []
    
    for pattern in REDACTION_PATTERNS:
        if pattern.search(text):
            errors.append(f"REDACTION_PATTERN: text matches forbidden pattern '{pattern.pattern}'")
    
    return errors


def _validate_string_content(text: str, field_name: str) -> List[str]:
    """
    Validate string content for redaction patterns.
    
    Returns list of error messages.
    """
    if not text:
        return []
    
    errors = []
    
    # Check redaction patterns
    pattern_errors = _check_redaction_patterns(text)
    for err in pattern_errors:
        errors.append(f"{field_name}: {err}")
    
    return errors


# ============================================================================
# PROVENANCE VALIDATION
# ============================================================================

def _validate_provenance(prov: Provenance) -> List[str]:
    """
    Validate provenance structure.
    
    Returns list of error messages.
    """
    errors = []
    
    # source_type required
    if prov.source_type is None:
        errors.append("PROVENANCE: source_type is required")
        return errors
    
    # source_id bounds
    if not prov.source_id:
        errors.append("PROVENANCE: source_id is required")
    elif len(prov.source_id) > MAX_SOURCE_ID_LEN:
        errors.append(f"PROVENANCE: source_id exceeds {MAX_SOURCE_ID_LEN} chars")
    
    # source_id must look like an ID, not raw text (for TOOL_CITED and DERIVED_SUMMARY)
    if prov.source_type in (ProvenanceType.TOOL_CITED, ProvenanceType.DERIVED_SUMMARY):
        if prov.source_id:
            # Reject if looks like raw text (contains spaces and is long, or has sentence-like structure)
            if " " in prov.source_id and len(prov.source_id) > 20:
                errors.append("PROVENANCE: source_id looks like raw text, not a structured ID")
            # Reject if contains common sentence patterns
            if any(word in prov.source_id.lower() for word in ["the ", "is ", "was ", "are ", "said"]):
                errors.append("PROVENANCE: source_id contains sentence-like content")
    
    # collected_at_ms must be >= 0
    if prov.collected_at_ms < 0:
        errors.append("PROVENANCE: collected_at_ms must be >= 0")
    
    # citation_ids bounds
    if len(prov.citation_ids) > MAX_CITATION_IDS:
        errors.append(f"PROVENANCE: citation_ids exceeds {MAX_CITATION_IDS} items")
    
    for i, cid in enumerate(prov.citation_ids):
        if len(cid) > MAX_CITATION_ID_LEN:
            errors.append(f"PROVENANCE: citation_ids[{i}] exceeds {MAX_CITATION_ID_LEN} chars")
    
    return errors


# ============================================================================
# FACT VALIDATION
# ============================================================================

def _validate_bounds(fact: MemoryFact) -> List[str]:
    """
    Validate all bounds on a MemoryFact.
    
    Returns list of error messages.
    """
    errors = []
    
    # fact_id bounds
    if not fact.fact_id:
        errors.append("BOUNDS: fact_id is required")
    elif len(fact.fact_id) > MAX_FACT_ID_LEN:
        errors.append(f"BOUNDS: fact_id exceeds {MAX_FACT_ID_LEN} chars")
    
    # key bounds
    if not fact.key:
        errors.append("BOUNDS: key is required")
    elif len(fact.key) > MAX_KEY_LEN:
        errors.append(f"BOUNDS: key exceeds {MAX_KEY_LEN} chars")
    
    # value_str bounds
    if fact.value_str is not None and len(fact.value_str) > MAX_VALUE_STR_LEN:
        errors.append(f"BOUNDS: value_str exceeds {MAX_VALUE_STR_LEN} chars")
    
    # value_list_str bounds
    if fact.value_list_str is not None:
        if len(fact.value_list_str) > MAX_LIST_ITEMS:
            errors.append(f"BOUNDS: value_list_str exceeds {MAX_LIST_ITEMS} items")
        for i, item in enumerate(fact.value_list_str):
            if len(item) > MAX_LIST_ITEM_LEN:
                errors.append(f"BOUNDS: value_list_str[{i}] exceeds {MAX_LIST_ITEM_LEN} chars")
    
    # tags bounds
    if len(fact.tags) > MAX_TAGS:
        errors.append(f"BOUNDS: tags exceeds {MAX_TAGS} items")
    for i, tag in enumerate(fact.tags):
        if len(tag) > MAX_TAG_LEN:
            errors.append(f"BOUNDS: tags[{i}] exceeds {MAX_TAG_LEN} chars")
    
    return errors


def _validate_one_of_value(fact: MemoryFact) -> List[str]:
    """
    Validate one-of value invariant.
    
    Exactly one of (value_str, value_num, value_bool, value_list_str) must be set,
    and must match value_type.
    """
    errors = []
    
    values_set = []
    if fact.value_str is not None:
        values_set.append("value_str")
    if fact.value_num is not None:
        values_set.append("value_num")
    if fact.value_bool is not None:
        values_set.append("value_bool")
    if fact.value_list_str is not None:
        values_set.append("value_list_str")
    
    if len(values_set) == 0:
        errors.append("ONE_OF_VALUE: no value field is set")
    elif len(values_set) > 1:
        errors.append(f"ONE_OF_VALUE: multiple value fields set: {values_set}")
    else:
        # Check type match
        value_field = values_set[0]
        expected_field = {
            MemoryValueType.STR: "value_str",
            MemoryValueType.NUM: "value_num",
            MemoryValueType.BOOL: "value_bool",
            MemoryValueType.STR_LIST: "value_list_str",
        }.get(fact.value_type)
        
        if value_field != expected_field:
            errors.append(f"ONE_OF_VALUE: value_type {fact.value_type.value} but {value_field} is set (expected {expected_field})")
    
    # Reject empty strings for STR type
    if fact.value_type == MemoryValueType.STR and fact.value_str is not None:
        if not fact.value_str.strip():
            errors.append("ONE_OF_VALUE: value_str is empty after trimming")
    
    # Reject empty lists for STR_LIST type
    if fact.value_type == MemoryValueType.STR_LIST and fact.value_list_str is not None:
        if len(fact.value_list_str) == 0:
            errors.append("ONE_OF_VALUE: value_list_str is empty")
    
    return errors


def _validate_confidence(fact: MemoryFact) -> List[str]:
    """
    Validate confidence bounds.
    
    - Must be in [0, 1]
    - DERIVED_SUMMARY cannot exceed 0.85
    """
    errors = []
    
    if fact.confidence < 0.0 or fact.confidence > 1.0:
        errors.append(f"CONFIDENCE: must be in [0, 1], got {fact.confidence}")
    
    # DERIVED_SUMMARY cap
    if fact.provenance and fact.provenance.source_type == ProvenanceType.DERIVED_SUMMARY:
        if fact.confidence > 0.85:
            errors.append(f"CONFIDENCE: DERIVED_SUMMARY cannot exceed 0.85, got {fact.confidence}")
    
    return errors


def _validate_timestamps(fact: MemoryFact) -> List[str]:
    """
    Validate timestamp constraints.
    """
    errors = []
    
    if fact.created_at_ms < 0:
        errors.append("TIMESTAMPS: created_at_ms must be >= 0")
    
    if fact.expires_at_ms is not None:
        if fact.expires_at_ms < fact.created_at_ms:
            errors.append("TIMESTAMPS: expires_at_ms must be >= created_at_ms")
    
    return errors


def _validate_content_redaction(fact: MemoryFact) -> List[str]:
    """
    Validate content for redaction patterns.
    """
    errors = []
    
    # Check value_str
    if fact.value_str:
        errors.extend(_validate_string_content(fact.value_str, "value_str"))
    
    # Check value_list_str items
    if fact.value_list_str:
        for i, item in enumerate(fact.value_list_str):
            item_errors = _validate_string_content(item, f"value_list_str[{i}]")
            errors.extend(item_errors)
    
    # Check key
    errors.extend(_validate_string_content(fact.key, "key"))
    
    # Check tags
    for i, tag in enumerate(fact.tags):
        errors.extend(_validate_string_content(tag, f"tags[{i}]"))
    
    return errors


# ============================================================================
# PUBLIC API
# ============================================================================

def validate_fact(fact: MemoryFact) -> Tuple[bool, List[str]]:
    """
    Validate a MemoryFact.
    
    Returns (is_valid, sorted_errors).
    Deterministic: same input => same output.
    """
    try:
        errors = []
        
        # Category validation
        if fact.category is None:
            errors.append("CATEGORY: category is required")
        
        # Value type validation
        if fact.value_type is None:
            errors.append("VALUE_TYPE: value_type is required")
        
        # Provenance validation
        if fact.provenance is None:
            errors.append("PROVENANCE: provenance is required")
        else:
            errors.extend(_validate_provenance(fact.provenance))
        
        # Bounds validation
        errors.extend(_validate_bounds(fact))
        
        # One-of value validation
        errors.extend(_validate_one_of_value(fact))
        
        # Confidence validation
        errors.extend(_validate_confidence(fact))
        
        # Timestamps validation
        errors.extend(_validate_timestamps(fact))
        
        # Content redaction validation
        errors.extend(_validate_content_redaction(fact))
        
        # Sort errors for determinism
        errors = sorted(set(errors))
        
        return (len(errors) == 0, errors)
    
    except Exception:
        return (False, ["INTERNAL_ERROR"])


def sanitize_and_validate_fact(fact: MemoryFact) -> Tuple[Optional[MemoryFact], List[str]]:
    """
    Sanitize and validate a MemoryFact.
    
    Sanitization:
    - Normalize whitespace (collapse multiple spaces, trim)
    - Lowercase tags
    
    Does NOT rewrite meaning or remove content.
    
    Returns (sanitized_fact or None, sorted_errors).
    Deterministic: same input => same output.
    """
    try:
        # Normalize whitespace helper
        def normalize_ws(s: str) -> str:
            if not s:
                return s
            return " ".join(s.split())
        
        # Sanitize fields
        sanitized_fact_id = normalize_ws(fact.fact_id) if fact.fact_id else fact.fact_id
        sanitized_key = normalize_ws(fact.key) if fact.key else fact.key
        sanitized_value_str = normalize_ws(fact.value_str) if fact.value_str else fact.value_str
        
        sanitized_value_list_str = None
        if fact.value_list_str is not None:
            sanitized_value_list_str = [normalize_ws(item) for item in fact.value_list_str]
        
        sanitized_tags = [normalize_ws(tag).lower() for tag in fact.tags] if fact.tags else []
        
        # Sanitize provenance source_id
        sanitized_source_id = normalize_ws(fact.provenance.source_id) if fact.provenance and fact.provenance.source_id else (fact.provenance.source_id if fact.provenance else "")
        
        sanitized_citation_ids = []
        if fact.provenance and fact.provenance.citation_ids:
            sanitized_citation_ids = [normalize_ws(cid) for cid in fact.provenance.citation_ids]
        
        # Build sanitized provenance
        sanitized_provenance = None
        if fact.provenance:
            sanitized_provenance = Provenance(
                source_type=fact.provenance.source_type,
                source_id=sanitized_source_id,
                collected_at_ms=fact.provenance.collected_at_ms,
                citation_ids=sanitized_citation_ids,
            )
        
        # Build sanitized fact
        sanitized_fact = MemoryFact(
            fact_id=sanitized_fact_id,
            category=fact.category,
            key=sanitized_key,
            value_type=fact.value_type,
            value_str=sanitized_value_str,
            value_num=fact.value_num,
            value_bool=fact.value_bool,
            value_list_str=sanitized_value_list_str,
            confidence=fact.confidence,
            provenance=sanitized_provenance,
            created_at_ms=fact.created_at_ms,
            expires_at_ms=fact.expires_at_ms,
            tags=sanitized_tags,
        )
        
        # Validate sanitized fact
        is_valid, errors = validate_fact(sanitized_fact)
        
        if is_valid:
            return (sanitized_fact, [])
        else:
            return (None, errors)
    
    except Exception:
        return (None, ["INTERNAL_ERROR"])


def validate_fact_dict(data: dict) -> Tuple[Optional[MemoryFact], List[str]]:
    """
    Construct and validate a MemoryFact from a dict.
    
    - Deep-scan for forbidden keys
    - Reject unknown keys (strict)
    - Validate all bounds
    - Enforce one-of value constraint
    
    Returns (fact or None, sorted_errors).
    Deterministic: same input => same output.
    """
    try:
        errors = []
        
        # Check input type
        if not isinstance(data, dict):
            return (None, ["INPUT: expected dict"])
        
        # Deep-scan for forbidden keys
        forbidden_errors = _deep_scan_forbidden_keys(data)
        errors.extend(forbidden_errors)
        
        # Define allowed keys
        allowed_keys = {
            "fact_id", "category", "key", "value_type",
            "value_str", "value_num", "value_bool", "value_list_str",
            "confidence", "provenance", "created_at_ms", "expires_at_ms", "tags",
        }
        
        allowed_provenance_keys = {
            "source_type", "source_id", "collected_at_ms", "citation_ids",
        }
        
        # Check for unknown keys at top level
        for key in data.keys():
            if key not in allowed_keys:
                errors.append(f"UNKNOWN_KEY: '{key}' is not allowed")
        
        # Check for unknown keys in provenance
        if "provenance" in data and isinstance(data["provenance"], dict):
            for key in data["provenance"].keys():
                if key not in allowed_provenance_keys:
                    errors.append(f"UNKNOWN_KEY: 'provenance.{key}' is not allowed")
        
        # Check required fields
        required_fields = ["fact_id", "category", "key", "value_type", "confidence", "provenance", "created_at_ms"]
        for field in required_fields:
            if field not in data:
                errors.append(f"MISSING_FIELD: '{field}' is required")
        
        # If there are errors from forbidden keys or unknown keys, return early
        if errors:
            return (None, sorted(set(errors)))
        
        # Parse enums
        try:
            category = MemoryCategory(data["category"])
        except (ValueError, KeyError):
            errors.append(f"INVALID_ENUM: category '{data.get('category')}' is not valid")
            category = None
        
        try:
            value_type = MemoryValueType(data["value_type"])
        except (ValueError, KeyError):
            errors.append(f"INVALID_ENUM: value_type '{data.get('value_type')}' is not valid")
            value_type = None
        
        # Parse provenance
        provenance = None
        prov_data = data.get("provenance")
        if prov_data is None:
            errors.append("MISSING_FIELD: 'provenance' is required")
        elif not isinstance(prov_data, dict):
            errors.append("INVALID_TYPE: 'provenance' must be a dict")
        else:
            # Check required provenance fields
            prov_required = ["source_type", "source_id", "collected_at_ms"]
            for field in prov_required:
                if field not in prov_data:
                    errors.append(f"MISSING_FIELD: 'provenance.{field}' is required")
            
            if not errors:
                try:
                    source_type = ProvenanceType(prov_data["source_type"])
                except (ValueError, KeyError):
                    errors.append(f"INVALID_ENUM: provenance.source_type '{prov_data.get('source_type')}' is not valid")
                    source_type = None
                
                if source_type:
                    provenance = Provenance(
                        source_type=source_type,
                        source_id=str(prov_data.get("source_id", "")),
                        collected_at_ms=int(prov_data.get("collected_at_ms", 0)),
                        citation_ids=list(prov_data.get("citation_ids", [])),
                    )
        
        if errors:
            return (None, sorted(set(errors)))
        
        # Build fact
        fact = MemoryFact(
            fact_id=str(data.get("fact_id", "")),
            category=category,
            key=str(data.get("key", "")),
            value_type=value_type,
            value_str=data.get("value_str"),
            value_num=data.get("value_num"),
            value_bool=data.get("value_bool"),
            value_list_str=data.get("value_list_str"),
            confidence=float(data.get("confidence", 0.0)),
            provenance=provenance,
            created_at_ms=int(data.get("created_at_ms", 0)),
            expires_at_ms=data.get("expires_at_ms"),
            tags=list(data.get("tags", [])),
        )
        
        # Sanitize and validate
        return sanitize_and_validate_fact(fact)
    
    except Exception:
        return (None, ["INTERNAL_ERROR"])
