"""
Phase 19 Step 6: Safety Filter (Forbidden Category Detector)

Rule-based forbidden category detector that prevents accidental storage of sensitive topics.
If forbidden content is detected in ANY fact in a write request, the ENTIRE write must be rejected.

Contract guarantees:
- Rule-based only (no ML, no embeddings, no external calls)
- Deterministic: same inputs -> same decision + same reason codes
- Fail-closed: if detector errors, treat as forbidden and reject
- No raw user text stored or logged
- Whole-request rejection: if any fact triggers -> reject all facts
- Deterministic reason codes with stable priority ordering
"""

import json
import re
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import List, Optional, Tuple

from backend.app.memory.schema import MemoryFact


# ============================================================================
# CONSTANTS
# ============================================================================

# Bounds for safety filter
MAX_MATCHES_RETURNED = 8
MAX_RULE_ID_LEN = 48
MAX_FIELD_LEN = 24
MAX_SCAN_TEXT_LEN = 1200
MAX_LIST_ITEM_LEN = 200

# Zero-width characters to remove
ZERO_WIDTH_CHARS = [
    '\u200b',  # zero width space
    '\u200c',  # zero width non-joiner
    '\u200d',  # zero width joiner
    '\ufeff',  # byte order mark
]


# ============================================================================
# ENUMS
# ============================================================================

class ForbiddenReason(Enum):
    """
    Forbidden category reasons with deterministic priority ordering.
    
    Priority order (highest wins): HEALTH > SEX_LIFE > POLITICS > RELIGION > UNION > OTHER > INTERNAL_ERROR
    """
    FORBIDDEN_HEALTH = "FORBIDDEN_HEALTH"
    FORBIDDEN_SEX_LIFE = "FORBIDDEN_SEX_LIFE"
    FORBIDDEN_POLITICS = "FORBIDDEN_POLITICS"
    FORBIDDEN_RELIGION = "FORBIDDEN_RELIGION"
    FORBIDDEN_UNION = "FORBIDDEN_UNION"
    FORBIDDEN_SENSITIVE_OTHER = "FORBIDDEN_SENSITIVE_OTHER"
    FORBIDDEN_INTERNAL_ERROR = "FORBIDDEN_INTERNAL_ERROR"


# Priority mapping (lower number = higher priority)
REASON_PRIORITY: dict[ForbiddenReason, int] = {
    ForbiddenReason.FORBIDDEN_HEALTH: 0,
    ForbiddenReason.FORBIDDEN_SEX_LIFE: 1,
    ForbiddenReason.FORBIDDEN_POLITICS: 2,
    ForbiddenReason.FORBIDDEN_RELIGION: 3,
    ForbiddenReason.FORBIDDEN_UNION: 4,
    ForbiddenReason.FORBIDDEN_SENSITIVE_OTHER: 5,
    ForbiddenReason.FORBIDDEN_INTERNAL_ERROR: 6,
}


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ForbiddenMatch:
    """A match found by the forbidden category detector."""
    reason: ForbiddenReason
    matched_rule_id: str  # bounded length <= 48
    field: str           # "key"|"value_str"|"value_str_list"|"tags"
    match_count: int
    evidence_len: int    # length only; NEVER include text


@dataclass
class ForbiddenScanResult:
    """Result of scanning facts for forbidden content."""
    forbidden: bool
    top_reason: Optional[ForbiddenReason]
    matches: List[ForbiddenMatch]  # bounded, max 8
    signature: str  # structure-only hash; no raw text


# ============================================================================
# DETECTION RULES
# ============================================================================

# Health/Medical patterns
HEALTH_PATTERNS = [
    (r'\bdiagnosed\b', "HEALTH_DIAGNOSED_01"),
    (r'\bdiabetes\b', "HEALTH_DIABETES_01"),
    (r'\bcancer\b', "HEALTH_CANCER_01"),
    (r'\basthma\b', "HEALTH_ASTHMA_01"),
    (r'\b(?:bp|blood pressure)\b', "HEALTH_BP_01"),
    (r'\bdepression\b', "HEALTH_DEPRESSION_01"),
    (r'\badhd\b', "HEALTH_ADHD_01"),
    (r'\bbipolar\b', "HEALTH_BIPOLAR_01"),
    (r'\bocd\b', "HEALTH_OCD_01"),
    (r'\bprescription\b', "HEALTH_PRESCRIPTION_01"),
    (r'\bmedication\b', "HEALTH_MEDICATION_01"),
    (r'\bsymptoms\b', "HEALTH_SYMPTOMS_01"),
    (r'\bhospital\b', "HEALTH_HOSPITAL_01"),
    (r'\bpregnant\b', "HEALTH_PREGNANT_01"),
    (r'\bmental health\b', "HEALTH_MENTAL_01"),
    (r'\btherapy\b', "HEALTH_THERAPY_01"),
    (r'\bdoctor\b', "HEALTH_DOCTOR_01"),
]

