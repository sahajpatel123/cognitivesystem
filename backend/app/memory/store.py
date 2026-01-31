"""
Phase 19 Step 4: Memory Store (Append-only Log + Derived View)

Implements an auditable, deterministic memory store with:
- Append-only event log (immutable events)
- Deterministic "current facts" derived view
- Hard caps enforcement with stable ordering
- No in-place mutations

Contract guarantees:
- All changes represented as events
- Recomputation from log yields identical view for same (log, now_ms, caps)
- Caps enforcement is deterministic with stable priority ordering
"""

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any, Dict, List, Optional, Tuple

from backend.app.memory.schema import (
    MemoryFact,
    MemoryCategory,
    ProvenanceType,
)


# ============================================================================
# CONSTANTS
# ============================================================================

MEMORY_STORE_VERSION = "19.4.0"

MAX_EVENT_ID_LEN = 64
MAX_SCOPE_ID_LEN = 128
MAX_REASON_CODE_LEN = 32
MAX_EVENTS_PER_SCOPE = 10000

# Default caps (safe fallback)
DEFAULT_MAX_FACTS_TOTAL = 100
DEFAULT_MAX_FACTS_PER_CATEGORY = 25


# ============================================================================
# EVENT TYPES
# ============================================================================

class EventType(Enum):
    """Event types for the append-only log."""
    FACT_ADDED = "FACT_ADDED"
    FACT_EXPIRED = "FACT_EXPIRED"
    FACT_REVOKED = "FACT_REVOKED"


# ============================================================================
# PROVENANCE PRECEDENCE (for tie-breaking)
# ============================================================================

PROVENANCE_PRECEDENCE: Dict[ProvenanceType, int] = {
    ProvenanceType.SYSTEM_KNOWN: 0,      # Highest precedence
    ProvenanceType.USER_EXPLICIT: 1,
    ProvenanceType.TOOL_CITED: 2,
    ProvenanceType.DERIVED_SUMMARY: 3,   # Lowest precedence
}


# ============================================================================
# CAPS DATACLASS
# ============================================================================

@dataclass(frozen=True)
class StoreCaps:
    """
    Caps for memory store.
    
    Deterministic enforcement with fail-closed behavior.
    """
    max_facts_total: int = DEFAULT_MAX_FACTS_TOTAL
    max_facts_per_category: int = DEFAULT_MAX_FACTS_PER_CATEGORY
    
    def is_valid(self) -> bool:
        """Check if caps are valid."""
        return (
            self.max_facts_total > 0 and
            self.max_facts_per_category > 0
        )


# ============================================================================
# EVENT DATACLASSES
# ============================================================================

@dataclass(frozen=True)
class MemoryEvent:
    """
    Base event for append-only log.
    
    All events are immutable and contain no raw user text.
    """
    event_id: str
    event_type: EventType
    fact_id: str
    scope_id: str
    created_at_ms: int


@dataclass(frozen=True)
class FactAddedEvent(MemoryEvent):
    """Event for adding a fact."""
    fact: MemoryFact
    expires_at_ms: int
    
    def __post_init__(self):
        # Ensure event_type is correct
        object.__setattr__(self, 'event_type', EventType.FACT_ADDED)


@dataclass(frozen=True)
class FactExpiredEvent(MemoryEvent):
    """Event for expiring a fact."""
    observed_at_ms: int
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.FACT_EXPIRED)


@dataclass(frozen=True)
class FactRevokedEvent(MemoryEvent):
    """Event for revoking a fact."""
    reason_code: str
    revoked_at_ms: int
    
    def __post_init__(self):
        object.__setattr__(self, 'event_type', EventType.FACT_REVOKED)


# ============================================================================
# ACTIVE FACT METADATA
# ============================================================================

@dataclass(frozen=True)
class ActiveFactMeta:
    """Metadata for an active fact in the derived view."""
    fact: MemoryFact
    expires_at_ms: int
    is_expired: bool
    is_revoked: bool
    added_at_ms: int


# ============================================================================
# CURRENT VIEW (DERIVED)
# ============================================================================

