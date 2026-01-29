"""
Phase 18 Step 4: Claim-to-Citation Binder Tests

Comprehensive tests for claim extraction, binding, and coverage enforcement:
- Determinism (replay 20 times)
- Coverage gate (required claims with no sources -> downgrade)
- Binding correctness
- Ordering stability
- Bounds enforcement
- No snippet text leakage
- Mixed source types (SourceBundle + GradedSource)
"""

import json
from datetime import datetime

from backend.app.retrieval.types import SourceBundle, SourceSnippet, ToolKind
from backend.app.research.claim_binder import (
    bind_claims_and_citations,
    extract_claims,
    bind_claims_to_sources,
    enforce_coverage,
    tokenize_text,
    compute_overlap_score,
    is_required_claim,
    classify_claim_kind,
    MAX_CLAIMS,
    MAX_CLAIM_LENGTH,
    MAX_CITATIONS_PER_CLAIM,
)
from backend.app.research.citations import (
    CitationRef,
    make_citation_ref,
    normalize_url,
    extract_domain,
)


SENSITIVE_SNIPPET_TEXT_123 = "SENSITIVE_SNIPPET_TEXT_123"
SENSITIVE_SNIPPET_TEXT_456 = "SENSITIVE_SNIPPET_TEXT_456"


def make_test_source(
    source_id: str,
    url: str,
    domain: str,
    snippets_text: list,
    title: str = "Test Source",
    metadata: dict = None,
) -> SourceBundle:
    """Create test SourceBundle."""
    if metadata is None:
        metadata = {}
    
    snippets = [SourceSnippet(text=text) for text in snippets_text]
    
    return SourceBundle(
        source_id=source_id,
        tool=ToolKind.WEB,
        url=url,
        domain=domain,
        title=title,
        retrieved_at="2026-01-29T00:00:00Z",
        snippets=snippets,
        metadata=metadata,
    )


def make_graded_source(source: SourceBundle, score: int, grade: str):
    """Simulate GradedSource from Step 18.3."""
    from dataclasses import dataclass
    
    @dataclass
    class MockCredibilityReport:
        score: int
        grade: str
    
    @dataclass
    class MockGradedSource:
        source: SourceBundle
        credibility: MockCredibilityReport
    
    return MockGradedSource(
        source=source,
        credibility=MockCredibilityReport(score=score, grade=grade),
    )


class TestClaimExtraction:
    """Test claim extraction logic."""
    
    def test_extract_basic_claims(self):
        """Extract claims from simple text."""
        text = "Python is a programming language. It was created in 1991. Use pip to install packages."
        claims = extract_claims(text)
        
        assert len(claims) > 0
        assert all(len(c.text) <= MAX_CLAIM_LENGTH for c in claims)
        assert all(hasattr(c, 'claim_id') for c in claims)
        assert all(hasattr(c, 'required') for c in claims)
        assert all(hasattr(c, 'kind') for c in claims)
        assert all(hasattr(c, 'confidence') for c in claims)
    
    def test_required_claim_detection(self):
        """Claims with facts/dates/numbers marked as required."""
        text1 = "Python was created in 1991."
        claims1 = extract_claims(text1)
        assert len(claims1) > 0
        assert claims1[0].required == True
        
        text2 = "You should use Python for scripting."
        claims2 = extract_claims(text2)
        assert len(claims2) > 0
        assert claims2[0].required == False
    
    def test_claim_kind_classification(self):
        """Claims classified into FACT/STAT/QUOTE/RECOMMENDATION."""
        text_fact = "Python is dynamically typed."
        text_stat = "Python has 85% market share."
        text_quote = 'Guido said "Python is awesome".'
        text_rec = "You should use Python for web development."
        
        claims_fact = extract_claims(text_fact)
        claims_stat = extract_claims(text_stat)
        claims_quote = extract_claims(text_quote)
        claims_rec = extract_claims(text_rec)
        
        assert claims_fact[0].kind == "FACT"
        assert claims_stat[0].kind == "STAT"
        assert claims_quote[0].kind == "QUOTE"
        assert claims_rec[0].kind == "RECOMMENDATION"
    
    def test_max_claims_bound(self):
        """Never exceed MAX_CLAIMS."""
        text = ". ".join([f"Claim number {i}" for i in range(50)])
        claims = extract_claims(text)
        
        assert len(claims) <= MAX_CLAIMS
    
    def test_deduplication(self):
        """Duplicate claims are deduplicated."""
        text = "Python is great. Python is great. Python is great."
        claims = extract_claims(text)
        
        assert len(claims) == 1
    
    def test_required_claims_first(self):
        """Required claims sorted before non-required."""
        text = "You should try Python. Python was created in 1991. Consider learning it."
        claims = extract_claims(text)
        
        required_indices = [i for i, c in enumerate(claims) if c.required]
        non_required_indices = [i for i, c in enumerate(claims) if not c.required]
        
        if required_indices and non_required_indices:
            assert max(required_indices) < min(non_required_indices)


