"""
Phase 18 Step 1: Retrieval Adapter (Single Chokepoint)

This is the ONLY entry point for all retrieval operations.
All web/doc research calls MUST go through retrieve().

Contract guarantees:
- Single chokepoint
- Deterministic output
- Fail-closed on errors
- Non-agentic (no loops, no planning)
- Normalized SourceBundle output only
"""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from backend.app.retrieval.types import (
    ToolKind,
    EnvMode,
    PolicyCaps,
    RequestFlags,
    SourceSnippet,
    SourceBundle,
    MAX_SNIPPET_TEXT_LENGTH,
    MAX_SNIPPETS_PER_SOURCE,
    MAX_TITLE_LENGTH,
    MAX_URL_LENGTH,
    MAX_METADATA_KEYS,
    MAX_QUERY_LENGTH,
)


@dataclass(frozen=True)
class RetrievalRequest:
    """
    Single allowed input structure for retrieval adapter.
    
    NO user profiles, NO memory blobs, NO hidden state.
    """
    query: str
    policy_caps: PolicyCaps
    allowed_tools: List[ToolKind]
    env_mode: EnvMode
    request_flags: RequestFlags


class RetrievalError(Exception):
    """Typed exception for retrieval failures."""
    pass


def canonicalize_query(query: str) -> str:
    """
    Canonicalize query deterministically.
    
    - Strip leading/trailing whitespace
    - Collapse internal whitespace to single spaces
    - Enforce max length
    """
    if not query:
        return ""
    
    canonical = re.sub(r'\s+', ' ', query.strip())
    
    if len(canonical) > MAX_QUERY_LENGTH:
        canonical = canonical[:MAX_QUERY_LENGTH]
    
    return canonical


def canonicalize_url(url: str) -> str:
    """
    Canonicalize URL deterministically.
    
    - Strip whitespace
    - Lower-case scheme and host
    - Enforce max length
    """
    if not url:
        return ""
    
    url = url.strip()
    
    if len(url) > MAX_URL_LENGTH:
        url = url[:MAX_URL_LENGTH]
    
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower() if parsed.scheme else ""
        netloc = parsed.netloc.lower() if parsed.netloc else ""
        path = parsed.path
        params = parsed.params
        query = parsed.query
        fragment = parsed.fragment
        
        canonical = f"{scheme}://{netloc}{path}"
        if params:
            canonical += f";{params}"
        if query:
            canonical += f"?{query}"
        if fragment:
            canonical += f"#{fragment}"
        
        return canonical
    except Exception:
        return url