@dataclass
class CurrentView:
    """
    Derived view of current facts from the event log.
    
    Deterministic: same (log, now_ms, caps) => identical view.
    """
    active_facts: Dict[str, ActiveFactMeta]
    dropped_due_to_caps: List[str]
    total_active: int
    per_category_active: Dict[str, int]
    store_version: str
    error_code: Optional[str] = None
    
    def get_fact_ids(self) -> List[str]:
        """Get sorted list of active fact IDs."""
        return sorted(self.active_facts.keys())


# ============================================================================
# EVENT ID GENERATION (DETERMINISTIC)
# ============================================================================

def _compute_event_id(
    scope_id: str,
    event_type: EventType,
    fact_id: str,
    created_at_ms: int,
    extra_fields: str = "",
) -> str:
    """
    Compute deterministic event ID via SHA256.
    
    Uses structure-only content (no raw user text values).
    """
    content = f"{scope_id}|{event_type.value}|{fact_id}|{created_at_ms}|{extra_fields}"
    hash_bytes = sha256(content.encode("utf-8")).hexdigest()
    return hash_bytes[:MAX_EVENT_ID_LEN]


def _compute_fact_added_event_id(
    scope_id: str,
    fact: MemoryFact,
    created_at_ms: int,
    expires_at_ms: int,
) -> str:
    """Compute event ID for FACT_ADDED event."""
    # Use structure-only fields (no raw values)
    extra = f"{expires_at_ms}|{fact.category.value}|{fact.key}|{fact.value_type.value}"
    if fact.value_str:
        extra += f"|str_len:{len(fact.value_str)}"
    if fact.value_list_str:
        extra += f"|list_len:{len(fact.value_list_str)}"
    return _compute_event_id(scope_id, EventType.FACT_ADDED, fact.fact_id, created_at_ms, extra)


def _compute_fact_expired_event_id(
    scope_id: str,
    fact_id: str,
    created_at_ms: int,
    observed_at_ms: int,
) -> str:
    """Compute event ID for FACT_EXPIRED event."""
    extra = f"observed:{observed_at_ms}"
    return _compute_event_id(scope_id, EventType.FACT_EXPIRED, fact_id, created_at_ms, extra)


def _compute_fact_revoked_event_id(
    scope_id: str,
    fact_id: str,
    created_at_ms: int,
    reason_code: str,
    revoked_at_ms: int,
) -> str:
    """Compute event ID for FACT_REVOKED event."""
    extra = f"reason:{reason_code}|revoked:{revoked_at_ms}"
    return _compute_event_id(scope_id, EventType.FACT_REVOKED, fact_id, created_at_ms, extra)


# ============================================================================
# PRIORITY KEY FOR CAPS ENFORCEMENT
# ============================================================================

def _compute_priority_key(meta: ActiveFactMeta) -> Tuple:
    """
    Compute priority key for deterministic caps enforcement.
    
    Priority order (higher priority = kept):
    1) Higher confidence first (desc) -> negate for sort
    2) Stronger provenance first (lower precedence value)
    3) Later collected_at_ms first (desc) -> negate for sort
    4) Shorter key length first (asc)
    5) fact_id lexicographic asc as final tie-breaker
    """
    fact = meta.fact
    
    # Confidence (negate for descending)
    confidence = -(fact.confidence or 0.0)
    
    # Provenance precedence (lower = stronger)
    prov_precedence = 999
    if fact.provenance and fact.provenance.source_type:
        prov_precedence = PROVENANCE_PRECEDENCE.get(fact.provenance.source_type, 999)
    
    # Collected at (negate for descending)
    collected_at = 0
    if fact.provenance and fact.provenance.collected_at_ms:
        collected_at = -fact.provenance.collected_at_ms
    elif meta.added_at_ms:
        collected_at = -meta.added_at_ms
    
    # Key length (ascending)
    key_len = len(fact.key) if fact.key else 0
    
    # Fact ID (ascending, final tie-breaker)
    fact_id = fact.fact_id
    
    return (confidence, prov_precedence, collected_at, key_len, fact_id)


# ============================================================================
# DERIVED VIEW COMPUTATION
# ============================================================================

