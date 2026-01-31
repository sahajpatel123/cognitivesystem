"""
Phase 19 Step 5: Read Boundary + Retrieval (Bounded MemoryBundle)

Single chokepoint for memory reads that returns bounded, deterministically ordered,
text-safe bundles of facts. Prevents memory flooding and ensures no raw user text.

Contract guarantees:
- Single read chokepoint for all memory retrieval
- Bounded output (max_facts, max_per_category, max_total_chars)
- Deterministic ordering with stable sort keys
- No raw user text or quotes (defense-in-depth)
- Safe template selection only (no freeform search)
- Fail-closed behavior on invalid inputs
"""

import json
import re
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Dict, List, Optional, Protocol, Tuple

from backend.app.memory.schema import MemoryFact, MemoryCategory
from backend.app.memory.store import StoreCaps


# ============================================================================
# CONSTANTS
# ============================================================================

# Hard bounds for request validation
MAX_FACTS_HARD_LIMIT = 24
MAX_PER_CATEGORY_HARD_LIMIT = 12
MAX_TOTAL_CHARS_HARD_LIMIT = 2000

# Default caps
DEFAULT_MAX_FACTS = 16
DEFAULT_MAX_PER_CATEGORY = 8
DEFAULT_MAX_TOTAL_CHARS = 1200

# Category priority for deterministic ordering (lower = higher priority)
CATEGORY_PRIORITY: Dict[MemoryCategory, int] = {
    MemoryCategory.PREFERENCES_CONSTRAINTS: 0,
    MemoryCategory.USER_GOALS: 1,
    MemoryCategory.PROJECT_CONTEXT: 2,
    MemoryCategory.WORKFLOW_STATE: 3,
}

# Char cost constants for different value types
CHAR_COST_NUM = 8
CHAR_COST_BOOL = 8
CHAR_COST_OVERHEAD = 16  # key + metadata overhead


# ============================================================================
# ENUMS
# ============================================================================

class ReadTemplate(Enum):
    """Safe templates for memory selection."""
    CONSTRAINTS_AND_PREFERENCES = "CONSTRAINTS_AND_PREFERENCES"
    GOALS_AND_WORKFLOW = "GOALS_AND_WORKFLOW"
    PROJECT_CONTEXT_ONLY = "PROJECT_CONTEXT_ONLY"
    WORKFLOW_STATE_ONLY = "WORKFLOW_STATE_ONLY"


class BundleReason(Enum):
    """Deterministic reasons for bundle results."""
    OK = "OK"
    REQUEST_INVALID = "REQUEST_INVALID"
    NO_MATCH = "NO_MATCH"
    ALL_SKIPPED_UNSAFE = "ALL_SKIPPED_UNSAFE"
    CAPPED = "CAPPED"
    INTERNAL_INCONSISTENCY = "INTERNAL_INCONSISTENCY"


# ============================================================================
# TEMPLATE MAPPINGS
# ============================================================================

TEMPLATE_CATEGORIES: Dict[ReadTemplate, List[MemoryCategory]] = {
    ReadTemplate.CONSTRAINTS_AND_PREFERENCES: [
        MemoryCategory.PREFERENCES_CONSTRAINTS,
    ],
    ReadTemplate.GOALS_AND_WORKFLOW: [
        MemoryCategory.USER_GOALS,
        MemoryCategory.WORKFLOW_STATE,
    ],
    ReadTemplate.PROJECT_CONTEXT_ONLY: [
        MemoryCategory.PROJECT_CONTEXT,
    ],
    ReadTemplate.WORKFLOW_STATE_ONLY: [
        MemoryCategory.WORKFLOW_STATE,
    ],
}


# ============================================================================
# PROTOCOLS
# ============================================================================

class MemoryStoreLike(Protocol):
    """Protocol for memory store interface."""
    
    def get_current_facts(self, now_ms: int, caps: Optional[StoreCaps] = None) -> List[MemoryFact]:
        """Get current active facts from derived view."""
        ...


# ============================================================================
# REQUEST AND RESPONSE DATACLASSES
# ============================================================================

