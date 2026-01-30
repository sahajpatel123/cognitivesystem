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
    # Legacy
    "get_redis",
    "load_cognitive_style",
    "save_cognitive_style",
    "load_hypotheses",
    "save_hypotheses",
    "load_session_summary",
    "save_session_summary",
]