# Politics patterns
POLITICS_PATTERNS = [
    (r'\bvote\b', "POLITICS_VOTE_01"),
    (r'\bvoting\b', "POLITICS_VOTING_01"),
    (r'\belection\b', "POLITICS_ELECTION_01"),
    (r'\bcampaign\b', "POLITICS_CAMPAIGN_01"),
    (r'\bbjp\b', "POLITICS_BJP_01"),
    (r'\bcongress\b', "POLITICS_CONGRESS_01"),
    (r'\baap\b', "POLITICS_AAP_01"),
    (r'\bpolitical party\b', "POLITICS_PARTY_01"),
    (r'\bleft wing\b', "POLITICS_LEFT_01"),
    (r'\bright wing\b', "POLITICS_RIGHT_01"),
    (r'\bdemocrat\b', "POLITICS_DEMOCRAT_01"),
    (r'\brepublican\b', "POLITICS_REPUBLICAN_01"),
]

# Religion patterns
RELIGION_PATTERNS = [
    (r'\bmuslim\b', "RELIGION_MUSLIM_01"),
    (r'\bhindu\b', "RELIGION_HINDU_01"),
    (r'\bchristian\b', "RELIGION_CHRISTIAN_01"),
    (r'\bsikh\b', "RELIGION_SIKH_01"),
    (r'\bjain\b', "RELIGION_JAIN_01"),
    (r'\bbuddhist\b', "RELIGION_BUDDHIST_01"),
    (r'\breligion\b', "RELIGION_GENERAL_01"),
    (r'\btemple\b', "RELIGION_TEMPLE_01"),
    (r'\bmosque\b', "RELIGION_MOSQUE_01"),
    (r'\bchurch\b', "RELIGION_CHURCH_01"),
    (r'\bislam\b', "RELIGION_ISLAM_01"),
    (r'\bhinduism\b', "RELIGION_HINDUISM_01"),
    (r'\bchristianity\b', "RELIGION_CHRISTIANITY_01"),
]

# Sex life patterns
SEX_LIFE_PATTERNS = [
    (r'\bsex life\b', "SEX_LIFE_GENERAL_01"),
    (r'\bsexual\b', "SEX_LIFE_SEXUAL_01"),
    (r'\bintercourse\b', "SEX_LIFE_INTERCOURSE_01"),
    (r'\bporn\b', "SEX_LIFE_PORN_01"),
    (r'\bfetish\b', "SEX_LIFE_FETISH_01"),
    (r'\bcondom\b', "SEX_LIFE_CONDOM_01"),
    (r'\bstd\b', "SEX_LIFE_STD_01"),
    (r'\berotic\b', "SEX_LIFE_EROTIC_01"),
]

# Union membership patterns
UNION_PATTERNS = [
    (r'\bunion member\b', "UNION_MEMBER_01"),
    (r'\btrade union\b', "UNION_TRADE_01"),
    (r'\blabor union\b', "UNION_LABOR_01"),
    (r'\bunionized\b', "UNION_UNIONIZED_01"),
    (r'\bcollective bargaining\b', "UNION_BARGAINING_01"),
]

# Sensitive identity patterns
SENSITIVE_OTHER_PATTERNS = [
    (r'\bsexual orientation\b', "SENSITIVE_ORIENTATION_01"),
    (r'\blgbt\b', "SENSITIVE_LGBT_01"),
    (r'\bgay\b', "SENSITIVE_GAY_01"),
    (r'\blesbian\b', "SENSITIVE_LESBIAN_01"),
    (r'\btransgender\b', "SENSITIVE_TRANSGENDER_01"),
    (r'\brace\b', "SENSITIVE_RACE_01"),
    (r'\bcaste\b', "SENSITIVE_CASTE_01"),
    (r'\bethnicity\b', "SENSITIVE_ETHNICITY_01"),
]

# Academic context exceptions (these should NOT trigger if found)
ACADEMIC_EXCEPTIONS = [
    r'\bpolitical science\b',
    r'\breligious studies\b',
    r'\bhealth education\b',
    r'\bsex education\b',
    r'\bmedical textbook\b',
    r'\bacademic course\b',
    r'\bsyllabus\b',
    r'\bcurriculum\b',
]

# Affiliation verbs that make context personal (these make exceptions not apply)
AFFILIATION_VERBS = [
    r'\bi am\b',
    r'\bmy religion is\b',
    r'\bi support\b',
    r'\bi vote\b',
    r'\bi believe\b',
    r'\bmy caste is\b',
    r'\bi have\b',
    r'\bi was diagnosed\b',
]

