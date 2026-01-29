"""
Phase 18 Step 1: Retrieval Adapter Tests

Comprehensive tests for retrieval adapter boundary guarantees:
- Determinism
- Canonicalization
- Output schema
- Fail-closed behavior
- Stable ordering
- Metadata sanitation
- Source ID stability
"""

import copy
from typing import List, Dict, Any

from backend.app.retrieval.adapter import (
    retrieve,
    RetrievalRequest,
    canonicalize_query,
    canonicalize_url,
    extract_domain,
    compute_source_id,
    validate_metadata,
    normalize_raw_source,
    stable_sort_sources,
    run_tool_stub,
)
from backend.app.retrieval.types import (
    ToolKind,
    EnvMode,
    PolicyCaps,
    RequestFlags,
    SourceSnippet,
    SourceBundle,
)


def make_test_caps(max_results=5):
    """Create test PolicyCaps."""
    return PolicyCaps(
        max_results=max_results,
        per_tool_timeout_ms=5000,
        total_timeout_ms=15000,
    )


def make_test_flags():
    """Create test RequestFlags."""
    return RequestFlags(
        citations_required=True,
        allow_cache=False,
    )


class TestCanonicalization:
    """Test query and URL canonicalization."""
    
    def test_query_canonicalization_whitespace(self):
        """Whitespace differences produce identical canonical query."""
        q1 = "  hello   world  "
        q2 = "hello world"
        q3 = "hello\n\tworld"
        
        c1 = canonicalize_query(q1)
        c2 = canonicalize_query(q2)
        c3 = canonicalize_query(q3)
        
        assert c1 == c2 == c3 == "hello world"
    
    def test_url_canonicalization(self):
        """URL canonicalization lower-cases scheme and host."""
        u1 = "HTTPS://EXAMPLE.COM/path"
        u2 = "https://example.com/path"
        
        c1 = canonicalize_url(u1)
        c2 = canonicalize_url(u2)
        
        assert c1 == c2 == "https://example.com/path"
    
    def test_domain_extraction(self):
        """Domain extraction is robust."""
        assert extract_domain("https://example.com/path") == "example.com"
        assert extract_domain("http://SUB.EXAMPLE.COM") == "sub.example.com"
        assert extract_domain("invalid") == "unknown"


class TestSourceIDStability:
    """Test source_id determinism."""
    
    def test_same_structure_same_id(self):
        """Same structure produces same source_id."""
        snippets = [SourceSnippet(text="test snippet")]
        metadata = {"key": "value"}
        
        id1 = compute_source_id(ToolKind.WEB, "https://example.com", "example.com", "Title", snippets, metadata)
        id2 = compute_source_id(ToolKind.WEB, "https://example.com", "example.com", "Title", snippets, metadata)
        
        assert id1 == id2
    
    def test_different_content_same_length_same_id(self):
        """Different snippet content but same length produces same ID (structure-only hashing)."""
        snippets1 = [SourceSnippet(text="test snippet")]
        snippets2 = [SourceSnippet(text="diff snippet")]
        metadata = {}
        
        id1 = compute_source_id(ToolKind.WEB, "https://example.com", "example.com", None, snippets1, metadata)
        id2 = compute_source_id(ToolKind.WEB, "https://example.com", "example.com", None, snippets2, metadata)
        
        assert id1 == id2
    
    def test_different_length_different_id(self):
        """Different snippet length produces different ID."""
        snippets1 = [SourceSnippet(text="short")]
        snippets2 = [SourceSnippet(text="longer snippet")]
        metadata = {}
        
        id1 = compute_source_id(ToolKind.WEB, "https://example.com", "example.com", None, snippets1, metadata)
        id2 = compute_source_id(ToolKind.WEB, "https://example.com", "example.com", None, snippets2, metadata)
        
        assert id1 != id2


