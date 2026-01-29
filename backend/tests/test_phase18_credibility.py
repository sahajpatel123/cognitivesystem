"""
Phase 18 Step 3: Source Credibility Grader Tests

Comprehensive tests for deterministic, rule-based credibility scoring:
- Determinism (replay 20 times)
- Domain classification
- Freshness bucketing
- Author/date presence
- Corroboration across distinct domains
- Grade band mapping
- Stable ordering
- Fail-closed behavior
"""

from datetime import datetime

from backend.app.retrieval.types import SourceBundle, SourceSnippet, ToolKind
from backend.app.research.credibility import (
    grade_sources,
    classify_domain,
    parse_date,
    extract_date_from_metadata,
    compute_age_days,
    classify_freshness,
    has_author_field,
    normalize_claim_text,
    extract_claim_tokens,
    compute_claim_key,
    assign_grade_band,
    DOMAIN_CLASS_GOV,
    DOMAIN_CLASS_EDU,
    DOMAIN_CLASS_UGC,
    DOMAIN_CLASS_UNKNOWN,
    DOMAIN_CLASS_MAJOR_MEDIA,
    DOMAIN_CLASS_JOURNAL,
    FRESHNESS_BUCKET_VERY_RECENT,
    FRESHNESS_BUCKET_RECENT,
    FRESHNESS_BUCKET_MODERATE,
    FRESHNESS_BUCKET_OLD,
    FRESHNESS_BUCKET_VERY_OLD,
    FRESHNESS_BUCKET_UNKNOWN,
    CREDIBILITY_MODEL_VERSION,
)


def make_test_bundle(
    source_id: str,
    tool: ToolKind,
    url: str,
    domain: str,
    title: str = "Test",
    snippets: list = None,
    metadata: dict = None,
) -> SourceBundle:
    """Create test SourceBundle."""
    if snippets is None:
        snippets = [SourceSnippet(text="test snippet")]
    if metadata is None:
        metadata = {}
    
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


class TestDomainClassification:
    """Test domain classification rules."""
    
    def test_gov_classification(self):
        """GOV domains classified correctly."""
        assert classify_domain("usa.gov", "https://usa.gov") == DOMAIN_CLASS_GOV
        assert classify_domain("cdc.gov", "https://cdc.gov") == DOMAIN_CLASS_GOV
        assert classify_domain("state.gov.uk", "https://state.gov.uk") == DOMAIN_CLASS_GOV
    
    def test_edu_classification(self):
        """EDU domains classified correctly."""
        assert classify_domain("mit.edu", "https://mit.edu") == DOMAIN_CLASS_EDU
        assert classify_domain("stanford.edu", "https://stanford.edu") == DOMAIN_CLASS_EDU
        assert classify_domain("cs.stanford.edu", "https://cs.stanford.edu") == DOMAIN_CLASS_EDU
    
    def test_ugc_classification(self):
        """UGC domains classified correctly."""
        assert classify_domain("myblog.blogspot.com", "https://myblog.blogspot.com") == DOMAIN_CLASS_UGC
        assert classify_domain("medium.com", "https://medium.com") == DOMAIN_CLASS_UGC
        assert classify_domain("reddit.com", "https://reddit.com") == DOMAIN_CLASS_UGC
    
    def test_unknown_classification(self):
        """Unknown domains classified as UNKNOWN."""
        assert classify_domain("example.com", "https://example.com") == DOMAIN_CLASS_UNKNOWN
        assert classify_domain("randomsite.net", "https://randomsite.net") == DOMAIN_CLASS_UNKNOWN
    
    def test_major_media_classification(self):
        """Major media domains classified correctly."""
        assert classify_domain("nytimes.com", "https://nytimes.com") == DOMAIN_CLASS_MAJOR_MEDIA
        assert classify_domain("bbc.com", "https://bbc.com") == DOMAIN_CLASS_MAJOR_MEDIA
    
    def test_journal_classification(self):
        """Journal domains classified correctly."""
        assert classify_domain("nature.com", "https://nature.com") == DOMAIN_CLASS_JOURNAL
        assert classify_domain("science.org", "https://science.org") == DOMAIN_CLASS_JOURNAL


