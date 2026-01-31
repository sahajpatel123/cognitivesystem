"""
Phase 19: Memory subsystem.

Exports:
- Phase 19 schema and adapter (new)
- Legacy session memory functions (backwards compatibility)
"""

# Phase 19 exports
from backend.app.memory.schema import (
    MemoryFact,
    MemoryCategory,
    MemoryValueType,
    Provenance,
    ProvenanceType,
    validate_fact,
    sanitize_and_validate_fact,
    validate_fact_dict,
)

from backend.app.memory.adapter import (
    MemoryWriteRequest,
    WriteResult,
    MemoryStore,
    write_memory,
    create_store,
    Tier,
    TierCaps,
    TIER_CAPS,
    ReasonCode,
)

# Phase 19 Step 3: TTL Policy Engine
from backend.app.memory.ttl_policy import (
    resolve_ttl,
    TTLClass,
    PlanTier,
    TTLDecision,
    TTL_POLICY_VERSION,
    TTL_1H,
    TTL_1D,
    TTL_10D,
    REQUEST_TIME_BUCKET_MS,
)

# Phase 19 Step 4: Memory Store (Append-only Log + Derived View)
from backend.app.memory.store import (
    MEMORY_STORE_VERSION,
    EventType,
    StoreCaps,
    MemoryEvent,
    FactAddedEvent,
    FactExpiredEvent,
    FactRevokedEvent,
    ActiveFactMeta,
    CurrentView,
    MemoryEventLogStore,
    recompute_current_view,
    create_event_log_store,
    create_memory_store,
    create_fact_added_event,
    create_fact_expired_event,
    create_fact_revoked_event,
)

# Phase 19 Step 5: Read Boundary + Bounded MemoryBundle
from backend.app.memory.read import (
    MemoryReadRequest,
    ReadTemplate,
    MemoryBundle,
    BundleReason,
    read_memory_bundle,
)

# Legacy exports for backwards compatibility (used by service.py)
from backend.app.memory.legacy import (
    get_redis,
    load_cognitive_style,
    save_cognitive_style,
    load_hypotheses,
    save_hypotheses,
    load_session_summary,
    save_session_summary,
)

__all__ = [
    # Phase 19 schema
    "MemoryFact",
    "MemoryCategory",
    "MemoryValueType",
    "Provenance",
    "ProvenanceType",
    "validate_fact",
    "sanitize_and_validate_fact",
    "validate_fact_dict",
    # Phase 19 adapter
    "MemoryWriteRequest",
    "WriteResult",
    "MemoryStore",
    "write_memory",
    "create_store",
    "Tier",
    "TierCaps",
    "TIER_CAPS",
    "ReasonCode",
    # Phase 19 TTL policy
    "resolve_ttl",
    "TTLClass",
    "PlanTier",
    "TTLDecision",
    "TTL_POLICY_VERSION",
    "TTL_1H",
    "TTL_1D",
    "TTL_10D",
    "REQUEST_TIME_BUCKET_MS",
    # Phase 19 store
    "MEMORY_STORE_VERSION",
    "EventType",
    "StoreCaps",
    "MemoryEvent",
    "FactAddedEvent",
    "FactExpiredEvent",
    "FactRevokedEvent",
    "ActiveFactMeta",
    "CurrentView",
    "MemoryEventLogStore",
    "recompute_current_view",
    "create_event_log_store",
    "create_memory_store",
    "create_fact_added_event",
    "create_fact_expired_event",
    "create_fact_revoked_event",
    # Phase 19 read boundary
    "MemoryReadRequest",
    "ReadTemplate",
    "MemoryBundle",
    "BundleReason",
    "read_memory_bundle",
    # Legacy
    "get_redis",
    "load_cognitive_style",
    "save_cognitive_style",
    "load_hypotheses",
    "save_hypotheses",
    "load_session_summary",
    "save_session_summary",
]