class TestMetadataValidation:
    """Test metadata validation."""
    
    def test_valid_metadata(self):
        """Valid metadata with primitives passes."""
        metadata = {
            "str_key": "value",
            "int_key": 42,
            "bool_key": True,
            "float_key": 3.14,
        }
        assert validate_metadata(metadata) == True
    
    def test_invalid_metadata_non_primitive(self):
        """Metadata with non-primitives fails."""
        metadata = {"list_key": [1, 2, 3]}
        assert validate_metadata(metadata) == False
        
        metadata = {"dict_key": {"nested": "value"}}
        assert validate_metadata(metadata) == False
    
    def test_invalid_metadata_too_many_keys(self):
        """Metadata with too many keys fails."""
        metadata = {f"key{i}": i for i in range(20)}
        assert validate_metadata(metadata) == False


class TestNormalization:
    """Test raw source normalization."""
    
    def test_normalize_valid_source(self):
        """Valid raw source normalizes correctly."""
        raw = {
            "url": "https://example.com/page",
            "title": "Example Page",
            "snippets": ["snippet 1", "snippet 2"],
            "metadata": {"score": 0.9},
        }
        
        source = normalize_raw_source(ToolKind.WEB, raw, "2026-01-29T00:00:00Z")
        
        assert source is not None
        assert source.url == "https://example.com/page"
        assert source.domain == "example.com"
        assert source.title == "Example Page"
        assert len(source.snippets) == 2
        assert source.snippets[0].text == "snippet 1"
        assert source.metadata == {"score": 0.9}
    
    def test_normalize_missing_url(self):
        """Missing URL returns None."""
        raw = {"title": "No URL", "snippets": ["text"]}
        source = normalize_raw_source(ToolKind.WEB, raw, "2026-01-29T00:00:00Z")
        assert source is None
    
    def test_normalize_empty_snippets(self):
        """Empty snippets returns None."""
        raw = {"url": "https://example.com", "snippets": []}
        source = normalize_raw_source(ToolKind.WEB, raw, "2026-01-29T00:00:00Z")
        assert source is None
    
    def test_normalize_bounds_enforcement(self):
        """Bounds are enforced during normalization."""
        long_title = "x" * 300
        long_snippet = "y" * 600
        
        raw = {
            "url": "https://example.com",
            "title": long_title,
            "snippets": [long_snippet],
        }
        
        source = normalize_raw_source(ToolKind.WEB, raw, "2026-01-29T00:00:00Z")
        
        assert source is not None
        assert len(source.title) == 200
        assert len(source.snippets[0].text) == 500
    
    def test_normalize_invalid_metadata(self):
        """Invalid metadata is replaced with empty dict."""
        raw = {
            "url": "https://example.com",
            "snippets": ["text"],
            "metadata": {"nested": {"invalid": "structure"}},
        }
        
        source = normalize_raw_source(ToolKind.WEB, raw, "2026-01-29T00:00:00Z")
        
        assert source is not None
        assert source.metadata == {}


class TestStableOrdering:
    """Test stable sorting of sources."""
    
    def test_stable_sort_by_tool_domain_url(self):
        """Sources sorted by tool, domain, url, source_id."""
        s1 = SourceBundle(
            source_id="aaa",
            tool=ToolKind.WEB,
            url="https://b.com/1",
            domain="b.com",
            title=None,
            retrieved_at="2026-01-29T00:00:00Z",
            snippets=[SourceSnippet(text="text")],
            metadata={},
        )
        
        s2 = SourceBundle(
            source_id="bbb",
            tool=ToolKind.WEB,
            url="https://a.com/1",
            domain="a.com",
            title=None,
            retrieved_at="2026-01-29T00:00:00Z",
            snippets=[SourceSnippet(text="text")],
            metadata={},
        )
        
        s3 = SourceBundle(
            source_id="ccc",
            tool=ToolKind.DOCS,
            url="https://c.com/1",
            domain="c.com",
            title=None,
            retrieved_at="2026-01-29T00:00:00Z",
            snippets=[SourceSnippet(text="text")],
            metadata={},
        )
        
        unsorted = [s1, s3, s2]
        sorted_sources = stable_sort_sources(unsorted)
        
        assert sorted_sources[0] == s3
        assert sorted_sources[1] == s2
        assert sorted_sources[2] == s1