class TestDateParsing:
    """Test date parsing logic."""
    
    def test_parse_iso_date(self):
        """Parse ISO8601 dates."""
        dt = parse_date("2026-01-15")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 1
        assert dt.day == 15
    
    def test_parse_iso_datetime(self):
        """Parse ISO8601 datetime."""
        dt = parse_date("2026-01-15T12:30:00Z")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 1
        assert dt.day == 15
    
    def test_parse_invalid_date(self):
        """Invalid date returns None."""
        assert parse_date("invalid") is None
        assert parse_date("") is None
        assert parse_date("not-a-date") is None
    
    def test_extract_from_metadata(self):
        """Extract date from metadata."""
        metadata = {"published_at": "2026-01-15"}
        dt = extract_date_from_metadata(metadata)
        assert dt is not None
        assert dt.year == 2026
    
    def test_extract_priority_order(self):
        """Extract uses priority order."""
        metadata = {
            "date": "2026-01-20",
            "published_at": "2026-01-15",
        }
        dt = extract_date_from_metadata(metadata)
        assert dt.day == 15


class TestFreshnessBuckets:
    """Test freshness bucketing."""
    
    def test_very_recent_bucket(self):
        """0-7 days is very recent."""
        now_ms = int(datetime(2026, 1, 29).timestamp() * 1000)
        date = datetime(2026, 1, 25)
        age_days = compute_age_days(date, now_ms)
        
        assert 0 <= age_days <= 7
        assert classify_freshness(age_days) == FRESHNESS_BUCKET_VERY_RECENT
    
    def test_recent_bucket(self):
        """8-30 days is recent."""
        now_ms = int(datetime(2026, 1, 29).timestamp() * 1000)
        date = datetime(2026, 1, 10)
        age_days = compute_age_days(date, now_ms)
        
        assert 8 <= age_days <= 30
        assert classify_freshness(age_days) == FRESHNESS_BUCKET_RECENT
    
    def test_moderate_bucket(self):
        """31-180 days is moderate."""
        now_ms = int(datetime(2026, 1, 29).timestamp() * 1000)
        date = datetime(2025, 11, 1)
        age_days = compute_age_days(date, now_ms)
        
        assert 31 <= age_days <= 180
        assert classify_freshness(age_days) == FRESHNESS_BUCKET_MODERATE
    
    def test_old_bucket(self):
        """181-730 days is old."""
        now_ms = int(datetime(2026, 1, 29).timestamp() * 1000)
        date = datetime(2024, 12, 1)
        age_days = compute_age_days(date, now_ms)
        
        assert 181 <= age_days <= 730
        assert classify_freshness(age_days) == FRESHNESS_BUCKET_OLD
    
    def test_very_old_bucket(self):
        """>730 days is very old."""
        now_ms = int(datetime(2026, 1, 29).timestamp() * 1000)
        date = datetime(2023, 1, 1)
        age_days = compute_age_days(date, now_ms)
        
        assert age_days > 730
        assert classify_freshness(age_days) == FRESHNESS_BUCKET_VERY_OLD
    
    def test_unknown_bucket(self):
        """None age is unknown."""
        assert classify_freshness(None) == FRESHNESS_BUCKET_UNKNOWN


class TestAuthorDatePresence:
    """Test author/date presence detection."""
    
    def test_has_author(self):
        """Detect author field."""
        assert has_author_field({"author": "John Doe"}) == True
        assert has_author_field({"byline": "Jane Smith"}) == True
        assert has_author_field({"writer": "Bob Jones"}) == True
    
    def test_no_author(self):
        """Detect missing author."""
        assert has_author_field({}) == False
        assert has_author_field({"title": "Article"}) == False
        assert has_author_field({"author": ""}) == False
        assert has_author_field({"author": "   "}) == False