# All pattern groups
PATTERN_GROUPS = [
    (HEALTH_PATTERNS, ForbiddenReason.FORBIDDEN_HEALTH),
    (SEX_LIFE_PATTERNS, ForbiddenReason.FORBIDDEN_SEX_LIFE),
    (POLITICS_PATTERNS, ForbiddenReason.FORBIDDEN_POLITICS),
    (RELIGION_PATTERNS, ForbiddenReason.FORBIDDEN_RELIGION),
    (UNION_PATTERNS, ForbiddenReason.FORBIDDEN_UNION),
    (SENSITIVE_OTHER_PATTERNS, ForbiddenReason.FORBIDDEN_SENSITIVE_OTHER),
]


# ============================================================================
# TEXT NORMALIZATION
# ============================================================================

def _normalize_text(text: str) -> str:
    """
    Normalize text for scanning with deterministic rules.
    
    Returns normalized text clamped to MAX_SCAN_TEXT_LEN.
    """
    if not text:
        return ""
    
    # Remove zero-width characters
    for char in ZERO_WIDTH_CHARS:
        text = text.replace(char, "")
    
    # Lowercase, collapse whitespace, strip
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Clamp length
    if len(text) > MAX_SCAN_TEXT_LEN:
        text = text[:MAX_SCAN_TEXT_LEN]
    
    return text


def _normalize_list_item(item: str) -> str:
    """Normalize a single list item with per-item length limit."""
    if not item:
        return ""
    
    # Same normalization as text but with per-item limit
    for char in ZERO_WIDTH_CHARS:
        item = item.replace(char, "")
    
    item = item.lower()
    item = re.sub(r'\s+', ' ', item)
    item = item.strip()
    
    # Clamp to per-item limit
    if len(item) > MAX_LIST_ITEM_LEN:
        item = item[:MAX_LIST_ITEM_LEN]
    
    return item


# ============================================================================
# PATTERN MATCHING
# ============================================================================

def _has_academic_exception(text: str) -> bool:
    """Check if text contains academic context that should exempt it."""
    for pattern in ACADEMIC_EXCEPTIONS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _has_affiliation_verb(text: str) -> bool:
    """Check if text contains personal affiliation verbs."""
    for pattern in AFFILIATION_VERBS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _scan_text_for_patterns(
    text: str,
    field_name: str,
    patterns: List[Tuple[str, str]],
    reason: ForbiddenReason,
) -> List[ForbiddenMatch]:
    """
    Scan text for forbidden patterns.
    
    Returns list of matches found.
    """
    if not text:
        return []
    
    normalized = _normalize_text(text)
    if not normalized:
        return []
    
    # Check for academic exception (but only if no affiliation verbs)
    if _has_academic_exception(normalized) and not _has_affiliation_verb(normalized):
        return []
    
    matches = []
    for pattern, rule_id in patterns:
        try:
            # Count matches
            match_count = len(re.findall(pattern, normalized, re.IGNORECASE))
            if match_count > 0:
                matches.append(ForbiddenMatch(
                    reason=reason,
                    matched_rule_id=rule_id[:MAX_RULE_ID_LEN],
                    field=field_name[:MAX_FIELD_LEN],
                    match_count=match_count,
                    evidence_len=len(normalized),
                ))
        except re.error:
            # Fail-closed: treat regex error as forbidden
            matches.append(ForbiddenMatch(
                reason=ForbiddenReason.FORBIDDEN_INTERNAL_ERROR,
                matched_rule_id="REGEX_ERROR",
                field=field_name[:MAX_FIELD_LEN],
                match_count=1,
                evidence_len=len(normalized),
            ))
    
    return matches


# ============================================================================
# SIGNATURE COMPUTATION
# ============================================================================