class TestRetrieveDeterminism:
    """Test retrieve() determinism."""
    
    def test_determinism_with_stubbed_tool(self):
        """Same request with same stubbed outputs produces identical results."""
        import backend.app.retrieval.adapter as adapter_module
        
        original_stub = adapter_module.run_tool_stub
        
        def mock_stub(tool, query, caps):
            return [
                {
                    "url": "https://example.com/1",
                    "title": "Result 1",
                    "snippets": ["snippet 1"],
                    "metadata": {"score": 0.9},
                },
                {
                    "url": "https://example.com/2",
                    "title": "Result 2",
                    "snippets": ["snippet 2"],
                    "metadata": {"score": 0.8},
                },
            ]
        
        adapter_module.run_tool_stub = mock_stub
        
        try:
            req = RetrievalRequest(
                query="test query",
                policy_caps=make_test_caps(),
                allowed_tools=[ToolKind.WEB],
                env_mode=EnvMode.DEV,
                request_flags=make_test_flags(),
            )
            
            result1 = retrieve(req)
            result2 = retrieve(req)
            
            assert len(result1) == len(result2)
            for i in range(len(result1)):
                assert result1[i].source_id == result2[i].source_id
                assert result1[i].url == result2[i].url
                assert result1[i].domain == result2[i].domain
        finally:
            adapter_module.run_tool_stub = original_stub


class TestFailClosed:
    """Test fail-closed behavior."""
    
    def test_empty_query_returns_empty(self):
        """Empty query returns []."""
        req = RetrievalRequest(
            query="",
            policy_caps=make_test_caps(),
            allowed_tools=[ToolKind.WEB],
            env_mode=EnvMode.DEV,
            request_flags=make_test_flags(),
        )
        
        result = retrieve(req)
        assert result == []
    
    def test_no_allowed_tools_returns_empty(self):
        """No allowed tools returns []."""
        req = RetrievalRequest(
            query="test",
            policy_caps=make_test_caps(),
            allowed_tools=[],
            env_mode=EnvMode.DEV,
            request_flags=make_test_flags(),
        )
        
        result = retrieve(req)
        assert result == []
    
    def test_invalid_max_results_returns_empty(self):
        """Invalid max_results returns []."""
        caps = PolicyCaps(
            max_results=0,
            per_tool_timeout_ms=5000,
            total_timeout_ms=15000,
        )
        
        req = RetrievalRequest(
            query="test",
            policy_caps=caps,
            allowed_tools=[ToolKind.WEB],
            env_mode=EnvMode.DEV,
            request_flags=make_test_flags(),
        )
        
        result = retrieve(req)
        assert result == []
    
    def test_tool_stub_not_implemented_returns_empty(self):
        """Tool stub raising NotImplementedError returns []."""
        req = RetrievalRequest(
            query="test",
            policy_caps=make_test_caps(),
            allowed_tools=[ToolKind.WEB],
            env_mode=EnvMode.DEV,
            request_flags=make_test_flags(),
        )
        
        result = retrieve(req)
        assert result == []


class TestOutputSchema:
    """Test output schema guarantees."""
    
    def test_output_is_list_of_source_bundles(self):
        """Output is always List[SourceBundle]."""
        import backend.app.retrieval.adapter as adapter_module
        
        original_stub = adapter_module.run_tool_stub
        
        def mock_stub(tool, query, caps):
            return [
                {
                    "url": "https://example.com",
                    "snippets": ["text"],
                },
            ]
        
        adapter_module.run_tool_stub = mock_stub
        
        try:
            req = RetrievalRequest(
                query="test",
                policy_caps=make_test_caps(),
                allowed_tools=[ToolKind.WEB],
                env_mode=EnvMode.DEV,
                request_flags=make_test_flags(),
            )
            
            result = retrieve(req)
            
            assert isinstance(result, list)
            for item in result:
                assert isinstance(item, SourceBundle)
                assert isinstance(item.source_id, str)
                assert isinstance(item.tool, ToolKind)
                assert isinstance(item.url, str)
                assert isinstance(item.domain, str)
                assert isinstance(item.retrieved_at, str)
                assert isinstance(item.snippets, list)
                assert isinstance(item.metadata, dict)
        finally:
            adapter_module.run_tool_stub = original_stub