class TestClaimFingerprinting:
    """Test claim fingerprinting logic."""
    
    def test_normalize_claim_text(self):
        """Text normalization is deterministic."""
        text1 = "The QUICK brown fox!"
        text2 = "the quick   brown  fox"
        
        norm1 = normalize_claim_text(text1)
        norm2 = normalize_claim_text(text2)
        
        assert norm1 == norm2
        assert norm1 == "the quick brown fox"
    
    def test_extract_claim_tokens(self):
        """Token extraction is deterministic."""
        text = "quantum computing enables faster encryption breaking capabilities"
        tokens = extract_claim_tokens(text)
        
        assert len(tokens) <= 12
        assert "quantum" in tokens
        assert "computing" in tokens
        assert "encryption" in tokens
    
    def test_claim_key_determinism(self):
        """Same snippets produce same claim key."""
        snippets = [SourceSnippet(text="test claim about quantum computing")]
        
        key1 = compute_claim_key(snippets)
        key2 = compute_claim_key(snippets)
        
        assert key1 == key2
        assert len(key1) == 16


class TestCorroboration:
    """Test corroboration scoring."""
    
    def test_same_claim_different_domains(self):
        """Same claim across different domains increases corroboration."""
        now_ms = int(datetime(2026, 1, 29).timestamp() * 1000)
        
        snippets = [SourceSnippet(text="quantum computing enables faster encryption breaking capabilities")]
        
        bundles = [
            make_test_bundle("1", ToolKind.WEB, "https://example.com/1", "example.com", snippets=snippets),
            make_test_bundle("2", ToolKind.WEB, "https://other.com/1", "other.com", snippets=snippets),
        ]
        
        graded = grade_sources(bundles, now_ms)
        
        for g in graded:
            assert g.credibility.corroboration_count >= 2
    
    def test_same_domain_no_inflation(self):
        """Same domain doesn't inflate corroboration."""
        now_ms = int(datetime(2026, 1, 29).timestamp() * 1000)
        
        snippets = [SourceSnippet(text="quantum computing enables faster encryption breaking capabilities")]
        
        bundles = [
            make_test_bundle("1", ToolKind.WEB, "https://example.com/1", "example.com", snippets=snippets),
            make_test_bundle("2", ToolKind.WEB, "https://example.com/2", "example.com", snippets=snippets),
        ]
        
        graded = grade_sources(bundles, now_ms)
        
        for g in graded:
            assert g.credibility.corroboration_count == 1


class TestGradeBands:
    """Test grade band assignment."""
    
    def test_grade_a(self):
        """Score >= 80 is grade A."""
        assert assign_grade_band(80) == "A"
        assert assign_grade_band(90) == "A"
        assert assign_grade_band(100) == "A"
    
    def test_grade_b(self):
        """Score 65-79 is grade B."""
        assert assign_grade_band(65) == "B"
        assert assign_grade_band(70) == "B"
        assert assign_grade_band(79) == "B"
    
    def test_grade_c(self):
        """Score 50-64 is grade C."""
        assert assign_grade_band(50) == "C"
        assert assign_grade_band(60) == "C"
        assert assign_grade_band(64) == "C"
    
    def test_grade_d(self):
        """Score 35-49 is grade D."""
        assert assign_grade_band(35) == "D"
        assert assign_grade_band(40) == "D"
        assert assign_grade_band(49) == "D"
    
    def test_grade_e(self):
        """Score < 35 is grade E."""
        assert assign_grade_band(0) == "E"
        assert assign_grade_band(20) == "E"
        assert assign_grade_band(34) == "E"


class TestStableOrdering:
    """Test output ordering stability."""
    
    def test_ordering_preserved(self):
        """Output ordering matches input ordering."""
        now_ms = int(datetime(2026, 1, 29).timestamp() * 1000)
        
        bundles = [
            make_test_bundle("1", ToolKind.WEB, "https://a.com/1", "a.com"),
            make_test_bundle("2", ToolKind.WEB, "https://b.com/1", "b.com"),
            make_test_bundle("3", ToolKind.WEB, "https://c.com/1", "c.com"),
        ]
        
        graded = grade_sources(bundles, now_ms)
        
        assert len(graded) == 3
        assert graded[0].source.source_id == "1"
        assert graded[1].source.source_id == "2"
        assert graded[2].source.source_id == "3"


