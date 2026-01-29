"""
Phase 18 Step 4: Citation Policy and References

Defines CitationRef structure and helpers for citation handling.
No snippet text is stored in CitationRef to prevent leakage.
"""

import hashlib
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse


MAX_URL_LENGTH = 300
MAX_DOMAIN_LENGTH = 80
MAX_TITLE_LENGTH = 120
MAX_DATE_LENGTH = 32


GRADE_TO_SCORE = {
    "A": 90,
    "B": 75,
    "C": 60,
    "D": 45,
    "E": 30,
    "UNKNOWN": 0,
}


@dataclass(frozen=True)
class CitationRef:
    """
    Citation reference attached to a claim.
    
    CRITICAL: No snippet text stored here to prevent leakage.
    Only metadata and pointers.
    """
    source_id: str
    url: str
    domain: str
    title: Optional[str]
    published_date: Optional[str]
    snippet_index: int
    snippet_len: int
    credibility_grade: Optional[str]
    credibility_score: Optional[int]


def normalize_url(url: str) -> str:
    """
    Normalize URL deterministically.
    
    Args:
        url: Raw URL string
    
    Returns:
        Normalized URL (bounded)
    """
    if not url:
        return ""
    
    url = url.strip()
    url_lower = url.lower()
    
    if not url_lower.startswith("http://") and not url_lower.startswith("https://"):
        url = "https://" + url
    
    url = url.lower()
    
    if url.endswith("/"):
        url = url[:-1]
    
    return url[:MAX_URL_LENGTH]


def extract_domain(url: str) -> str:
    """
    Extract domain from URL deterministically.
    
    Args:
        url: URL string
    
    Returns:
        Domain (bounded)
    """
    if not url:
        return "unknown"
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        domain = domain.lower().strip()
        
        if domain.startswith("www."):
            domain = domain[4:]
        
        return domain[:MAX_DOMAIN_LENGTH] if domain else "unknown"
    except Exception:
        return "unknown"


def make_citation_ref(
    source_id: str,
    url: str,
    domain: str,
    title: str,
    snippet_index: int,
    snippet_len: int,
    published_date: Optional[str] = None,
    credibility_report: Optional[object] = None,
) -> CitationRef:
    """
    Create CitationRef from source metadata.
    
    Args:
        source_id: Source ID
        url: Source URL
        domain: Source domain
        title: Source title
        snippet_index: Index of snippet (0-based)
        snippet_len: Length of snippet (metadata only)
        published_date: Optional publication date
        credibility_report: Optional CredibilityReport from Step 18.3
    
    Returns:
        CitationRef with bounded fields
    """
    credibility_grade = None
    credibility_score = None
    
    if credibility_report:
        credibility_grade = getattr(credibility_report, "grade", None)
        credibility_score = getattr(credibility_report, "score", None)
        
        if credibility_grade and credibility_grade not in GRADE_TO_SCORE:
            credibility_grade = "UNKNOWN"
        
        if credibility_score is not None:
            credibility_score = max(0, min(100, credibility_score))
    
    bounded_title = title[:MAX_TITLE_LENGTH] if title else None
    bounded_date = published_date[:MAX_DATE_LENGTH] if published_date else None
    
    return CitationRef(
        source_id=source_id,
        url=normalize_url(url),
        domain=domain[:MAX_DOMAIN_LENGTH],
        title=bounded_title,
        published_date=bounded_date,
        snippet_index=snippet_index,
        snippet_len=snippet_len,
        credibility_grade=credibility_grade,
        credibility_score=credibility_score,
    )
