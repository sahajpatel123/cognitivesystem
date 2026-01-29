"""
Phase 18 Step 6: Cache + Canonicalization

Deterministic cache keys, canonicalization, and in-memory bounded cache.
All operations are deterministic and fail-closed.
"""

import hashlib
import json
import re
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


DEFAULT_WEB_BUCKET_MS = 900000  # 15 minutes
DEFAULT_DOCS_BUCKET_MS = 3600000  # 60 minutes
DEFAULT_FALLBACK_BUCKET_MS = 3600000  # 60 minutes

TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'gclid', 'fbclid'
}


def canonicalize_query(q: Optional[str]) -> str:
    """
    Canonicalize query string deterministically.
    
    Args:
        q: Raw query string
    
    Returns:
        Canonical query (trimmed, collapsed whitespace, normalized line breaks)
    """
    if not q:
        return ""
    
    q = q.strip()
    
    q = re.sub(r'[\r\n]+', ' ', q)
    
    q = re.sub(r'\s+', ' ', q)
    
    return q


def canonicalize_url(url: Optional[str]) -> str:
    """
    Canonicalize URL deterministically.
    
    Args:
        url: Raw URL string
    
    Returns:
        Canonical URL (lowercase scheme/host, no fragment, no tracking params, sorted query params)
    """
    if not url:
        return ""
    
    url = url.strip()
    if not url:
        return ""
    
    try:
        parsed = urlparse(url)
        
        scheme = parsed.scheme.lower() if parsed.scheme else 'https'
        netloc = parsed.netloc.lower() if parsed.netloc else ''
        
        if ':' in netloc:
            host, port = netloc.rsplit(':', 1)
            try:
                port_int = int(port)
                if (scheme == 'http' and port_int == 80) or (scheme == 'https' and port_int == 443):
                    netloc = host
            except ValueError:
                pass
        
        path = parsed.path or ''
        path = re.sub(r'/+', '/', path)
        
        if path and path != '/' and path.endswith('/'):
            path = path.rstrip('/')
        
        if not path:
            path = '/'
        
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        
        filtered_params = {
            k: v for k, v in query_params.items()
            if k not in TRACKING_PARAMS
        }
        
        sorted_keys = sorted(filtered_params.keys())
        sorted_params = [(k, filtered_params[k][0] if filtered_params[k] else '') for k in sorted_keys]
        query = urlencode(sorted_params)
        
        canonical = urlunparse((scheme, netloc, path, '', query, ''))
        
        return canonical
    
    except Exception:
        return url.strip()


def extract_domain(url: Optional[str]) -> str:
    """
    Extract domain from URL deterministically.
    
    Args:
        url: URL string
    
    Returns:
        Domain (lowercase, without www prefix)
    """
    if not url:
        return ""
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower() if parsed.netloc else ""
        
        if ':' in domain:
            domain = domain.split(':')[0]
        
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain
    except Exception:
        return ""


