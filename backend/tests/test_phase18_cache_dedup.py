"""
Phase 18 Step 6: Cache + Dedup + Canonicalization Tests

Comprehensive tests for cache, canonicalization, and deduplication:
- Determinism (replay 20 times)
- Cache key stability
- URL canonicalization
- Dedup winner selection
- Stable ordering after dedup
"""

import json
import random
from typing import List

from backend.app.retrieval.types import SourceBundle, SourceSnippet, ToolKind
from backend.app.research.cache import (
    canonicalize_query,
    canonicalize_url,
    extract_domain,
    compute_canonical_source_id,
    compute_time_bucket,
    get_default_bucket_ms,
    make_cache_key,
    ResearchCache,
    DEFAULT_WEB_BUCKET_MS,
    DEFAULT_DOCS_BUCKET_MS,
)
from backend.app.research.dedup import (
    dedup_bundles,
    compute_dedup_key,
    compute_winner_score,
)


def make_test_bundle(
    source_id: str,
    url: str,
    domain: str,
    title: str,
    snippets_text: List[str],
    tool: ToolKind = ToolKind.WEB,
    metadata: dict = None,
) -> SourceBundle:
    """Create test SourceBundle."""
    if metadata is None:
        metadata = {}
    
    snippets = [SourceSnippet(text=text) for text in snippets_text]
    
    return SourceBundle(
        source_id=source_id,
        tool=tool,
        url=url,
        domain=domain,
        title=title,
        retrieved_at="2026-01-29T00:00:00Z",
        snippets=snippets,
        metadata=metadata,
    )


def bundle_to_stable_repr(bundle: SourceBundle) -> dict:
    """Convert bundle to stable representation for comparison."""
    return {
        'tool': bundle.tool.value if hasattr(bundle.tool, 'value') else str(bundle.tool),
        'domain': bundle.domain,
        'url': canonicalize_url(bundle.url),
        'source_id': bundle.source_id,
        'snippet_count': len(bundle.snippets),
        'snippet_lengths': tuple(len(s.text) for s in bundle.snippets),
        'metadata_keys': tuple(sorted(bundle.metadata.keys())) if bundle.metadata else (),
    }


class TestCanonicalization:
    """Test canonicalization functions."""
    
    def test_query_canonicalization(self):
        """Query canonicalization collapses whitespace and normalizes."""
        q1 = "  test   query  "
        q2 = "test query"
        q3 = "test\n\nquery"
        q4 = "test\r\nquery"
        
        c1 = canonicalize_query(q1)
        c2 = canonicalize_query(q2)
        c3 = canonicalize_query(q3)
        c4 = canonicalize_query(q4)
        
        assert c1 == c2 == c3 == c4
        assert c1 == "test query"
    
    def test_query_empty_handling(self):
        """Empty/None queries return empty string."""
        assert canonicalize_query(None) == ""
        assert canonicalize_query("") == ""
        assert canonicalize_query("   ") == ""
    
    def test_url_canonicalization_basic(self):
        """URL canonicalization lowercases and normalizes."""
        u1 = "HTTPS://EXAMPLE.COM/Path"
        u2 = "https://example.com/Path"
        u3 = "https://example.com/Path/"
        
        c1 = canonicalize_url(u1)
        c2 = canonicalize_url(u2)
        c3 = canonicalize_url(u3)
        
        assert c1.lower() == c2.lower()
        assert c1 == c2 == c3
    
    def test_url_tracking_params_removed(self):
        """Tracking params are removed."""
        url = "https://example.com/page?utm_source=test&utm_medium=email&foo=bar&gclid=123"
        canonical = canonicalize_url(url)
        
        assert 'utm_source' not in canonical
        assert 'utm_medium' not in canonical
        assert 'gclid' not in canonical
        assert 'foo=bar' in canonical
    
    def test_url_query_params_sorted(self):
        """Query params are sorted."""
        u1 = "https://example.com/page?z=1&a=2&m=3"
        u2 = "https://example.com/page?a=2&m=3&z=1"
        
        c1 = canonicalize_url(u1)
        c2 = canonicalize_url(u2)
        
        assert c1 == c2
    
    def test_url_default_ports_removed(self):
        """Default ports are removed."""
        u1 = "http://example.com:80/path"
        u2 = "http://example.com/path"
        u3 = "https://example.com:443/path"
        u4 = "https://example.com/path"
        
        c1 = canonicalize_url(u1)
        c2 = canonicalize_url(u2)
        c3 = canonicalize_url(u3)
        c4 = canonicalize_url(u4)
        
        assert c1 == c2
        assert c3 == c4
    
    def test_url_fragment_removed(self):
        """URL fragments are removed."""
        u1 = "https://example.com/page#section"
        u2 = "https://example.com/page"
        
        c1 = canonicalize_url(u1)
        c2 = canonicalize_url(u2)
        
        assert c1 == c2
        assert '#' not in c1
    
    def test_domain_extraction(self):
        """Domain extraction works correctly."""
        assert extract_domain("https://www.example.com/path") == "example.com"
        assert extract_domain("https://example.com:8080/path") == "example.com"
        assert extract_domain("http://subdomain.example.com") == "subdomain.example.com"
        assert extract_domain("") == ""
        assert extract_domain(None) == ""