def _compute_signature(matches: List[ForbiddenMatch]) -> str:
    """
    Compute deterministic signature from matches (structure-only, no raw text).
    """
    # Create structure-only data
    signature_data = {
        "match_count": len(matches),
        "reasons": {},
        "rule_ids": [],
        "fields": [],
        "total_evidence_len": 0,
    }
    
    # Aggregate by reason
    for match in matches:
        reason_key = match.reason.value
        if reason_key not in signature_data["reasons"]:
            signature_data["reasons"][reason_key] = 0
        signature_data["reasons"][reason_key] += match.match_count
        
        signature_data["rule_ids"].append(match.matched_rule_id)
        signature_data["fields"].append(match.field)
        signature_data["total_evidence_len"] += match.evidence_len
    
    # Sort for determinism
    signature_data["rule_ids"].sort()
    signature_data["fields"].sort()
    
    # Convert to canonical JSON
    json_str = json.dumps(signature_data, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    
    # Hash
    return sha256(json_str.encode('utf-8')).hexdigest()


# ============================================================================
# MAIN SCANNING FUNCTIONS
# ============================================================================

def scan_fact_forbidden(fact: MemoryFact) -> ForbiddenScanResult:
    """
    Scan a single fact for forbidden content.
    
    Returns ForbiddenScanResult with forbidden=True if any forbidden content detected.
    """
    try:
        all_matches = []
        
        # Scan key
        if fact.key:
            for patterns, reason in PATTERN_GROUPS:
                matches = _scan_text_for_patterns(fact.key, "key", patterns, reason)
                all_matches.extend(matches)
        
        # Scan value_str
        if fact.value_str:
            for patterns, reason in PATTERN_GROUPS:
                matches = _scan_text_for_patterns(fact.value_str, "value_str", patterns, reason)
                all_matches.extend(matches)
        
        # Scan value_list_str
        if fact.value_list_str:
            for i, item in enumerate(fact.value_list_str):
                normalized_item = _normalize_list_item(item)
                if normalized_item:
                    for patterns, reason in PATTERN_GROUPS:
                        matches = _scan_text_for_patterns(normalized_item, "value_str_list", patterns, reason)
                        all_matches.extend(matches)
        
        # Scan tags
        if fact.tags:
            for tag in fact.tags:
                if tag:
                    for patterns, reason in PATTERN_GROUPS:
                        matches = _scan_text_for_patterns(tag, "tags", patterns, reason)
                        all_matches.extend(matches)
        
        # Limit matches
        if len(all_matches) > MAX_MATCHES_RETURNED:
            # Sort by priority and take top matches
            all_matches.sort(key=lambda m: REASON_PRIORITY[m.reason])
            all_matches = all_matches[:MAX_MATCHES_RETURNED]
        
        # Determine top reason
        top_reason = None
        if all_matches:
            # Find highest priority reason
            top_priority = min(REASON_PRIORITY[match.reason] for match in all_matches)
            for match in all_matches:
                if REASON_PRIORITY[match.reason] == top_priority:
                    top_reason = match.reason
                    break
        
        # Compute signature
        signature = _compute_signature(all_matches)
        
        return ForbiddenScanResult(
            forbidden=len(all_matches) > 0,
            top_reason=top_reason,
            matches=all_matches,
            signature=signature,
        )
    
    except Exception:
        # Fail-closed: any exception means forbidden
        error_match = ForbiddenMatch(
            reason=ForbiddenReason.FORBIDDEN_INTERNAL_ERROR,
            matched_rule_id="SCAN_EXCEPTION",
            field="unknown",
            match_count=1,
            evidence_len=0,
        )
        return ForbiddenScanResult(
            forbidden=True,
            top_reason=ForbiddenReason.FORBIDDEN_INTERNAL_ERROR,
            matches=[error_match],
            signature=_compute_signature([error_match]),
        )


def scan_facts_forbidden(facts: List[MemoryFact]) -> ForbiddenScanResult:
    """
    Scan multiple facts for forbidden content.
    
    Returns forbidden=True if ANY fact triggers; returns top_reason based on priority.
    """
    try:
        all_matches = []
        
        # Scan each fact
        for fact in facts:
            result = scan_fact_forbidden(fact)
            if result.forbidden:
                all_matches.extend(result.matches)
        
        # Limit total matches
        if len(all_matches) > MAX_MATCHES_RETURNED:
            # Sort by priority and take top matches
            all_matches.sort(key=lambda m: REASON_PRIORITY[m.reason])
            all_matches = all_matches[:MAX_MATCHES_RETURNED]
        
        # Determine top reason
        top_reason = None
        if all_matches:
            # Find highest priority reason
            top_priority = min(REASON_PRIORITY[match.reason] for match in all_matches)
            for match in all_matches:
                if REASON_PRIORITY[match.reason] == top_priority:
                    top_reason = match.reason
                    break
        
        # Compute signature
        signature = _compute_signature(all_matches)
        
        return ForbiddenScanResult(
            forbidden=len(all_matches) > 0,
            top_reason=top_reason,
            matches=all_matches,
            signature=signature,
        )
    
    except Exception:
        # Fail-closed: any exception means forbidden
        error_match = ForbiddenMatch(
            reason=ForbiddenReason.FORBIDDEN_INTERNAL_ERROR,
            matched_rule_id="SCAN_EXCEPTION",
            field="unknown",
            match_count=1,
            evidence_len=0,
        )
        return ForbiddenScanResult(
            forbidden=True,
            top_reason=ForbiddenReason.FORBIDDEN_INTERNAL_ERROR,
            matches=[error_match],
            signature=_compute_signature([error_match]),
        )