def recompute_current_view(
    events: List[MemoryEvent],
    now_ms: int,
    caps: StoreCaps,
) -> CurrentView:
    """
    Recompute current facts view from event log.
    
    Deterministic: same inputs => identical output.
    
    Args:
        events: List of events in log order
        now_ms: Current time in milliseconds
        caps: Store caps for enforcement
    
    Returns:
        CurrentView with active facts and metadata
    """
    # Validate caps
    if not caps.is_valid():
        return CurrentView(
            active_facts={},
            dropped_due_to_caps=[],
            total_active=0,
            per_category_active={},
            store_version=MEMORY_STORE_VERSION,
            error_code="INVALID_CAPS",
        )
    
    # Track fact states
    facts_by_id: Dict[str, ActiveFactMeta] = {}
    revoked_ids: set = set()
    expired_ids: set = set()
    
    # Replay events in log order
    for event in events:
        if isinstance(event, FactAddedEvent):
            # Reject duplicate FACT_ADDED unless previously revoked
            if event.fact_id in facts_by_id and event.fact_id not in revoked_ids:
                # Duplicate - skip (policy: reject duplicates)
                continue
            
            # If previously revoked, allow re-add
            if event.fact_id in revoked_ids:
                revoked_ids.discard(event.fact_id)
            
            # Check derived expiry
            is_expired = event.expires_at_ms <= now_ms
            
            facts_by_id[event.fact_id] = ActiveFactMeta(
                fact=event.fact,
                expires_at_ms=event.expires_at_ms,
                is_expired=is_expired,
                is_revoked=False,
                added_at_ms=event.created_at_ms,
            )
        
        elif isinstance(event, FactExpiredEvent):
            # Mark as expired (event dominates)
            expired_ids.add(event.fact_id)
            if event.fact_id in facts_by_id:
                meta = facts_by_id[event.fact_id]
                facts_by_id[event.fact_id] = ActiveFactMeta(
                    fact=meta.fact,
                    expires_at_ms=meta.expires_at_ms,
                    is_expired=True,
                    is_revoked=meta.is_revoked,
                    added_at_ms=meta.added_at_ms,
                )
        
        elif isinstance(event, FactRevokedEvent):
            # Mark as revoked (revocation dominates)
            revoked_ids.add(event.fact_id)
            if event.fact_id in facts_by_id:
                meta = facts_by_id[event.fact_id]
                facts_by_id[event.fact_id] = ActiveFactMeta(
                    fact=meta.fact,
                    expires_at_ms=meta.expires_at_ms,
                    is_expired=meta.is_expired,
                    is_revoked=True,
                    added_at_ms=meta.added_at_ms,
                )
    
    # Filter to only active facts (not expired, not revoked)
    active_facts: Dict[str, ActiveFactMeta] = {}
    for fact_id, meta in facts_by_id.items():
        # Check derived expiry
        is_derived_expired = meta.expires_at_ms <= now_ms
        # Check event-based expiry
        is_event_expired = fact_id in expired_ids
        # Check revocation
        is_revoked = fact_id in revoked_ids
        
        if not is_derived_expired and not is_event_expired and not is_revoked:
            active_facts[fact_id] = meta
    
    # Apply caps enforcement
    dropped_due_to_caps: List[str] = []
    
    # Stage A: Per-category cap
    by_category: Dict[str, List[Tuple[str, ActiveFactMeta]]] = {}
    for fact_id, meta in active_facts.items():
        cat = meta.fact.category.value
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append((fact_id, meta))
    
    # Sort each category by priority and trim
    for cat, items in by_category.items():
        # Sort by priority key (lower = higher priority = kept)
        items.sort(key=lambda x: _compute_priority_key(x[1]))
        
        if len(items) > caps.max_facts_per_category:
            # Drop excess (lower priority = later in sorted list)
            for fact_id, _ in items[caps.max_facts_per_category:]:
                dropped_due_to_caps.append(fact_id)
                del active_facts[fact_id]
            by_category[cat] = items[:caps.max_facts_per_category]
    
    # Stage B: Total cap
    if len(active_facts) > caps.max_facts_total:
        # Sort all active facts by priority
        all_items = [(fid, meta) for fid, meta in active_facts.items()]
        all_items.sort(key=lambda x: _compute_priority_key(x[1]))
        
        # Drop excess
        for fact_id, _ in all_items[caps.max_facts_total:]:
            if fact_id in active_facts:  # May already be dropped
                dropped_due_to_caps.append(fact_id)
                del active_facts[fact_id]
    
    # Sort dropped list for determinism
    dropped_due_to_caps.sort()
    
    # Compute per-category counts
    per_category_active: Dict[str, int] = {}
    for meta in active_facts.values():
        cat = meta.fact.category.value
        per_category_active[cat] = per_category_active.get(cat, 0) + 1
    
    return CurrentView(
        active_facts=active_facts,
        dropped_due_to_caps=dropped_due_to_caps,
        total_active=len(active_facts),
        per_category_active=per_category_active,
        store_version=MEMORY_STORE_VERSION,
        error_code=None,
    )