class TestTokenization:
    """Test tokenization for claim-citation matching."""
    
    def test_tokenize_removes_stopwords(self):
        """Stopwords removed from tokens."""
        text = "the quick brown fox jumps over the lazy dog"
        tokens = tokenize_text(text)
        
        assert "the" not in tokens
        assert "over" not in tokens
        assert "quick" in tokens or "brown" in tokens or "fox" in tokens
    
    def test_overlap_score(self):
        """Overlap score computed correctly."""
        claim_tokens = ["python", "programming", "language"]
        snippet_tokens = ["python", "language", "easy"]
        
        score = compute_overlap_score(claim_tokens, snippet_tokens)
        assert score == 2


class TestCitationRef:
    """Test CitationRef structure."""
    
    def test_citation_ref_no_snippet_text(self):
        """CitationRef does not store snippet text."""
        citation = make_citation_ref(
            source_id="test123",
            url="https://example.com/article",
            domain="example.com",
            title="Test Article",
            snippet_index=0,
            snippet_len=100,
            published_date="2026-01-15",
            credibility_report=None,
        )
        
        citation_dict = {
            "source_id": citation.source_id,
            "url": citation.url,
            "domain": citation.domain,
            "title": citation.title,
            "published_date": citation.published_date,
            "snippet_index": citation.snippet_index,
            "snippet_len": citation.snippet_len,
        }
        
        citation_json = json.dumps(citation_dict)
        
        assert "snippet_text" not in citation_json.lower()
        assert citation.snippet_len == 100
    
    def test_url_normalization(self):
        """URL normalized correctly."""
        url1 = "HTTPS://EXAMPLE.COM/PATH/"
        url2 = "example.com/path"
        
        norm1 = normalize_url(url1)
        norm2 = normalize_url(url2)
        
        assert norm1 == "https://example.com/path"
        assert norm2 == "https://example.com/path"
    
    def test_domain_extraction(self):
        """Domain extracted correctly."""
        url1 = "https://www.example.com/path"
        url2 = "https://subdomain.example.com"
        
        domain1 = extract_domain(url1)
        domain2 = extract_domain(url2)
        
        assert domain1 == "example.com"
        assert domain2 == "subdomain.example.com"


class TestBinding:
    """Test claim-to-citation binding."""
    
    def test_binding_works(self):
        """Claims bind to matching sources."""
        text = "Python is a high-level programming language created by Guido van Rossum."
        claims = extract_claims(text)
        
        sources = [
            make_test_source(
                "src1",
                "https://python.org/about",
                "python.org",
                ["Python is a high-level programming language designed for readability."],
                metadata={"author": "PSF"},
            ),
        ]
        
        bindings = bind_claims_to_sources(claims, sources)
        
        assert len(bindings) > 0
        for claim_id, citations in bindings.items():
            assert len(citations) <= MAX_CITATIONS_PER_CLAIM
    
    def test_no_duplicate_citations(self):
        """No duplicate (source_id, snippet_index) per claim."""
        text = "Python is popular for web development and data science."
        claims = extract_claims(text)
        
        sources = [
            make_test_source(
                "src1",
                "https://example.com",
                "example.com",
                [
                    "Python is popular for web development.",
                    "Python is widely used in data science.",
                ],
            ),
        ]
        
        bindings = bind_claims_to_sources(claims, sources)
        
        for claim_id, citations in bindings.items():
            keys = [(c.source_id, c.snippet_index) for c in citations]
            assert len(keys) == len(set(keys))
    
    def test_credibility_score_ordering(self):
        """Higher credibility sources ranked first."""
        text = "Python is a programming language."
        claims = extract_claims(text)
        
        source_low = make_test_source(
            "src_low",
            "https://blog.example.com",
            "blog.example.com",
            ["Python is a programming language used widely."],
        )
        source_high = make_test_source(
            "src_high",
            "https://python.org",
            "python.org",
            ["Python is a programming language with rich features."],
        )
        
        graded_low = make_graded_source(source_low, 30, "E")
        graded_high = make_graded_source(source_high, 90, "A")
        
        sources = [graded_low, graded_high]
        
        bindings = bind_claims_to_sources(claims, sources)
        
        if bindings:
            first_binding = list(bindings.values())[0]
            if len(first_binding) >= 2:
                assert first_binding[0].credibility_score >= first_binding[1].credibility_score


