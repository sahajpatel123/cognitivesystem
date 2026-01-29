"""
Phase 18 Step 3: Source Credibility Grader (Rule-based)

Deterministic, explainable credibility scoring for research sources.

Contract guarantees:
- Deterministic: same inputs + same now_ms => identical outputs
- Rule-based: all weights/thresholds are explicit constants
- Fail-closed: invalid inputs produce safe defaults
- No ML, no embeddings, no network calls
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional

from backend.app.retrieval.types import SourceBundle, SourceSnippet


CREDIBILITY_MODEL_VERSION = "18.3.0"


DOMAIN_CLASS_GOV = "GOV"
DOMAIN_CLASS_EDU = "EDU"
DOMAIN_CLASS_JOURNAL = "JOURNAL"
DOMAIN_CLASS_MAJOR_MEDIA = "MAJOR_MEDIA"
DOMAIN_CLASS_OFFICIAL = "OFFICIAL"
DOMAIN_CLASS_UGC = "UGC"
DOMAIN_CLASS_UNKNOWN = "UNKNOWN"


DOMAIN_SCORES = {
    DOMAIN_CLASS_GOV: 40,
    DOMAIN_CLASS_EDU: 35,
    DOMAIN_CLASS_JOURNAL: 35,
    DOMAIN_CLASS_OFFICIAL: 30,
    DOMAIN_CLASS_MAJOR_MEDIA: 25,
    DOMAIN_CLASS_UNKNOWN: 10,
    DOMAIN_CLASS_UGC: 0,
}


FRESHNESS_BUCKET_VERY_RECENT = "0-7_days"
FRESHNESS_BUCKET_RECENT = "8-30_days"
FRESHNESS_BUCKET_MODERATE = "31-180_days"
FRESHNESS_BUCKET_OLD = "181-730_days"
FRESHNESS_BUCKET_VERY_OLD = ">730_days"
FRESHNESS_BUCKET_UNKNOWN = "unknown"


FRESHNESS_SCORES = {
    FRESHNESS_BUCKET_VERY_RECENT: 15,
    FRESHNESS_BUCKET_RECENT: 12,
    FRESHNESS_BUCKET_MODERATE: 8,
    FRESHNESS_BUCKET_OLD: 4,
    FRESHNESS_BUCKET_VERY_OLD: 0,
    FRESHNESS_BUCKET_UNKNOWN: 5,
}


PENALTY_NO_AUTHOR = -5
PENALTY_NO_DATE = -5


CORROBORATION_SCORES = {
    0: 0,
    1: 0,
    2: 5,
    3: 8,
}
CORROBORATION_MAX_BONUS = 10


GRADE_BAND_A = "A"
GRADE_BAND_B = "B"
GRADE_BAND_C = "C"
GRADE_BAND_D = "D"
GRADE_BAND_E = "E"


MAJOR_MEDIA_DOMAINS = {
    "nytimes.com",
    "washingtonpost.com",
    "wsj.com",
    "bbc.com",
    "bbc.co.uk",
    "reuters.com",
    "apnews.com",
    "theguardian.com",
    "cnn.com",
    "npr.org",
}


JOURNAL_PATTERNS = [
    "nature.com",
    "science.org",
    "sciencedirect.com",
    "springer.com",
    "wiley.com",
    "ieee.org",
    "acm.org",
    "plos.org",
    "pubmed.ncbi.nlm.nih.gov",
    "arxiv.org",
]


UGC_PATTERNS = [
    "blogspot.com",
    "medium.com",
    "wordpress.com",
    "reddit.com",
    "stackoverflow.com",
    "stackexchange.com",
    "quora.com",
    "github.io",
]


@dataclass(frozen=True)
class CredibilityReport:
    """
    Credibility scoring breakdown.
    
    All fields are deterministic and explicitly derived from rules.
    """
    score: int
    grade: str
    domain_class: str
    freshness_bucket: str
    has_author: bool
    has_date: bool
    age_days: Optional[int]
    corroboration_count: int
    score_breakdown: Dict[str, int]
    model_version: str


@dataclass(frozen=True)
class GradedSource:
    """
    Source bundle with attached credibility report.
    
    Preserves original SourceBundle + adds grading.
    """
    source: SourceBundle
    credibility: CredibilityReport


def classify_domain(domain: str, url: str) -> str:
    """
    Classify domain deterministically.
    
    Priority order (first match wins):
    1. GOV
    2. EDU
    3. JOURNAL
    4. OFFICIAL
    5. MAJOR_MEDIA
    6. UGC
    7. UNKNOWN (fallback)
    
    Args:
        domain: Domain string (already lowercase)
        url: Full URL (for additional context)
    
    Returns:
        Domain class string
    """
    domain_lower = domain.lower()
    url_lower = url.lower()
    
    if domain_lower.endswith(".gov") or ".gov." in domain_lower:
        return DOMAIN_CLASS_GOV
    
    if domain_lower.endswith(".edu") or ".edu." in domain_lower:
        return DOMAIN_CLASS_EDU
    
    for pattern in JOURNAL_PATTERNS:
        if pattern in domain_lower:
            return DOMAIN_CLASS_JOURNAL
    
    if (domain_lower.startswith("docs.") or 
        domain_lower.startswith("developer.") or 
        domain_lower.startswith("api.")):
        return DOMAIN_CLASS_OFFICIAL
    
    if domain_lower in MAJOR_MEDIA_DOMAINS:
        return DOMAIN_CLASS_MAJOR_MEDIA
    
    for pattern in UGC_PATTERNS:
        if pattern in domain_lower:
            return DOMAIN_CLASS_UGC
    
    return DOMAIN_CLASS_UNKNOWN


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse date string deterministically.
    
    Accepts ISO8601-like formats:
    - YYYY-MM-DD
    - YYYY-MM-DDTHH:MM:SSZ
    - YYYY-MM-DD HH:MM:SS
    
    Args:
        date_str: Date string
    
    Returns:
        datetime object or None if unparseable
    """
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    
    return None