class TestCacheKeys:
    """Test cache key generation."""
    
    def test_same_inputs_same_key(self):
        """Same inputs produce same cache key."""
        query = "test query"
        tool_kind = "WEB"
        env_mode = "dev"
        policy_caps = {"max_calls": 10}
        request_flags = {"citations_required": True}
        now_ms = 1000000
        
        key1, parts1 = make_cache_key(query, tool_kind, env_mode, policy_caps, request_flags, now_ms)
        key2, parts2 = make_cache_key(query, tool_kind, env_mode, policy_caps, request_flags, now_ms)
        
        assert key1 == key2
        assert parts1 == parts2
    
    def test_equivalent_whitespace_same_key(self):
        """Equivalent query whitespace produces same key."""
        tool_kind = "WEB"
        env_mode = "dev"
        policy_caps = {}
        request_flags = {}
        now_ms = 1000000
        
        key1, _ = make_cache_key("  test   query  ", tool_kind, env_mode, policy_caps, request_flags, now_ms)
        key2, _ = make_cache_key("test query", tool_kind, env_mode, policy_caps, request_flags, now_ms)
        
        assert key1 == key2
    
    def test_different_time_bucket_different_key(self):
        """Different time buckets produce different keys."""
        query = "test query"
        tool_kind = "WEB"
        env_mode = "dev"
        policy_caps = {}
        request_flags = {}
        
        bucket_ms = DEFAULT_WEB_BUCKET_MS
        now_ms_1 = 0
        now_ms_2 = bucket_ms + 1
        
        key1, _ = make_cache_key(query, tool_kind, env_mode, policy_caps, request_flags, now_ms_1)
        key2, _ = make_cache_key(query, tool_kind, env_mode, policy_caps, request_flags, now_ms_2)
        
        assert key1 != key2
    
    def test_policy_caps_difference_different_key(self):
        """Different policy caps produce different keys."""
        query = "test query"
        tool_kind = "WEB"
        env_mode = "dev"
        request_flags = {}
        now_ms = 1000000
        
        caps1 = {"max_calls": 10}
        caps2 = {"max_calls": 20}
        
        key1, _ = make_cache_key(query, tool_kind, env_mode, caps1, request_flags, now_ms)
        key2, _ = make_cache_key(query, tool_kind, env_mode, caps2, request_flags, now_ms)
        
        assert key1 != key2
    
    def test_time_bucket_computation(self):
        """Time bucket computation is deterministic."""
        bucket_ms = 60000
        
        assert compute_time_bucket(0, bucket_ms) == 0
        assert compute_time_bucket(59999, bucket_ms) == 0
        assert compute_time_bucket(60000, bucket_ms) == 1
        assert compute_time_bucket(120000, bucket_ms) == 2
    
    def test_default_bucket_sizes(self):
        """Default bucket sizes are correct."""
        assert get_default_bucket_ms("WEB") == DEFAULT_WEB_BUCKET_MS
        assert get_default_bucket_ms("DOCS") == DEFAULT_DOCS_BUCKET_MS
        assert get_default_bucket_ms("UNKNOWN") == DEFAULT_DOCS_BUCKET_MS