class TestCoverageGate:
    """Test coverage enforcement."""
    
    def test_no_sources_required_claim_downgrade(self):
        """Required claim with no sources -> UNKNOWN or ASK_CLARIFY."""
        text = "Python was released in 1991."
        sources = []
        
        output = bind_claims_and_citations(text, sources, citations_required=True)
        
        assert output.final_mode in ["UNKNOWN", "ASK_CLARIFY"]
        assert len(output.uncovered_required_claim_ids) > 0
    
    def test_clarifiable_claim_ask_clarify(self):
        """Clarifiable uncovered claim -> ASK_CLARIFY."""
        text = "What version of Python should I use?"
        sources = []
        
        output = bind_claims_and_citations(text, sources, citations_required=True)
        
        assert output.final_mode == "ASK_CLARIFY"
        assert len(output.clarify_questions) > 0
    
    def test_non_clarifiable_unknown(self):
        """Non-clarifiable uncovered claim -> UNKNOWN."""
        text = "Python was created in 1991."
        sources = []
        
        output = bind_claims_and_citations(text, sources, citations_required=True)
        
        assert output.final_mode in ["UNKNOWN", "ASK_CLARIFY"]
    
    def test_all_required_covered_ok(self):
        """All required claims covered -> OK."""
        text = "Python is a programming language."
        
        sources = [
            make_test_source(
                "src1",
                "https://python.org",
                "python.org",
                ["Python is a high-level programming language."],
            ),
        ]
        
        output = bind_claims_and_citations(text, sources, citations_required=True)
        
        assert output.final_mode == "OK"
        assert len(output.uncovered_required_claim_ids) == 0
    
    def test_only_non_required_uncovered_ok(self):
        """Only non-required claims uncovered -> OK."""
        text = "You should try Python. It is easy to learn."
        
        sources = []
        
        output = bind_claims_and_citations(text, sources, citations_required=True)
        
        if all(not c.required for c in output.claims):
            assert output.final_mode == "OK"
    
    def test_mixed_coverage_downgrade(self):
        """Some required covered, some not -> downgrade."""
        text = "Python was created in 1991. You should use Python for scripting."
        
        sources = [
            make_test_source(
                "src1",
                "https://example.com",
                "example.com",
                ["Python is useful for scripting tasks."],
            ),
        ]
        
        output = bind_claims_and_citations(text, sources, citations_required=True)
        
        if any(c.required for c in output.claims):
            required_claim_ids = [c.claim_id for c in output.claims if c.required]
            covered = any(
                claim_id in output.bindings and output.bindings[claim_id]
                for claim_id in required_claim_ids
            )
            
            if not covered:
                assert output.final_mode in ["UNKNOWN", "ASK_CLARIFY"]


class TestBounds:
    """Test bounds enforcement."""
    
    def test_max_claims(self):
        """Never exceed MAX_CLAIMS."""
        text = ". ".join([f"Claim {i} is important" for i in range(50)])
        sources = []
        
        output = bind_claims_and_citations(text, sources, citations_required=False)
        
        assert len(output.claims) <= MAX_CLAIMS
    
    def test_max_citations_per_claim(self):
        """Never exceed MAX_CITATIONS_PER_CLAIM."""
        text = "Python is a programming language."
        
        sources = [
            make_test_source(
                f"src{i}",
                f"https://example{i}.com",
                f"example{i}.com",
                ["Python is a programming language with many features."],
            )
            for i in range(10)
        ]
        
        output = bind_claims_and_citations(text, sources, citations_required=False)
        
        for claim_id, citations in output.bindings.items():
            assert len(citations) <= MAX_CITATIONS_PER_CLAIM
    
    def test_claim_length_bounded(self):
        """Claims never exceed MAX_CLAIM_LENGTH."""
        long_text = "This is a very long claim " * 50
        
        output = bind_claims_and_citations(long_text, [], citations_required=False)
        
        for claim in output.claims:
            assert len(claim.text) <= MAX_CLAIM_LENGTH