def extract_date_from_metadata(metadata: Dict) -> Optional[datetime]:
    """
    Extract date from metadata deterministically.
    
    Tries known date fields in priority order.
    
    Args:
        metadata: Source metadata dict
    
    Returns:
        datetime or None
    """
    date_fields = ["published_at", "date", "last_updated", "updated_at", "timestamp"]
    
    for field in date_fields:
        if field in metadata:
            value = metadata[field]
            if isinstance(value, str):
                parsed = parse_date(value)
                if parsed:
                    return parsed
    
    return None


def compute_age_days(date: datetime, now_ms: int) -> int:
    """
    Compute age in days from date to now_ms.
    
    Args:
        date: datetime object
        now_ms: Current time in milliseconds
    
    Returns:
        Age in days (non-negative)
    """
    now_dt = datetime.utcfromtimestamp(now_ms / 1000.0)
    delta = now_dt - date
    age_days = max(0, delta.days)
    return age_days


def classify_freshness(age_days: Optional[int]) -> str:
    """
    Classify freshness into buckets.
    
    Args:
        age_days: Age in days or None
    
    Returns:
        Freshness bucket string
    """
    if age_days is None:
        return FRESHNESS_BUCKET_UNKNOWN
    
    if age_days <= 7:
        return FRESHNESS_BUCKET_VERY_RECENT
    elif age_days <= 30:
        return FRESHNESS_BUCKET_RECENT
    elif age_days <= 180:
        return FRESHNESS_BUCKET_MODERATE
    elif age_days <= 730:
        return FRESHNESS_BUCKET_OLD
    else:
        return FRESHNESS_BUCKET_VERY_OLD


def has_author_field(metadata: Dict) -> bool:
    """
    Check if metadata has author field.
    
    Args:
        metadata: Source metadata dict
    
    Returns:
        True if author present and non-empty
    """
    author_fields = ["author", "byline", "writer"]
    
    for field in author_fields:
        if field in metadata:
            value = metadata[field]
            if isinstance(value, str) and value.strip():
                return True
    
    return False


def normalize_claim_text(text: str) -> str:
    """
    Normalize text for claim fingerprinting.
    
    - Lowercase
    - Remove punctuation
    - Collapse whitespace
    
    Args:
        text: Raw text
    
    Returns:
        Normalized text
    """
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_claim_tokens(text: str, max_tokens: int = 12) -> List[str]:
    """
    Extract claim tokens deterministically.
    
    - Tokens must be >4 chars
    - Sort by length (desc), then lexicographically
    - Take top N
    
    Args:
        text: Normalized text
        max_tokens: Maximum tokens to extract
    
    Returns:
        List of tokens (sorted, deduped, bounded)
    """
    tokens = text.split()
    tokens = [t for t in tokens if len(t) > 4]
    tokens = list(set(tokens))
    tokens.sort(key=lambda t: (-len(t), t))
    return tokens[:max_tokens]


def compute_claim_key(snippets: List[SourceSnippet]) -> str:
    """
    Compute claim fingerprint from snippets.
    
    Deterministic hash of normalized claim material.
    
    Args:
        snippets: List of source snippets
    
    Returns:
        Claim key (16-char hex string)
    """
    all_text = " ".join([s.text for s in snippets])
    normalized = normalize_claim_text(all_text)
    tokens = extract_claim_tokens(normalized)
    claim_material = "|".join(tokens)[:256]
    
    if not claim_material:
        claim_material = "empty"
    
    hash_digest = hashlib.sha256(claim_material.encode('utf-8')).hexdigest()
    return hash_digest[:16]