class TestBoundsEnforcement:
    """Test bounds enforcement."""
    
    def test_max_results_enforced(self):
        """max_results cap is enforced."""
        import backend.app.retrieval.adapter as adapter_module
        
        original_stub = adapter_module.run_tool_stub
        
        def mock_stub(tool, query, caps):
            return [
                {"url": f"https://example.com/{i}", "snippets": [f"snippet {i}"]}
                for i in range(20)
            ]
        
        adapter_module.run_tool_stub = mock_stub
        
        try:
            req = RetrievalRequest(
                query="test",
                policy_caps=make_test_caps(max_results=3),
                allowed_tools=[ToolKind.WEB],
                env_mode=EnvMode.DEV,
                request_flags=make_test_flags(),
            )
            
            result = retrieve(req)
            
            assert len(result) <= 3
        finally:
            adapter_module.run_tool_stub = original_stub


if __name__ == "__main__":
    print("Running Phase 18 Step 1 Retrieval Adapter Tests...")
    print()
    
    print("Test Group: Canonicalization")
    test_canon = TestCanonicalization()
    test_canon.test_query_canonicalization_whitespace()
    print("✓ Query canonicalization whitespace")
    test_canon.test_url_canonicalization()
    print("✓ URL canonicalization")
    test_canon.test_domain_extraction()
    print("✓ Domain extraction")
    
    print("\nTest Group: Source ID Stability")
    test_id = TestSourceIDStability()
    test_id.test_same_structure_same_id()
    print("✓ Same structure -> same ID")
    test_id.test_different_content_same_length_same_id()
    print("✓ Different content same length -> same ID (structure-only)")
    test_id.test_different_length_different_id()
    print("✓ Different length -> different ID")
    
    print("\nTest Group: Metadata Validation")
    test_meta = TestMetadataValidation()
    test_meta.test_valid_metadata()
    print("✓ Valid metadata passes")
    test_meta.test_invalid_metadata_non_primitive()
    print("✓ Non-primitive metadata fails")
    test_meta.test_invalid_metadata_too_many_keys()
    print("✓ Too many keys fails")
    
    print("\nTest Group: Normalization")
    test_norm = TestNormalization()
    test_norm.test_normalize_valid_source()
    print("✓ Valid source normalizes")
    test_norm.test_normalize_missing_url()
    print("✓ Missing URL returns None")
    test_norm.test_normalize_empty_snippets()
    print("✓ Empty snippets returns None")
    test_norm.test_normalize_bounds_enforcement()
    print("✓ Bounds enforced")
    test_norm.test_normalize_invalid_metadata()
    print("✓ Invalid metadata replaced")
    
    print("\nTest Group: Stable Ordering")
    test_sort = TestStableOrdering()
    test_sort.test_stable_sort_by_tool_domain_url()
    print("✓ Stable sort by tool/domain/url/id")
    
    print("\nTest Group: Retrieve Determinism")
    test_det = TestRetrieveDeterminism()
    test_det.test_determinism_with_stubbed_tool()
    print("✓ Same request -> identical results")
    
    print("\nTest Group: Fail-Closed")
    test_fail = TestFailClosed()
    test_fail.test_empty_query_returns_empty()
    print("✓ Empty query -> []")
    test_fail.test_no_allowed_tools_returns_empty()
    print("✓ No allowed tools -> []")
    test_fail.test_invalid_max_results_returns_empty()
    print("✓ Invalid max_results -> []")
    test_fail.test_tool_stub_not_implemented_returns_empty()
    print("✓ NotImplementedError -> []")
    
    print("\nTest Group: Output Schema")
    test_schema = TestOutputSchema()
    test_schema.test_output_is_list_of_source_bundles()
    print("✓ Output is List[SourceBundle]")
    
    print("\nTest Group: Bounds Enforcement")
    test_bounds = TestBoundsEnforcement()
    test_bounds.test_max_results_enforced()
    print("✓ max_results cap enforced")
    
    print("\n" + "="*60)
    print("ALL RETRIEVAL ADAPTER TESTS PASSED ✓")
    print("="*60)