class TestFailClosed:
    """Test fail-closed behavior."""
    
    def test_invalid_metadata_no_crash(self):
        """Invalid metadata doesn't crash."""
        now_ms = int(datetime(2026, 1, 29).timestamp() * 1000)
        
        bundles = [
            make_test_bundle(
                "1",
                ToolKind.WEB,
                "https://example.com",
                "example.com",
                metadata={"date": "invalid-date", "author": 12345},
            ),
        ]
        
        graded = grade_sources(bundles, now_ms)
        
        assert len(graded) == 1
        assert graded[0].credibility.has_date == False
    
    def test_empty_snippets_no_crash(self):
        """Empty snippets don't crash."""
        now_ms = int(datetime(2026, 1, 29).timestamp() * 1000)
        
        bundles = [
            make_test_bundle("1", ToolKind.WEB, "https://example.com", "example.com", snippets=[]),
        ]
        
        graded = grade_sources(bundles, now_ms)
        
        assert len(graded) == 1


class TestDeterminism:
    """Test determinism guarantees."""
    
    def test_replay_identical_results(self):
        """Same inputs produce identical results across 20 runs."""
        now_ms = int(datetime(2026, 1, 29).timestamp() * 1000)
        
        bundles = [
            make_test_bundle(
                "1",
                ToolKind.WEB,
                "https://cdc.gov/article",
                "cdc.gov",
                snippets=[SourceSnippet(text="public health guidance on vaccination")],
                metadata={"author": "CDC Staff", "date": "2026-01-20"},
            ),
            make_test_bundle(
                "2",
                ToolKind.WEB,
                "https://nytimes.com/health",
                "nytimes.com",
                snippets=[SourceSnippet(text="public health guidance on vaccination")],
                metadata={"author": "Reporter", "date": "2026-01-21"},
            ),
        ]
        
        results = []
        for _ in range(20):
            graded = grade_sources(bundles, now_ms)
            results.append(graded)
        
        for i in range(1, 20):
            assert len(results[i]) == len(results[0])
            for j in range(len(results[0])):
                assert results[i][j].credibility.score == results[0][j].credibility.score
                assert results[i][j].credibility.grade == results[0][j].credibility.grade
                assert results[i][j].credibility.domain_class == results[0][j].credibility.domain_class
                assert results[i][j].credibility.corroboration_count == results[0][j].credibility.corroboration_count


class TestScoreBreakdown:
    """Test score breakdown and penalty application."""
    
    def test_author_penalty_applied(self):
        """Missing author applies penalty."""
        now_ms = int(datetime(2026, 1, 29).timestamp() * 1000)
        
        bundle_with_author = make_test_bundle(
            "1", ToolKind.WEB, "https://example.com", "example.com",
            metadata={"author": "John Doe"},
        )
        bundle_without_author = make_test_bundle(
            "2", ToolKind.WEB, "https://example.com", "example.com",
            metadata={},
        )
        
        graded_with = grade_sources([bundle_with_author], now_ms)
        graded_without = grade_sources([bundle_without_author], now_ms)
        
        assert graded_with[0].credibility.has_author == True
        assert graded_without[0].credibility.has_author == False
        assert graded_with[0].credibility.score > graded_without[0].credibility.score
    
    def test_date_penalty_applied(self):
        """Missing date applies penalty."""
        now_ms = int(datetime(2026, 1, 29).timestamp() * 1000)
        
        bundle_with_date = make_test_bundle(
            "1", ToolKind.WEB, "https://example.com", "example.com",
            metadata={"date": "2026-01-20"},
        )
        bundle_without_date = make_test_bundle(
            "2", ToolKind.WEB, "https://example.com", "example.com",
            metadata={},
        )
        
        graded_with = grade_sources([bundle_with_date], now_ms)
        graded_without = grade_sources([bundle_without_date], now_ms)
        
        assert graded_with[0].credibility.has_date == True
        assert graded_without[0].credibility.has_date == False
        assert graded_with[0].credibility.score > graded_without[0].credibility.score


class TestModelVersion:
    """Test model version tracking."""
    
    def test_model_version_present(self):
        """Model version is attached to reports."""
        now_ms = int(datetime(2026, 1, 29).timestamp() * 1000)
        
        bundles = [make_test_bundle("1", ToolKind.WEB, "https://example.com", "example.com")]
        graded = grade_sources(bundles, now_ms)
        
        assert graded[0].credibility.model_version == CREDIBILITY_MODEL_VERSION
        assert graded[0].credibility.model_version == "18.3.0"