class TestCacheBehavior:
    """Test cache get/put/eviction."""
    
    def test_put_then_get(self):
        """Put then get returns value."""
        cache = ResearchCache(max_entries=10)
        
        key = "test_key"
        value = [{"data": "test"}]
        
        cache.put(key, value, created_bucket=0)
        result = cache.get(key)
        
        assert result == value
    
    def test_get_miss(self):
        """Get miss returns None."""
        cache = ResearchCache(max_entries=10)
        
        result = cache.get("nonexistent")
        
        assert result is None
    
    def test_eviction_deterministic(self):
        """Eviction is deterministic (FIFO by inserted_seq)."""
        cache = ResearchCache(max_entries=3)
        
        cache.put("key1", "value1", created_bucket=0)
        cache.put("key2", "value2", created_bucket=0)
        cache.put("key3", "value3", created_bucket=0)
        
        assert cache.size() == 3
        
        cache.put("key4", "value4", created_bucket=0)
        
        assert cache.size() == 3
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_clear(self):
        """Clear removes all entries."""
        cache = ResearchCache(max_entries=10)
        
        cache.put("key1", "value1", created_bucket=0)
        cache.put("key2", "value2", created_bucket=0)
        
        cache.clear()
        
        assert cache.size() == 0
        assert cache.get("key1") is None


class TestDedup:
    """Test deduplication logic."""
    
    def test_duplicate_urls_collapse(self):
        """Duplicate URLs collapse to one."""
        bundle1 = make_test_bundle(
            "src1", "https://example.com/page", "example.com", "Title 1", ["snippet1"]
        )
        bundle2 = make_test_bundle(
            "src2", "https://example.com/page?utm_source=test", "example.com", "Title 2", ["snippet2", "snippet3"]
        )
        
        bundles = [bundle1, bundle2]
        deduped = dedup_bundles(bundles)
        
        assert len(deduped) == 1
        assert deduped[0].source_id == "src2"
    
    def test_winner_selection_metadata(self):
        """Winner selection prefers more metadata."""
        bundle1 = make_test_bundle(
            "src1", "https://example.com/page", "example.com", "Title", ["snippet"],
            metadata={"key1": "val1"}
        )
        bundle2 = make_test_bundle(
            "src2", "https://example.com/page", "example.com", "Title", ["snippet"],
            metadata={"key1": "val1", "key2": "val2"}
        )
        
        bundles = [bundle1, bundle2]
        deduped = dedup_bundles(bundles)
        
        assert len(deduped) == 1
        assert deduped[0].source_id == "src2"
    
    def test_winner_selection_snippet_count(self):
        """Winner selection prefers more snippets."""
        bundle1 = make_test_bundle(
            "src1", "https://example.com/page", "example.com", "Title", ["snippet1"]
        )
        bundle2 = make_test_bundle(
            "src2", "https://example.com/page", "example.com", "Title", ["snippet1", "snippet2"]
        )
        
        bundles = [bundle1, bundle2]
        deduped = dedup_bundles(bundles)
        
        assert len(deduped) == 1
        assert deduped[0].source_id == "src2"
    
    def test_stable_ordering(self):
        """Dedup output ordering is stable."""
        bundle1 = make_test_bundle("src1", "https://b.com/page", "b.com", "Title", ["snippet"])
        bundle2 = make_test_bundle("src2", "https://a.com/page", "a.com", "Title", ["snippet"])
        bundle3 = make_test_bundle("src3", "https://c.com/page", "c.com", "Title", ["snippet"])
        
        bundles = [bundle1, bundle2, bundle3]
        deduped = dedup_bundles(bundles)
        
        assert deduped[0].source_id == "src2"
        assert deduped[1].source_id == "src1"
        assert deduped[2].source_id == "src3"
    
    def test_dedup_idempotent(self):
        """Dedup is idempotent."""
        bundle1 = make_test_bundle("src1", "https://example.com/page", "example.com", "Title", ["snippet"])
        bundle2 = make_test_bundle("src2", "https://example.com/page", "example.com", "Title", ["snippet", "snippet2"])
        
        bundles = [bundle1, bundle2]
        deduped1 = dedup_bundles(bundles)
        deduped2 = dedup_bundles(deduped1)
        
        assert len(deduped1) == len(deduped2)
        assert deduped1[0].source_id == deduped2[0].source_id
    
    def test_empty_bundles(self):
        """Empty bundle list returns empty list."""
        deduped = dedup_bundles([])
        assert deduped == []


