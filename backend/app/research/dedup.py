"""
Phase 18 Step 6: Deduplication

Deterministic deduplication of SourceBundle lists with stable ordering.
"""

from typing import List, Tuple, Optional
from backend.app.retrieval.types import SourceBundle
from backend.app.research.cache import canonicalize_url, extract_domain


def compute_dedup_key(bundle: SourceBundle, canonical_url: str) -> Tuple:
    """
    Compute dedup key for SourceBundle.
    
    Priority:
    1) (tool_kind, canonical_url) if url present and non-empty
    2) else (tool_kind, source_id) if present
    3) else fallback to (tool_kind, domain, title_length, snippet_count, snippet_lengths)
    
    Args:
        bundle: SourceBundle
        canonical_url: Pre-computed canonical URL
    
    Returns:
        Dedup key tuple
    """
    tool_kind = bundle.tool.value if hasattr(bundle.tool, 'value') else str(bundle.tool)
    
    if canonical_url:
        return ('url', tool_kind, canonical_url)
    
    if bundle.source_id:
        return ('id', tool_kind, bundle.source_id)
    
    title_length = len(bundle.title) if bundle.title else 0
    snippet_count = len(bundle.snippets)
    snippet_lengths = tuple(len(s.text) for s in bundle.snippets)
    
    return ('fallback', tool_kind, bundle.domain, title_length, snippet_count, snippet_lengths)


def compute_winner_score(bundle: SourceBundle, canonical_url: str) -> Tuple:
    """
    Compute winner selection score for SourceBundle.
    
    Higher score wins (lexicographically).
    
    Priority:
    1) More non-empty metadata keys (count)
    2) Higher snippet_count
    3) Longer total snippet text length
    4) Lexicographically smaller canonical_url
    5) Lexicographically smaller source_id
    
    Args:
        bundle: SourceBundle
        canonical_url: Pre-computed canonical URL
    
    Returns:
        Score tuple (negated for higher-wins comparison)
    """
    metadata_count = len(bundle.metadata) if bundle.metadata else 0
    snippet_count = len(bundle.snippets)
    total_snippet_length = sum(len(s.text) for s in bundle.snippets)
    
    canonical_url_for_sort = canonical_url if canonical_url else "zzzzz"
    source_id_for_sort = bundle.source_id if bundle.source_id else "zzzzz"
    
    return (
        -metadata_count,
        -snippet_count,
        -total_snippet_length,
        canonical_url_for_sort,
        source_id_for_sort,
    )


def dedup_bundles(bundles: List[SourceBundle]) -> List[SourceBundle]:
    """
    Deduplicate SourceBundle list deterministically.
    
    Args:
        bundles: List of SourceBundle
    
    Returns:
        Deduplicated list with stable ordering
    """
    if not bundles:
        return []
    
    canonical_urls = {}
    canonical_domains = {}
    
    for bundle in bundles:
        canonical_urls[id(bundle)] = canonicalize_url(bundle.url)
        canonical_domains[id(bundle)] = extract_domain(bundle.url) if bundle.url else bundle.domain
    
    dedup_map = {}
    
    for bundle in bundles:
        canonical_url = canonical_urls[id(bundle)]
        dedup_key = compute_dedup_key(bundle, canonical_url)
        
        if dedup_key not in dedup_map:
            dedup_map[dedup_key] = bundle
        else:
            existing = dedup_map[dedup_key]
            existing_canonical_url = canonical_urls[id(existing)]
            
            existing_score = compute_winner_score(existing, existing_canonical_url)
            candidate_score = compute_winner_score(bundle, canonical_url)
            
            if candidate_score < existing_score:
                dedup_map[dedup_key] = bundle
    
    deduped_bundles = list(dedup_map.values())
    
    def sort_key(bundle: SourceBundle) -> Tuple:
        tool_kind = bundle.tool.value if hasattr(bundle.tool, 'value') else str(bundle.tool)
        canonical_url = canonical_urls[id(bundle)]
        domain = canonical_domains[id(bundle)]
        source_id = bundle.source_id if bundle.source_id else ""
        
        return (tool_kind, domain, canonical_url, source_id)
    
    deduped_bundles.sort(key=sort_key)
    
    return deduped_bundles