if __name__ == "__main__":
    print("Running Phase 18 Step 3 Credibility Grader Tests...")
    print()
    
    print("Test Group: Domain Classification")
    test_dc = TestDomainClassification()
    test_dc.test_gov_classification()
    print("✓ GOV classification")
    test_dc.test_edu_classification()
    print("✓ EDU classification")
    test_dc.test_ugc_classification()
    print("✓ UGC classification")
    test_dc.test_unknown_classification()
    print("✓ UNKNOWN classification")
    test_dc.test_major_media_classification()
    print("✓ Major media classification")
    test_dc.test_journal_classification()
    print("✓ Journal classification")
    
    print("\nTest Group: Date Parsing")
    test_dp = TestDateParsing()
    test_dp.test_parse_iso_date()
    print("✓ Parse ISO date")
    test_dp.test_parse_iso_datetime()
    print("✓ Parse ISO datetime")
    test_dp.test_parse_invalid_date()
    print("✓ Invalid date returns None")
    test_dp.test_extract_from_metadata()
    print("✓ Extract from metadata")
    test_dp.test_extract_priority_order()
    print("✓ Extract priority order")
    
    print("\nTest Group: Freshness Buckets")
    test_fb = TestFreshnessBuckets()
    test_fb.test_very_recent_bucket()
    print("✓ Very recent bucket (0-7 days)")
    test_fb.test_recent_bucket()
    print("✓ Recent bucket (8-30 days)")
    test_fb.test_moderate_bucket()
    print("✓ Moderate bucket (31-180 days)")
    test_fb.test_old_bucket()
    print("✓ Old bucket (181-730 days)")
    test_fb.test_very_old_bucket()
    print("✓ Very old bucket (>730 days)")
    test_fb.test_unknown_bucket()
    print("✓ Unknown bucket")
    
    print("\nTest Group: Author/Date Presence")
    test_adp = TestAuthorDatePresence()
    test_adp.test_has_author()
    print("✓ Detect author field")
    test_adp.test_no_author()
    print("✓ Detect missing author")
    
    print("\nTest Group: Claim Fingerprinting")
    test_cf = TestClaimFingerprinting()
    test_cf.test_normalize_claim_text()
    print("✓ Text normalization")
    test_cf.test_extract_claim_tokens()
    print("✓ Token extraction")
    test_cf.test_claim_key_determinism()
    print("✓ Claim key determinism")
    
    print("\nTest Group: Corroboration")
    test_corr = TestCorroboration()
    test_corr.test_same_claim_different_domains()
    print("✓ Same claim different domains -> corroboration")
    test_corr.test_same_domain_no_inflation()
    print("✓ Same domain no inflation")
    
    print("\nTest Group: Grade Bands")
    test_gb = TestGradeBands()
    test_gb.test_grade_a()
    print("✓ Grade A (>=80)")
    test_gb.test_grade_b()
    print("✓ Grade B (65-79)")
    test_gb.test_grade_c()
    print("✓ Grade C (50-64)")
    test_gb.test_grade_d()
    print("✓ Grade D (35-49)")
    test_gb.test_grade_e()
    print("✓ Grade E (<35)")
    
    print("\nTest Group: Stable Ordering")
    test_so = TestStableOrdering()
    test_so.test_ordering_preserved()
    print("✓ Output ordering preserved")
    
    print("\nTest Group: Fail-Closed")
    test_fc = TestFailClosed()
    test_fc.test_invalid_metadata_no_crash()
    print("✓ Invalid metadata no crash")
    test_fc.test_empty_snippets_no_crash()
    print("✓ Empty snippets no crash")
    
    print("\nTest Group: Determinism")
    test_det = TestDeterminism()
    test_det.test_replay_identical_results()
    print("✓ Replay 20 times -> identical results")
    
    print("\nTest Group: Score Breakdown")
    test_sb = TestScoreBreakdown()
    test_sb.test_author_penalty_applied()
    print("✓ Author penalty applied")
    test_sb.test_date_penalty_applied()
    print("✓ Date penalty applied")
    
    print("\nTest Group: Model Version")
    test_mv = TestModelVersion()
    test_mv.test_model_version_present()
    print("✓ Model version present")
    
    print("\n" + "="*60)
    print("ALL CREDIBILITY GRADER TESTS PASSED ✓")
    print("="*60)