# ============================================================================
# MEMORY EVENT LOG STORE
# ============================================================================

class MemoryEventLogStore:
    """
    Append-only event log store with derived view computation.
    
    Guarantees:
    - Events are immutable once appended
    - read_events returns copies
    - Recomputation is deterministic
    """
    
    def __init__(self):
        self._events_by_scope: Dict[str, List[MemoryEvent]] = {}
    
    def append_event(self, scope_id: str, event: MemoryEvent) -> bool:
        """
        Append a single event to the log.
        
        Returns True if appended, False if rejected.
        """
        # Validate scope_id
        if not scope_id or len(scope_id) > MAX_SCOPE_ID_LEN:
            return False
        
        # Initialize scope if needed
        if scope_id not in self._events_by_scope:
            self._events_by_scope[scope_id] = []
        
        # Check max events
        if len(self._events_by_scope[scope_id]) >= MAX_EVENTS_PER_SCOPE:
            return False
        
        # Append (immutable - we store the event as-is)
        self._events_by_scope[scope_id].append(event)
        return True
    
    def append_events(self, scope_id: str, events: List[MemoryEvent]) -> int:
        """
        Append multiple events to the log.
        
        Returns count of successfully appended events.
        """
        count = 0
        for event in events:
            if self.append_event(scope_id, event):
                count += 1
        return count
    
    def read_events(self, scope_id: str) -> List[MemoryEvent]:
        """
        Read all events for a scope.
        
        Returns a copy of the event list.
        """
        if scope_id not in self._events_by_scope:
            return []
        # Return a copy to prevent external mutation
        return list(self._events_by_scope[scope_id])
    
    def recompute(self, scope_id: str, now_ms: int, caps: StoreCaps) -> CurrentView:
        """
        Recompute current view for a scope.
        
        Deterministic: same (events, now_ms, caps) => identical view.
        """
        events = self.read_events(scope_id)
        return recompute_current_view(events, now_ms, caps)
    
    def event_count(self, scope_id: str) -> int:
        """Get event count for a scope."""
        if scope_id not in self._events_by_scope:
            return 0
        return len(self._events_by_scope[scope_id])


# ============================================================================
# COMPATIBILITY WRAPPER (for adapter.py)
# ============================================================================