class TestDeterminism:
    """Test deterministic behavior."""
    
    def test_dedup_replay_identical(self):
        """Same inputs produce identical dedup results across 20 runs with shuffling."""
        bundle1 = make_test_bundle("src1", "https://a.com/page", "a.com", "Title A", ["snippet1"])
        bundle2 = make_test_bundle("src2", "https://b.com/page", "b.com", "Title B", ["snippet2"])
        bundle3 = make_test_bundle("src3", "https://a.com/page?utm_source=test", "a.com", "Title A2", ["snippet3", "snippet4"])
        bundle4 = make_test_bundle("src4", "https://c.com/page", "c.com", "Title C", ["snippet5"])
        
        base_bundles = [bundle1, bundle2, bundle3, bundle4]
        
        results = []
        for _ in range(20):
            shuffled = base_bundles.copy()
            random.shuffle(shuffled)
            
            deduped = dedup_bundles(shuffled)
            stable_reprs = [bundle_to_stable_repr(b) for b in deduped]
            results.append(stable_reprs)
        
        for i in range(1, 20):
            assert results[i] == results[0]
    
    def test_cache_key_determinism(self):
        """Same cache key inputs produce identical keys."""
        query = "test query"
        tool_kind = "WEB"
        env_mode = "dev"
        policy_caps = {"max_calls": 10, "timeout": 5000}
        request_flags = {"citations_required": True, "allow_cache": True}
        now_ms = 1000000
        
        keys = []
        for _ in range(20):
            key, _ = make_cache_key(query, tool_kind, env_mode, policy_caps, request_flags, now_ms)
            keys.append(key)
        
        for i in range(1, 20):
            assert keys[i] == keys[0]


class TestSourceIdComputation:
    """Test canonical source ID computation."""
    
    def test_source_id_deterministic(self):
        """Same structure produces same source ID."""
        sid1 = compute_canonical_source_id(
            tool="WEB",
            canonical_url="https://example.com/page",
            domain="example.com",
            title_length=10,
            snippet_count=2,
            snippet_lengths=(50, 60),
            metadata_keys=("author", "date"),
        )
        
        sid2 = compute_canonical_source_id(
            tool="WEB",
            canonical_url="https://example.com/page",
            domain="example.com",
            title_length=10,
            snippet_count=2,
            snippet_lengths=(50, 60),
            metadata_keys=("author", "date"),
        )
        
        assert sid1 == sid2
        assert len(sid1) == 12
    
    def test_source_id_different_structure(self):
        """Different structure produces different source ID."""
        sid1 = compute_canonical_source_id(
            tool="WEB",
            canonical_url="https://example.com/page",
            domain="example.com",
            title_length=10,
            snippet_count=2,
            snippet_lengths=(50, 60),
            metadata_keys=("author", "date"),
        )
        
        sid2 = compute_canonical_source_id(
            tool="WEB",
            canonical_url="https://example.com/page",
            domain="example.com",
            title_length=10,
            snippet_count=3,
            snippet_lengths=(50, 60, 70),
            metadata_keys=("author", "date"),
        )
        
        assert sid1 != sid2