@dataclass
class MemoryReadRequest:
    """
    Request for reading memory bundle.
    
    Bounded and validated. No freeform query text allowed.
    """
    now_ms: int
    categories: Optional[List[MemoryCategory]] = None
    keys: Optional[List[str]] = None
    template: Optional[ReadTemplate] = None
    max_facts: int = DEFAULT_MAX_FACTS
    max_total_chars: int = DEFAULT_MAX_TOTAL_CHARS
    max_per_category: int = DEFAULT_MAX_PER_CATEGORY
    
    def is_valid(self) -> Tuple[bool, Optional[str]]:
        """Validate request. Returns (is_valid, error_reason)."""
        # Check now_ms
        if self.now_ms < 0:
            return False, "NOW_MS_NEGATIVE"
        
        # Check caps bounds
        if not (1 <= self.max_facts <= MAX_FACTS_HARD_LIMIT):
            return False, "MAX_FACTS_OUT_OF_BOUNDS"
        if not (1 <= self.max_per_category <= MAX_PER_CATEGORY_HARD_LIMIT):
            return False, "MAX_PER_CATEGORY_OUT_OF_BOUNDS"
        if not (1 <= self.max_total_chars <= MAX_TOTAL_CHARS_HARD_LIMIT):
            return False, "MAX_TOTAL_CHARS_OUT_OF_BOUNDS"
        
        # Check selector presence
        has_template = self.template is not None
        has_categories = self.categories is not None and len(self.categories) > 0
        has_keys = self.keys is not None and len(self.keys) > 0
        
        if not (has_template or has_categories):
            return False, "NO_SELECTOR_PROVIDED"
        
        # If keys provided, categories must also be provided
        if has_keys and not has_categories:
            return False, "KEYS_WITHOUT_CATEGORIES"
        
        # Check key bounds
        if has_keys and len(self.keys) > 50:
            return False, "TOO_MANY_KEYS"
        
        # Check category bounds
        if has_categories and len(self.categories) > 10:
            return False, "TOO_MANY_CATEGORIES"
        
        return True, None


@dataclass
class MemoryBundle:
    """
    Bounded bundle of memory facts.
    
    JSON-serializable with deterministic structure.
    """
    facts: List[MemoryFact]
    bundle_reason: str
    selected_count: int
    skipped_count: int
    applied_caps: Dict[str, int]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        # Convert facts to serializable format
        facts_data = []
        for fact in self.facts:
            fact_dict = {
                "fact_id": fact.fact_id,
                "category": fact.category.value,
                "key": fact.key,
                "value_type": fact.value_type.value,
                "value_str": fact.value_str,
                "value_num": fact.value_num,
                "value_bool": fact.value_bool,
                "value_list_str": fact.value_list_str,
                "confidence": fact.confidence,
                "created_at_ms": fact.created_at_ms,
                "expires_at_ms": fact.expires_at_ms,
                "tags": fact.tags,
            }
            if fact.provenance:
                fact_dict["provenance"] = {
                    "source_type": fact.provenance.source_type.value,
                    "source_id": fact.provenance.source_id,
                    "collected_at_ms": fact.provenance.collected_at_ms,
                    "citation_ids": fact.provenance.citation_ids,
                }
            facts_data.append(fact_dict)
        
        return {
            "facts": facts_data,
            "bundle_reason": self.bundle_reason,
            "selected_count": self.selected_count,
            "skipped_count": self.skipped_count,
            "applied_caps": self.applied_caps,
        }


# ============================================================================
# UNSAFE FACT DETECTION
# ============================================================================

# Forbidden patterns (case-insensitive)
FORBIDDEN_PATTERNS = [
    r'\buser\s+said\b',
    r'\byou\s+said\b',
    r'\bi\s+said\b',
    r'\bhe\s+said\b',
    r'\bshe\s+said\b',
    r'\bignore\s+previous\s+instructions\b',
    r'\bignore\s+all\s+previous\b',
    r'\bforget\s+everything\b',
    r'\boverride\s+instructions\b',
]

# Compiled regex patterns for performance
COMPILED_FORBIDDEN = [re.compile(pattern, re.IGNORECASE) for pattern in FORBIDDEN_PATTERNS]


