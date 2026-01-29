"""
Phase 18 Step 1: Retrieval Types and Schemas

Strict dataclass definitions for retrieval adapter boundary.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class ToolKind(Enum):
    """Allowed retrieval tools."""
    WEB = "WEB"
    DOCS = "DOCS"


class EnvMode(Enum):
    """Environment mode for retrieval."""
    DEV = "DEV"
    STAGING = "STAGING"
    PROD = "PROD"


@dataclass(frozen=True)
class PolicyCaps:
    """
    Policy caps for retrieval operations.
    
    Bounds are deterministic and enforced by adapter.
    """
    max_results: int  # 1-10
    per_tool_timeout_ms: int  # e.g., 5000
    total_timeout_ms: int  # e.g., 15000
    max_tool_calls_total: int = 5  # Future: Step 18.2+
    max_tool_calls_per_minute: int = 10  # Future: Step 18.2+


@dataclass(frozen=True)
class RequestFlags:
    """Request-level flags for retrieval."""
    citations_required: bool = True
    allow_cache: bool = False  # Future: Step 18.6+


@dataclass(frozen=True)
class SourceSnippet:
    """
    A single text snippet from a source.
    
    Bounded to prevent unbounded content.
    """
    text: str  # Max 500 chars enforced by adapter
    start: Optional[int] = None
    end: Optional[int] = None


@dataclass(frozen=True)
class SourceBundle:
    """
    Normalized source output from retrieval adapter.
    
    This is the ONLY output format from retrieve().
    No free-form text, no assistant summaries, no tool directives.
    """
    source_id: str  # Deterministic hash of structure
    tool: ToolKind
    url: str  # Canonical URL or doc URI
    domain: str  # Extracted host
    title: Optional[str]  # Bounded to 200 chars
    retrieved_at: str  # ISO timestamp (deterministic in tests)
    snippets: List[SourceSnippet]  # Bounded count (max 5)
    metadata: Dict[str, Any]  # Only primitives: str/int/bool/float, max 10 keys


# Bounds constants
MAX_SNIPPET_TEXT_LENGTH = 500
MAX_SNIPPETS_PER_SOURCE = 5
MAX_TITLE_LENGTH = 200
MAX_URL_LENGTH = 2000
MAX_METADATA_KEYS = 10
MAX_QUERY_LENGTH = 500
