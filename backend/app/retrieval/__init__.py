"""
Phase 18 Step 1: Retrieval Adapter Boundary

Single chokepoint for all research/retrieval operations.
"""

from backend.app.retrieval.adapter import retrieve, RetrievalRequest
from backend.app.retrieval.types import (
    ToolKind,
    EnvMode,
    PolicyCaps,
    RequestFlags,
    SourceSnippet,
    SourceBundle,
)

__all__ = [
    "retrieve",
    "RetrievalRequest",
    "ToolKind",
    "EnvMode",
    "PolicyCaps",
    "RequestFlags",
    "SourceSnippet",
    "SourceBundle",
]