class TestGates:
    """Test gate requirements."""
    
    def test_gate_same_inputs_same_ordered_bundles(self):
        """Gate: Same inputs -> same ordered bundles after dedup (20 replays)."""
        bundle1 = make_test_bundle("src1", "https://example.com/a", "example.com", "Title A", ["snippet1"])
        bundle2 = make_test_bundle("src2", "https://example.com/b", "example.com", "Title B", ["snippet2"])
        bundle3 = make_test_bundle("src3", "https://example.com/a?utm_source=test", "example.com", "Title A2", ["snippet3", "snippet4"])
        
        base_bundles = [bundle1, bundle2, bundle3]
        
        serialized_results = []
        for _ in range(20):
            shuffled = base_bundles.copy()
            random.shuffle(shuffled)
            
            deduped = dedup_bundles(shuffled)
            
            stable_repr = json.dumps([bundle_to_stable_repr(b) for b in deduped], sort_keys=True)
            serialized_results.append(stable_repr)
        
        for i in range(1, 20):
            assert serialized_results[i] == serialized_results[0]


if __name__ == "__main__":
    print("Running Phase 18 Step 6 Cache + Dedup Tests...")
    print()
    
    print("Test Group: Canonicalization")
    test_canon = TestCanonicalization()
    test_canon.test_query_canonicalization()
    print("✓ Query canonicalization")
    test_canon.test_query_empty_handling()
    print("✓ Query empty handling")
    test_canon.test_url_canonicalization_basic()
    print("✓ URL canonicalization basic")
    test_canon.test_url_tracking_params_removed()
    print("✓ URL tracking params removed")
    test_canon.test_url_query_params_sorted()
    print("✓ URL query params sorted")
    test_canon.test_url_default_ports_removed()
    print("✓ URL default ports removed")
    test_canon.test_url_fragment_removed()
    print("✓ URL fragment removed")
    test_canon.test_domain_extraction()
    print("✓ Domain extraction")
    
    print("\nTest Group: Cache Keys")
    test_keys = TestCacheKeys()
    test_keys.test_same_inputs_same_key()
    print("✓ Same inputs -> same key")
    test_keys.test_equivalent_whitespace_same_key()
    print("✓ Equivalent whitespace -> same key")
    test_keys.test_different_time_bucket_different_key()
    print("✓ Different time bucket -> different key")
    test_keys.test_policy_caps_difference_different_key()
    print("✓ Policy caps difference -> different key")
    test_keys.test_time_bucket_computation()
    print("✓ Time bucket computation")
    test_keys.test_default_bucket_sizes()
    print("✓ Default bucket sizes")
    
    print("\nTest Group: Cache Behavior")
    test_cache = TestCacheBehavior()
    test_cache.test_put_then_get()
    print("✓ Put then get")
    test_cache.test_get_miss()
    print("✓ Get miss")
    test_cache.test_eviction_deterministic()
    print("✓ Eviction deterministic (FIFO)")
    test_cache.test_clear()
    print("✓ Clear")
    
    print("\nTest Group: Dedup")
    test_dedup = TestDedup()
    test_dedup.test_duplicate_urls_collapse()
    print("✓ Duplicate URLs collapse")
    test_dedup.test_winner_selection_metadata()
    print("✓ Winner selection: metadata count")
    test_dedup.test_winner_selection_snippet_count()
    print("✓ Winner selection: snippet count")
    test_dedup.test_stable_ordering()
    print("✓ Stable ordering")
    test_dedup.test_dedup_idempotent()
    print("✓ Dedup idempotent")
    test_dedup.test_empty_bundles()
    print("✓ Empty bundles")
    
    print("\nTest Group: Determinism")
    test_det = TestDeterminism()
    test_det.test_dedup_replay_identical()
    print("✓ Dedup replay 20 times -> identical results")
    test_det.test_cache_key_determinism()
    print("✓ Cache key determinism")
    
    print("\nTest Group: Source ID Computation")
    test_sid = TestSourceIdComputation()
    test_sid.test_source_id_deterministic()
    print("✓ Source ID deterministic")
    test_sid.test_source_id_different_structure()
    print("✓ Source ID different for different structure")
    
    print("\nTest Group: Gates")
    test_gates = TestGates()
    test_gates.test_gate_same_inputs_same_ordered_bundles()
    print("✓ Gate: Same inputs -> same ordered bundles (20 replays)")
    
    print("\n" + "="*60)
    print("ALL CACHE + DEDUP TESTS PASSED ✓")
    print("="*60)