def compute_canonical_source_id(
    tool: str,
    canonical_url: str,
    domain: str,
    title_length: int,
    snippet_count: int,
    snippet_lengths: tuple,
    metadata_keys: tuple,
) -> str:
    """
    Compute deterministic source ID from structure (no raw text).
    
    Args:
        tool: Tool kind value
        canonical_url: Canonical URL
        domain: Domain
        title_length: Title length
        snippet_count: Number of snippets
        snippet_lengths: Tuple of snippet lengths
        metadata_keys: Tuple of sorted metadata keys
    
    Returns:
        12-char hex hash
    """
    structure = {
        'tool': tool,
        'canonical_url': canonical_url,
        'domain': domain,
        'title_length': title_length,
        'snippet_count': snippet_count,
        'snippet_lengths': snippet_lengths,
        'metadata_keys': metadata_keys,
    }
    
    canonical_json = json.dumps(structure, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    hash_digest = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    
    return hash_digest[:12]


def compute_time_bucket(now_ms: int, bucket_ms: int) -> int:
    """
    Compute time bucket deterministically.
    
    Args:
        now_ms: Current time in milliseconds
        bucket_ms: Bucket size in milliseconds
    
    Returns:
        Time bucket (floor division)
    """
    return now_ms // bucket_ms


def get_default_bucket_ms(tool_kind: str) -> int:
    """
    Get default bucket size for tool kind.
    
    Args:
        tool_kind: Tool kind value
    
    Returns:
        Bucket size in milliseconds
    """
    if tool_kind == 'WEB':
        return DEFAULT_WEB_BUCKET_MS
    elif tool_kind == 'DOCS':
        return DEFAULT_DOCS_BUCKET_MS
    else:
        return DEFAULT_FALLBACK_BUCKET_MS


@dataclass(frozen=True)
class CacheKeyParts:
    """Human-inspectable cache key parts."""
    canonical_query: str
    tool_kind: str
    env_mode: str
    policy_caps: Dict[str, Any]
    request_flags: Dict[str, Any]
    time_bucket: int


@dataclass
class CacheEntry:
    """Cache entry with value and metadata."""
    value: Any
    created_bucket: int
    inserted_seq: int


def make_cache_key(
    query: str,
    tool_kind: str,
    env_mode: str,
    policy_caps: Dict[str, Any],
    request_flags: Dict[str, Any],
    now_ms: int,
    bucket_ms: Optional[int] = None,
) -> tuple:
    """
    Create deterministic cache key.
    
    Args:
        query: Query string
        tool_kind: Tool kind
        env_mode: Environment mode
        policy_caps: Policy caps (stable primitives only)
        request_flags: Request flags (citations_required, allow_cache, etc.)
        now_ms: Current time in milliseconds
        bucket_ms: Optional bucket size (defaults based on tool_kind)
    
    Returns:
        Tuple of (key_hash, key_parts)
    """
    canonical_q = canonicalize_query(query)
    
    if bucket_ms is None:
        bucket_ms = get_default_bucket_ms(tool_kind)
    
    time_bucket = compute_time_bucket(now_ms, bucket_ms)
    
    sorted_caps = {k: policy_caps[k] for k in sorted(policy_caps.keys())}
    sorted_flags = {k: request_flags[k] for k in sorted(request_flags.keys())}
    
    key_parts = CacheKeyParts(
        canonical_query=canonical_q,
        tool_kind=tool_kind,
        env_mode=env_mode,
        policy_caps=sorted_caps,
        request_flags=sorted_flags,
        time_bucket=time_bucket,
    )
    
    key_dict = asdict(key_parts)
    key_json = json.dumps(key_dict, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    key_hash = hashlib.sha256(key_json.encode('utf-8')).hexdigest()
    
    return (key_hash, key_parts)


class ResearchCache:
    """
    In-memory bounded cache with deterministic eviction.
    
    Eviction policy: FIFO by inserted_seq.
    """
    
    def __init__(self, max_entries: int = 128):
        """
        Initialize cache.
        
        Args:
            max_entries: Maximum number of entries
        """
        self.max_entries = max_entries
        self._cache: Dict[str, CacheEntry] = {}
        self._seq_counter = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if miss
        """
        try:
            entry = self._cache.get(key)
            if entry is None:
                return None
            return entry.value
        except Exception:
            return None
    
    def put(self, key: str, value: Any, created_bucket: int) -> None:
        """
        Put value into cache with eviction if needed.
        
        Args:
            key: Cache key
            value: Value to cache
            created_bucket: Time bucket when value was created
        """
        try:
            if len(self._cache) >= self.max_entries and key not in self._cache:
                self._evict_one()
            
            self._seq_counter += 1
            self._cache[key] = CacheEntry(
                value=value,
                created_bucket=created_bucket,
                inserted_seq=self._seq_counter,
            )
        except Exception:
            pass
    
    def _evict_one(self) -> None:
        """Evict oldest entry by inserted_seq (FIFO)."""
        if not self._cache:
            return
        
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].inserted_seq)
        del self._cache[oldest_key]
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._seq_counter = 0
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)