def compute_corroboration_score(
    bundles: List[SourceBundle],
    claim_keys: Dict[str, str],
) -> Dict[str, int]:
    """
    Compute corroboration counts per source.
    
    Counts distinct domains sharing the same claim_key.
    
    Args:
        bundles: List of source bundles
        claim_keys: Map of source_id -> claim_key
    
    Returns:
        Map of source_id -> corroboration_count
    """
    claim_to_domains: Dict[str, set] = {}
    
    for bundle in bundles:
        claim_key = claim_keys.get(bundle.source_id)
        if claim_key:
            if claim_key not in claim_to_domains:
                claim_to_domains[claim_key] = set()
            claim_to_domains[claim_key].add(bundle.domain)
    
    corroboration_counts = {}
    for bundle in bundles:
        claim_key = claim_keys.get(bundle.source_id)
        if claim_key and claim_key in claim_to_domains:
            count = len(claim_to_domains[claim_key])
        else:
            count = 1
        corroboration_counts[bundle.source_id] = count
    
    return corroboration_counts


def compute_final_score(
    domain_score: int,
    freshness_score: int,
    author_penalty: int,
    date_penalty: int,
    corroboration_bonus: int,
) -> int:
    """
    Compute final credibility score with clamping.
    
    Args:
        domain_score: Domain class score
        freshness_score: Freshness bucket score
        author_penalty: Author presence penalty
        date_penalty: Date presence penalty
        corroboration_bonus: Corroboration bonus
    
    Returns:
        Final score (0-100)
    """
    score = domain_score + freshness_score + author_penalty + date_penalty + corroboration_bonus
    return max(0, min(100, score))


def assign_grade_band(score: int) -> str:
    """
    Assign grade band from score.
    
    Args:
        score: Final score (0-100)
    
    Returns:
        Grade band (A/B/C/D/E)
    """
    if score >= 80:
        return GRADE_BAND_A
    elif score >= 65:
        return GRADE_BAND_B
    elif score >= 50:
        return GRADE_BAND_C
    elif score >= 35:
        return GRADE_BAND_D
    else:
        return GRADE_BAND_E


def grade_sources(bundles: List[SourceBundle], now_ms: int) -> List[GradedSource]:
    """
    Grade sources with deterministic credibility scoring.
    
    Single entrypoint for credibility grading.
    
    Args:
        bundles: List of source bundles from retrieval adapter
        now_ms: Current time in milliseconds (injected for determinism)
    
    Returns:
        List of graded sources (stable-sorted, same order as input)
    """
    if not bundles:
        return []
    
    claim_keys = {}
    for bundle in bundles:
        claim_key = compute_claim_key(bundle.snippets)
        claim_keys[bundle.source_id] = claim_key
    
    corroboration_counts = compute_corroboration_score(bundles, claim_keys)
    
    graded = []
    
    for bundle in bundles:
        domain_class = classify_domain(bundle.domain, bundle.url)
        domain_score = DOMAIN_SCORES[domain_class]
        
        date_obj = extract_date_from_metadata(bundle.metadata)
        age_days = compute_age_days(date_obj, now_ms) if date_obj else None
        freshness_bucket = classify_freshness(age_days)
        freshness_score = FRESHNESS_SCORES[freshness_bucket]
        
        has_author = has_author_field(bundle.metadata)
        has_date = date_obj is not None
        
        author_penalty = 0 if has_author else PENALTY_NO_AUTHOR
        date_penalty = 0 if has_date else PENALTY_NO_DATE
        
        corroboration_count = corroboration_counts.get(bundle.source_id, 1)
        if corroboration_count in CORROBORATION_SCORES:
            corroboration_bonus = CORROBORATION_SCORES[corroboration_count]
        else:
            corroboration_bonus = CORROBORATION_MAX_BONUS
        
        final_score = compute_final_score(
            domain_score,
            freshness_score,
            author_penalty,
            date_penalty,
            corroboration_bonus,
        )
        
        grade = assign_grade_band(final_score)
        
        score_breakdown = {
            "domain": domain_score,
            "freshness": freshness_score,
            "author_penalty": author_penalty,
            "date_penalty": date_penalty,
            "corroboration_bonus": corroboration_bonus,
        }
        
        report = CredibilityReport(
            score=final_score,
            grade=grade,
            domain_class=domain_class,
            freshness_bucket=freshness_bucket,
            has_author=has_author,
            has_date=has_date,
            age_days=age_days,
            corroboration_count=corroboration_count,
            score_breakdown=score_breakdown,
            model_version=CREDIBILITY_MODEL_VERSION,
        )
        
        graded.append(GradedSource(source=bundle, credibility=report))
    
    return graded