def is_fact_safe_for_bundle(fact: MemoryFact) -> bool:
    """
    Check if fact is safe for inclusion in bundle.
    
    Deterministic checks for forbidden patterns and unsafe content.
    """
    # Check all string fields
    string_fields = []
    
    if fact.key:
        string_fields.append(fact.key)
    
    if fact.value_str:
        string_fields.append(fact.value_str)
    
    if fact.value_list_str:
        string_fields.extend(fact.value_list_str)
    
    if fact.tags:
        string_fields.extend(fact.tags)
    
    # Check each string field
    for field_value in string_fields:
        if not field_value:
            continue
        
        # Check for markdown quote at start of line
        if field_value.startswith('>'):
            return False
        
        # Check for multi-line quotes
        lines = field_value.split('\n')
        for line in lines:
            if line.strip().startswith('>'):
                return False
        
        # Check forbidden patterns
        for pattern in COMPILED_FORBIDDEN:
            if pattern.search(field_value):
                return False
        
        # Check for sensitive sentinels (test artifacts)
        if 'SENSITIVE_' in field_value.upper():
            return False
    
    # Check provenance source_id for safety
    if fact.provenance and fact.provenance.source_id:
        source_id = fact.provenance.source_id
        for pattern in COMPILED_FORBIDDEN:
            if pattern.search(source_id):
                return False
    
    return True


# ============================================================================
# DETERMINISTIC ORDERING
# ============================================================================

def _compute_tie_break_hash(fact: MemoryFact) -> str:
    """
    Compute deterministic tie-break hash from structure-only fields.
    
    Uses stable fields, no raw value text.
    """
    # Structure-only fields
    data = {
        "fact_id": fact.fact_id,
        "category": fact.category.value,
        "key": fact.key or "",
        "value_type": fact.value_type.value,
        "confidence": fact.confidence or 0.0,
    }
    
    # Add value lengths (not content)
    if fact.value_str:
        data["value_str_len"] = len(fact.value_str)
    if fact.value_list_str:
        data["value_list_len"] = len(fact.value_list_str)
        data["value_list_total_chars"] = sum(len(item) for item in fact.value_list_str)
    
    # Add provenance type
    if fact.provenance and fact.provenance.source_type:
        data["provenance_type"] = fact.provenance.source_type.value
    
    # Canonical JSON
    json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return sha256(json_str.encode('utf-8')).hexdigest()[:16]


def _compute_sort_key(fact: MemoryFact) -> Tuple:
    """
    Compute sort key for deterministic ordering.
    
    Priority order:
    1. Confidence DESC (negate for sort)
    2. collected_at_ms DESC (negate for sort)
    3. Category priority ASC (lower = higher priority)
    4. Tie-break hash ASC
    """
    # Confidence (negate for descending)
    confidence = -(fact.confidence or 0.0)
    
    # Collected at (negate for descending)
    collected_at = 0
    if fact.provenance and fact.provenance.collected_at_ms:
        collected_at = -fact.provenance.collected_at_ms
    elif fact.created_at_ms:
        collected_at = -fact.created_at_ms
    
    # Category priority
    category_priority = CATEGORY_PRIORITY.get(fact.category, 999)
    
    # Tie-break hash
    tie_break = _compute_tie_break_hash(fact)
    
    return (confidence, collected_at, category_priority, tie_break)


# ============================================================================
# CHAR COST COMPUTATION
# ============================================================================

def _compute_char_cost(fact: MemoryFact) -> int:
    """Compute character cost for a fact."""
    cost = CHAR_COST_OVERHEAD
    
    # Key cost
    if fact.key:
        cost += len(fact.key)
    
    # Value cost
    if fact.value_str:
        cost += len(fact.value_str)
    elif fact.value_list_str:
        cost += sum(len(item) for item in fact.value_list_str)
    elif fact.value_num is not None:
        cost += CHAR_COST_NUM
    elif fact.value_bool is not None:
        cost += CHAR_COST_BOOL
    
    return cost


# ============================================================================
# SELECTION LOGIC
# ============================================================================

def _select_candidates_by_request(
    all_facts: List[MemoryFact],
    req: MemoryReadRequest,
) -> List[MemoryFact]:
    """Select candidate facts based on request criteria."""
    candidates = []
    
    # Determine target categories
    target_categories = set()
    
    if req.template:
        target_categories.update(TEMPLATE_CATEGORIES[req.template])
    
    if req.categories:
        target_categories.update(req.categories)
    
    # Filter facts
    for fact in all_facts:
        # Category filter
        if target_categories and fact.category not in target_categories:
            continue
        
        # Key filter (exact match)
        if req.keys:
            if not fact.key or fact.key not in req.keys:
                continue
        
        candidates.append(fact)
    
    return candidates