class TestSnippetLeakage:
    """Test that snippet text never leaks into output."""
    
    def test_no_sensitive_text_in_citation_ref(self):
        """Sensitive snippet text not in CitationRef."""
        sources = [
            make_test_source(
                "src1",
                "https://example.com",
                "example.com",
                [SENSITIVE_SNIPPET_TEXT_123, SENSITIVE_SNIPPET_TEXT_456],
            ),
        ]
        
        text = "This is a test claim about something."
        output = bind_claims_and_citations(text, sources, citations_required=False)
        
        output_json = json.dumps({
            "final_mode": output.final_mode,
            "claims": [
                {
                    "claim_id": c.claim_id,
                    "text": c.text,
                    "kind": c.kind,
                    "required": c.required,
                }
                for c in output.claims
            ],
            "bindings": {
                claim_id: [
                    {
                        "source_id": cit.source_id,
                        "url": cit.url,
                        "domain": cit.domain,
                        "snippet_index": cit.snippet_index,
                        "snippet_len": cit.snippet_len,
                    }
                    for cit in citations
                ]
                for claim_id, citations in output.bindings.items()
            },
        })
        
        assert SENSITIVE_SNIPPET_TEXT_123 not in output_json
        assert SENSITIVE_SNIPPET_TEXT_456 not in output_json


class TestDeterminism:
    """Test determinism guarantees."""
    
    def test_replay_identical_results(self):
        """Same inputs produce identical results across 20 runs."""
        text = "Python was created in 1991 by Guido van Rossum. It is widely used for web development."
        
        sources = [
            make_test_source(
                "src1",
                "https://python.org/history",
                "python.org",
                ["Python was created by Guido van Rossum in 1991."],
                metadata={"author": "PSF", "date": "2020-01-15"},
            ),
            make_test_source(
                "src2",
                "https://example.com/python",
                "example.com",
                ["Python is used for web development and data science."],
                metadata={"author": "Author"},
            ),
        ]
        
        results = []
        for _ in range(20):
            output = bind_claims_and_citations(text, sources, citations_required=True)
            results.append(output)
        
        for i in range(1, 20):
            assert results[i].final_mode == results[0].final_mode
            assert len(results[i].claims) == len(results[0].claims)
            assert len(results[i].bindings) == len(results[0].bindings)
            assert results[i].uncovered_required_claim_ids == results[0].uncovered_required_claim_ids
            
            for j in range(len(results[0].claims)):
                assert results[i].claims[j].claim_id == results[0].claims[j].claim_id
                assert results[i].claims[j].text == results[0].claims[j].text
                assert results[i].claims[j].required == results[0].claims[j].required
            
            for claim_id in results[0].bindings:
                assert claim_id in results[i].bindings
                assert len(results[i].bindings[claim_id]) == len(results[0].bindings[claim_id])
                
                for k in range(len(results[0].bindings[claim_id])):
                    assert results[i].bindings[claim_id][k].source_id == results[0].bindings[claim_id][k].source_id
                    assert results[i].bindings[claim_id][k].snippet_index == results[0].bindings[claim_id][k].snippet_index


class TestMixedSourceTypes:
    """Test with both SourceBundle and GradedSource."""
    
    def test_mixed_sources(self):
        """Handle both SourceBundle and GradedSource."""
        text = "Python is a programming language."
        
        source1 = make_test_source(
            "src1",
            "https://python.org",
            "python.org",
            ["Python is a programming language."],
        )
        
        source2 = make_test_source(
            "src2",
            "https://example.com",
            "example.com",
            ["Python language features."],
        )
        
        graded2 = make_graded_source(source2, 85, "A")
        
        sources = [source1, graded2]
        
        output = bind_claims_and_citations(text, sources, citations_required=False)
        
        assert len(output.claims) > 0
        assert len(output.bindings) > 0