def extract_domain(url: str) -> str:
    """
    Extract domain from URL robustly.
    
    Fallback to "unknown" if parsing fails.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower() if parsed.netloc else "unknown"
        return domain
    except Exception:
        return "unknown"


def compute_source_id(tool: ToolKind, url: str, domain: str, title: Optional[str], snippets: List[SourceSnippet], metadata: dict) -> str:
    """
    Compute deterministic source_id.
    
    Hash includes:
    - tool
    - url
    - domain
    - title (if present)
    - snippet lengths (NOT content, for privacy)
    - metadata keys sorted (NOT values, for privacy)
    
    This ensures determinism while avoiding text leakage in ID.
    """
    id_data = {
        "tool": tool.value,
        "url": url,
        "domain": domain,
        "title": title if title else None,
        "snippet_lengths": [len(s.text) for s in snippets],
        "metadata_keys": sorted(metadata.keys()),
    }
    
    canonical_json = json.dumps(id_data, sort_keys=True, separators=(',', ':'))
    hash_digest = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    
    return hash_digest


def validate_metadata(metadata: dict) -> bool:
    """
    Validate metadata contains only primitives and is bounded.
    
    Allowed types: str, int, bool, float
    Max keys: MAX_METADATA_KEYS
    """
    if not isinstance(metadata, dict):
        return False
    
    if len(metadata) > MAX_METADATA_KEYS:
        return False
    
    for key, value in metadata.items():
        if not isinstance(key, str):
            return False
        if not isinstance(value, (str, int, bool, float)):
            return False
    
    return True


def normalize_raw_source(tool: ToolKind, raw: dict, retrieved_at: str) -> Optional[SourceBundle]:
    """
    Normalize raw tool output to SourceBundle.
    
    Returns None if source is invalid or malformed.
    Enforces all bounds and schema constraints.
    """
    try:
        url = raw.get("url", "")
        if not url:
            return None
        
        url = canonicalize_url(url)
        domain = extract_domain(url)
        
        title = raw.get("title")
        if title and len(title) > MAX_TITLE_LENGTH:
            title = title[:MAX_TITLE_LENGTH]
        
        raw_snippets = raw.get("snippets", [])
        if not isinstance(raw_snippets, list):
            return None
        
        snippets = []
        for raw_snippet in raw_snippets[:MAX_SNIPPETS_PER_SOURCE]:
            if isinstance(raw_snippet, dict):
                text = raw_snippet.get("text", "")
            elif isinstance(raw_snippet, str):
                text = raw_snippet
            else:
                continue
            
            if len(text) > MAX_SNIPPET_TEXT_LENGTH:
                text = text[:MAX_SNIPPET_TEXT_LENGTH]
            
            snippet = SourceSnippet(
                text=text,
                start=raw_snippet.get("start") if isinstance(raw_snippet, dict) else None,
                end=raw_snippet.get("end") if isinstance(raw_snippet, dict) else None,
            )
            snippets.append(snippet)
        
        if not snippets:
            return None
        
        metadata = raw.get("metadata", {})
        if not validate_metadata(metadata):
            metadata = {}
        
        source_id = compute_source_id(tool, url, domain, title, snippets, metadata)
        
        return SourceBundle(
            source_id=source_id,
            tool=tool,
            url=url,
            domain=domain,
            title=title,
            retrieved_at=retrieved_at,
            snippets=snippets,
            metadata=metadata,
        )
    except Exception:
        return None


def stable_sort_sources(sources: List[SourceBundle]) -> List[SourceBundle]:
    """
    Sort sources deterministically.
    
    Order:
    1. tool (enum order: WEB, DOCS)
    2. domain (lexicographic)
    3. url (lexicographic)
    4. source_id (lexicographic)
    """
    return sorted(
        sources,
        key=lambda s: (s.tool.value, s.domain, s.url, s.source_id)
    )


def run_tool_stub(tool: ToolKind, query: str, caps: PolicyCaps) -> List[dict]:
    """
    Tool runner stub for Step 18.1.
    
    In production, this raises NotImplementedError.
    In tests, this is monkeypatched to return controlled raw results.
    
    Step 18.2+ will implement actual tool connectors.
    """
    raise NotImplementedError(f"Tool {tool.value} not implemented in Step 18.1")


def retrieve(req: RetrievalRequest) -> List[SourceBundle]:
    """
    Single chokepoint for all retrieval operations.
    
    Contract:
    - Validates inputs
    - Canonicalizes query
    - Dispatches to tool stubs
    - Normalizes outputs to SourceBundle
    - Enforces bounds
    - Returns stable-sorted list
    - Fail-closed: returns [] on errors
    
    Args:
        req: RetrievalRequest with query, caps, tools, env, flags
    
    Returns:
        List[SourceBundle]: Normalized, bounded, sorted sources
    """
    try:
        if not req.query:
            return []
        
        if not req.allowed_tools:
            return []
        
        if req.policy_caps.max_results < 1 or req.policy_caps.max_results > 10:
            return []
        
        canonical_query = canonicalize_query(req.query)
        if not canonical_query:
            return []
        
        retrieved_at = "2026-01-29T00:00:00Z"
        
        all_sources = []
        
        for tool in req.allowed_tools:
            if not isinstance(tool, ToolKind):
                continue
            
            try:
                raw_results = run_tool_stub(tool, canonical_query, req.policy_caps)
                
                for raw in raw_results:
                    normalized = normalize_raw_source(tool, raw, retrieved_at)
                    if normalized:
                        all_sources.append(normalized)
            except NotImplementedError:
                continue
            except Exception:
                continue
        
        all_sources = all_sources[:req.policy_caps.max_results]
        
        sorted_sources = stable_sort_sources(all_sources)
        
        return sorted_sources
    
    except Exception:
        return []