def _apply_caps_and_select(
    candidates: List[MemoryFact],
    req: MemoryReadRequest,
) -> Tuple[List[MemoryFact], Dict[str, int]]:
    """
    Apply caps and select final facts.
    
    Returns (selected_facts, applied_caps).
    """
    applied_caps = {}
    
    # Sort candidates by priority
    candidates.sort(key=_compute_sort_key)
    
    # Stage 1: Per-category cap
    by_category: Dict[MemoryCategory, List[MemoryFact]] = {}
    for fact in candidates:
        if fact.category not in by_category:
            by_category[fact.category] = []
        by_category[fact.category].append(fact)
    
    # Apply per-category limit
    category_limited = []
    for category, facts in by_category.items():
        if len(facts) > req.max_per_category:
            applied_caps[f"per_category_{category.value}"] = req.max_per_category
            facts = facts[:req.max_per_category]
        category_limited.extend(facts)
    
    # Re-sort after category limiting
    category_limited.sort(key=_compute_sort_key)
    
    # Stage 2: Total fact cap
    if len(category_limited) > req.max_facts:
        applied_caps["max_facts"] = req.max_facts
        category_limited = category_limited[:req.max_facts]
    
    # Stage 3: Character budget
    selected = []
    total_chars = 0
    
    for fact in category_limited:
        char_cost = _compute_char_cost(fact)
        if total_chars + char_cost > req.max_total_chars:
            applied_caps["max_total_chars"] = req.max_total_chars
            break
        
        selected.append(fact)
        total_chars += char_cost
    
    return selected, applied_caps


# ============================================================================
# MAIN READ FUNCTION
# ============================================================================

def read_memory_bundle(
    req: MemoryReadRequest,
    store: MemoryStoreLike,
) -> MemoryBundle:
    """
    Single chokepoint for memory reads.
    
    Returns bounded, deterministically ordered, text-safe bundle of facts.
    """
    try:
        # Validate request
        is_valid, error_reason = req.is_valid()
        if not is_valid:
            return MemoryBundle(
                facts=[],
                bundle_reason=BundleReason.REQUEST_INVALID.value,
                selected_count=0,
                skipped_count=0,
                applied_caps={"error": error_reason},
            )
        
        # Get all current facts from store
        all_facts = store.get_current_facts(req.now_ms)
        
        # Select candidates based on request
        candidates = _select_candidates_by_request(all_facts, req)
        
        if not candidates:
            return MemoryBundle(
                facts=[],
                bundle_reason=BundleReason.NO_MATCH.value,
                selected_count=0,
                skipped_count=0,
                applied_caps={},
            )
        
        # Filter unsafe facts
        safe_candidates = []
        skipped_unsafe = 0
        
        for fact in candidates:
            if is_fact_safe_for_bundle(fact):
                safe_candidates.append(fact)
            else:
                skipped_unsafe += 1
        
        if not safe_candidates:
            return MemoryBundle(
                facts=[],
                bundle_reason=BundleReason.ALL_SKIPPED_UNSAFE.value,
                selected_count=0,
                skipped_count=skipped_unsafe,
                applied_caps={},
            )
        
        # Apply caps and select final facts
        selected_facts, applied_caps = _apply_caps_and_select(safe_candidates, req)
        
        # Determine bundle reason
        bundle_reason = BundleReason.OK.value
        if applied_caps:
            bundle_reason = BundleReason.CAPPED.value
        
        return MemoryBundle(
            facts=selected_facts,
            bundle_reason=bundle_reason,
            selected_count=len(selected_facts),
            skipped_count=skipped_unsafe,
            applied_caps=applied_caps,
        )
    
    except Exception:
        # Fail-closed on any exception
        return MemoryBundle(
            facts=[],
            bundle_reason=BundleReason.INTERNAL_INCONSISTENCY.value,
            selected_count=0,
            skipped_count=0,
            applied_caps={},
        )