class MemoryStore:
    """
    Compatibility wrapper that provides the MemoryStore interface
    expected by the adapter, backed by the event log store.
    
    This ensures backwards compatibility with existing code.
    """
    
    def __init__(self, scope_id: str = "default"):
        self._scope_id = scope_id
        self._event_store = MemoryEventLogStore()
        self._default_caps = StoreCaps()
    
    def write_facts(
        self,
        facts: List[MemoryFact],
        ttl_applied_ms: int,
        now_ms: int,
    ) -> List[str]:
        """
        Write facts to store (legacy method for backwards compatibility).
        
        Returns list of fact_ids written (stable order).
        """
        expires_at_ms = now_ms + ttl_applied_ms
        return self.write_facts_with_expiry(facts, expires_at_ms)
    
    def write_facts_with_expiry(
        self,
        facts: List[MemoryFact],
        expires_at_ms: int,
    ) -> List[str]:
        """
        Write facts to store with pre-computed bucketed expiry.
        
        Creates FACT_ADDED events for each fact.
        Returns list of fact_ids written (stable order).
        """
        fact_ids = []
        created_at_ms = expires_at_ms  # Use expires_at_ms as proxy for now_ms
        
        for fact in facts:
            event_id = _compute_fact_added_event_id(
                self._scope_id, fact, created_at_ms, expires_at_ms
            )
            event = FactAddedEvent(
                event_id=event_id,
                event_type=EventType.FACT_ADDED,
                fact_id=fact.fact_id,
                scope_id=self._scope_id,
                created_at_ms=created_at_ms,
                fact=fact,
                expires_at_ms=expires_at_ms,
            )
            if self._event_store.append_event(self._scope_id, event):
                fact_ids.append(fact.fact_id)
        
        return fact_ids
    
    def get_fact(self, fact_id: str, now_ms: int = 0) -> Optional[MemoryFact]:
        """Get a fact by ID (if active)."""
        view = self._event_store.recompute(self._scope_id, now_ms, self._default_caps)
        if fact_id in view.active_facts:
            return view.active_facts[fact_id].fact
        return None
    
    def count(self, now_ms: int = 0) -> int:
        """Get total active fact count."""
        view = self._event_store.recompute(self._scope_id, now_ms, self._default_caps)
        return view.total_active
    
    def get_current_facts(self, now_ms: int, caps: Optional[StoreCaps] = None) -> List[MemoryFact]:
        """
        Get current active facts from derived view.
        
        Returns list of MemoryFact objects that are currently active.
        """
        if caps is None:
            caps = self._default_caps
        view = self._event_store.recompute(self._scope_id, now_ms, caps)
        return [meta.fact for meta in view.active_facts.values()]
    
    def get_event_store(self) -> MemoryEventLogStore:
        """Get the underlying event store (for testing)."""
        return self._event_store


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_event_log_store() -> MemoryEventLogStore:
    """Create a new event log store instance."""
    return MemoryEventLogStore()


def create_memory_store(scope_id: str = "default") -> MemoryStore:
    """Create a new memory store instance with compatibility wrapper."""
    return MemoryStore(scope_id)


# ============================================================================
# EVENT FACTORY FUNCTIONS
# ============================================================================

def create_fact_added_event(
    scope_id: str,
    fact: MemoryFact,
    created_at_ms: int,
    expires_at_ms: int,
) -> FactAddedEvent:
    """Create a FACT_ADDED event."""
    event_id = _compute_fact_added_event_id(scope_id, fact, created_at_ms, expires_at_ms)
    return FactAddedEvent(
        event_id=event_id,
        event_type=EventType.FACT_ADDED,
        fact_id=fact.fact_id,
        scope_id=scope_id,
        created_at_ms=created_at_ms,
        fact=fact,
        expires_at_ms=expires_at_ms,
    )


def create_fact_expired_event(
    scope_id: str,
    fact_id: str,
    created_at_ms: int,
    observed_at_ms: int,
) -> FactExpiredEvent:
    """Create a FACT_EXPIRED event."""
    event_id = _compute_fact_expired_event_id(scope_id, fact_id, created_at_ms, observed_at_ms)
    return FactExpiredEvent(
        event_id=event_id,
        event_type=EventType.FACT_EXPIRED,
        fact_id=fact_id,
        scope_id=scope_id,
        created_at_ms=created_at_ms,
        observed_at_ms=observed_at_ms,
    )


def create_fact_revoked_event(
    scope_id: str,
    fact_id: str,
    created_at_ms: int,
    reason_code: str,
    revoked_at_ms: int,
) -> FactRevokedEvent:
    """Create a FACT_REVOKED event."""
    # Bound reason code
    reason_code = reason_code[:MAX_REASON_CODE_LEN] if reason_code else "UNKNOWN"
    event_id = _compute_fact_revoked_event_id(
        scope_id, fact_id, created_at_ms, reason_code, revoked_at_ms
    )
    return FactRevokedEvent(
        event_id=event_id,
        event_type=EventType.FACT_REVOKED,
        fact_id=fact_id,
        scope_id=scope_id,
        created_at_ms=created_at_ms,
        reason_code=reason_code,
        revoked_at_ms=revoked_at_ms,
    )