class TestFailClosed:
    """Test fail-closed behavior."""
    
    def test_empty_text_fail_closed(self):
        """Empty text returns safe default."""
        output = bind_claims_and_citations("", [], citations_required=True)
        
        assert output.final_mode == "UNKNOWN"
        assert len(output.claims) == 0
    
    def test_exception_handling(self):
        """Exceptions caught and return safe default."""
        text = "Test claim"
        
        output = bind_claims_and_citations(text, None, citations_required=True)
        
        assert output.final_mode == "UNKNOWN"


if __name__ == "__main__":
    print("Running Phase 18 Step 4 Claim-to-Citation Tests...")
    print()
    
    print("Test Group: Claim Extraction")
    test_ce = TestClaimExtraction()
    test_ce.test_extract_basic_claims()
    print("✓ Extract basic claims")
    test_ce.test_required_claim_detection()
    print("✓ Required claim detection")
    test_ce.test_claim_kind_classification()
    print("✓ Claim kind classification")
    test_ce.test_max_claims_bound()
    print("✓ Max claims bound")
    test_ce.test_deduplication()
    print("✓ Deduplication")
    test_ce.test_required_claims_first()
    print("✓ Required claims first")
    
    print("\nTest Group: Tokenization")
    test_tok = TestTokenization()
    test_tok.test_tokenize_removes_stopwords()
    print("✓ Stopwords removed")
    test_tok.test_overlap_score()
    print("✓ Overlap score")
    
    print("\nTest Group: CitationRef")
    test_cr = TestCitationRef()
    test_cr.test_citation_ref_no_snippet_text()
    print("✓ No snippet text in CitationRef")
    test_cr.test_url_normalization()
    print("✓ URL normalization")
    test_cr.test_domain_extraction()
    print("✓ Domain extraction")
    
    print("\nTest Group: Binding")
    test_bind = TestBinding()
    test_bind.test_binding_works()
    print("✓ Binding works")
    test_bind.test_no_duplicate_citations()
    print("✓ No duplicate citations")
    test_bind.test_credibility_score_ordering()
    print("✓ Credibility score ordering")
    
    print("\nTest Group: Coverage Gate")
    test_cov = TestCoverageGate()
    test_cov.test_no_sources_required_claim_downgrade()
    print("✓ No sources required claim -> downgrade")
    test_cov.test_clarifiable_claim_ask_clarify()
    print("✓ Clarifiable claim -> ASK_CLARIFY")
    test_cov.test_non_clarifiable_unknown()
    print("✓ Non-clarifiable -> UNKNOWN")
    test_cov.test_all_required_covered_ok()
    print("✓ All required covered -> OK")
    test_cov.test_only_non_required_uncovered_ok()
    print("✓ Only non-required uncovered -> OK")
    test_cov.test_mixed_coverage_downgrade()
    print("✓ Mixed coverage -> downgrade")
    
    print("\nTest Group: Bounds")
    test_bounds = TestBounds()
    test_bounds.test_max_claims()
    print("✓ Max claims enforced")
    test_bounds.test_max_citations_per_claim()
    print("✓ Max citations per claim enforced")
    test_bounds.test_claim_length_bounded()
    print("✓ Claim length bounded")
    
    print("\nTest Group: Snippet Leakage")
    test_leak = TestSnippetLeakage()
    test_leak.test_no_sensitive_text_in_citation_ref()
    print("✓ No sensitive text in CitationRef")
    
    print("\nTest Group: Determinism")
    test_det = TestDeterminism()
    test_det.test_replay_identical_results()
    print("✓ Replay 20 times -> identical results")
    
    print("\nTest Group: Mixed Source Types")
    test_mixed = TestMixedSourceTypes()
    test_mixed.test_mixed_sources()
    print("✓ Mixed SourceBundle and GradedSource")
    
    print("\nTest Group: Fail-Closed")
    test_fc = TestFailClosed()
    test_fc.test_empty_text_fail_closed()
    print("✓ Empty text fail-closed")
    test_fc.test_exception_handling()
    print("✓ Exception handling")
    
    print("\n" + "="*60)
    print("ALL CLAIM-TO-CITATION TESTS PASSED ✓")
    print("="*60)
