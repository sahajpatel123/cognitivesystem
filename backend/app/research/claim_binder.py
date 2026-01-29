"""
Phase 18 Step 4: Claim-to-Citation Binder

Mechanical enforcement of "no source → unknown".
Extracts claims, binds to citations, enforces coverage gate.
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Union


MAX_CLAIMS = 12
MAX_CLAIM_LENGTH = 200
MAX_CITATIONS_PER_CLAIM = 3
MAX_UNCOVERED_IDS = 5
MAX_CLARIFY_QUESTIONS = 3
MAX_CLARIFY_QUESTION_LENGTH = 160
MAX_TOKENS_PER_CLAIM = 12


STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "about", "into", "through", "during",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "should", "could", "may", "might",
    "can", "this", "that", "these", "those", "i", "you", "he", "she", "it",
    "we", "they", "them", "their", "there", "here", "over",
}


FACTUAL_VERBS = {
    "is", "are", "was", "were", "causes", "leads", "results", "illegal",
    "required", "prohibited", "mandates", "requires", "enforces",
}


CLARIFIABLE_WORDS = {
    "which", "what", "where", "when", "version", "error", "environment",
    "location", "why", "how",
}


PRONOUN_STARTS = {
    "it", "this", "that", "these", "those", "they", "them",
}


@dataclass(frozen=True)
class Claim:
    """
    Atomic claim extracted from answer text.
    """
    claim_id: str
    text: str
    kind: str
    required: bool
    confidence: str


@dataclass
class BinderOutput:
    """
    Output of claim-to-citation binding with coverage enforcement.
    """
    final_mode: str
    claims: List[Claim]
    bindings: Dict[str, list]
    uncovered_required_claim_ids: List[str]
    clarify_questions: List[str]


def canonicalize_text(text: str) -> str:
    """
    Canonicalize text for deduplication.
    
    Args:
        text: Raw text
    
    Returns:
        Canonical form (casefold + collapsed spaces)
    """
    text = text.strip().casefold()
    text = re.sub(r'\s+', ' ', text)
    return text


def compute_claim_id(text: str) -> str:
    """
    Compute stable claim ID from canonical text.
    
    Args:
        text: Claim text
    
    Returns:
        12-char hex hash
    """
    canonical = canonicalize_text(text)
    hash_digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    return hash_digest[:12]


def extract_sentences(text: str) -> List[str]:
    """
    Extract sentence candidates deterministically.
    
    Args:
        text: Raw answer text
    
    Returns:
        List of sentence candidates
    """
    sentences = []
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        
        if re.match(r'^[-*•]\s+', line):
            bullet_text = re.sub(r'^[-*•]\s+', '', line).strip()
            if bullet_text:
                sentences.append(bullet_text)
        else:
            parts = re.split(r'([.!?]+)', line)
            
            current = ""
            for i, part in enumerate(parts):
                if re.match(r'^[.!?]+$', part):
                    current += part
                    if current.strip():
                        sentences.append(current.strip())
                    current = ""
                else:
                    current += part
            
            if current.strip():
                sentences.append(current.strip())
    
    return sentences


def is_required_claim(text: str) -> bool:
    """
    Determine if claim is required using heuristics.
    
    Args:
        text: Claim text
    
    Returns:
        True if required
    """
    text_lower = text.lower()
    
    if re.search(r'\d', text):
        return True
    
    if re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b', text_lower):
        return True
    
    if re.search(r'\b\d{4}\b', text):
        return True
    
    for verb in FACTUAL_VERBS:
        if f' {verb} ' in f' {text_lower} ':
            return True
    
    if re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text):
        return True
    
    if 'according to' in text_lower:
        return True
    
    if re.search(r'https?://|www\.', text_lower):
        return True
    
    if text.endswith("?") and any(word in text_lower for word in CLARIFIABLE_WORDS):
        return True
    
    return False


def classify_claim_kind(text: str) -> str:
    """
    Classify claim kind deterministically.
    
    Args:
        text: Claim text
    
    Returns:
        Kind: FACT, STAT, QUOTE, RECOMMENDATION
    """
    text_lower = text.lower()
    
    if '"' in text or "'" in text or 'said' in text_lower or 'states' in text_lower:
        return "QUOTE"
    
    if re.search(r'\d+%|\d+\.\d+|\d+,\d+|\$\d+', text):
        return "STAT"
    
    if any(word in text_lower for word in ['should', 'must', 'recommend', 'suggest', 'advise', 'consider']):
        return "RECOMMENDATION"
    
    return "FACT"


def assess_confidence(text: str, required: bool) -> str:
    """
    Assess claim confidence deterministically.
    
    Args:
        text: Claim text
        required: Whether claim is required
    
    Returns:
        Confidence: HIGH, MED, LOW
    """
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['may', 'might', 'possibly', 'perhaps', 'unclear', 'uncertain']):
        return "LOW"
    
    if required and re.search(r'\d', text):
        return "HIGH"
    
    if any(word in text_lower for word in ['always', 'never', 'definitely', 'certainly', 'proven']):
        return "HIGH"
    
    return "MED"


def extract_claims(text: str) -> List[Claim]:
    """
    Extract atomic claims from answer text.
    
    Args:
        text: Answer text
    
    Returns:
        List of claims (bounded, deduplicated, stable-sorted)
    """
    if not text or not text.strip():
        return []
    
    sentences = extract_sentences(text)
    
    candidates = []
    seen_canonical = set()
    
    for sentence in sentences:
        if len(sentence) < 8:
            continue
        
        bounded_text = sentence[:MAX_CLAIM_LENGTH]
        canonical = canonicalize_text(bounded_text)
        
        if canonical in seen_canonical:
            continue
        
        seen_canonical.add(canonical)
        
        claim_id = compute_claim_id(bounded_text)
        required = is_required_claim(bounded_text)
        kind = classify_claim_kind(bounded_text)
        confidence = assess_confidence(bounded_text, required)
        
        claim = Claim(
            claim_id=claim_id,
            text=bounded_text,
            kind=kind,
            required=required,
            confidence=confidence,
        )
        candidates.append(claim)
    
    required_claims = [c for c in candidates if c.required]
    non_required_claims = [c for c in candidates if not c.required]
    
    sorted_claims = required_claims + non_required_claims
    
    return sorted_claims[:MAX_CLAIMS]


def tokenize_text(text: str) -> List[str]:
    """
    Tokenize text for claim-citation matching.
    
    Args:
        text: Text to tokenize
    
    Returns:
        List of tokens (lowercase, alnum, no stopwords)
    """
    text = text.lower()
    tokens = re.findall(r'\b[a-z0-9]+\b', text)
    tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 2]
    return tokens[:MAX_TOKENS_PER_CLAIM]


def compute_overlap_score(claim_tokens: List[str], snippet_tokens: List[str]) -> int:
    """
    Compute token overlap score.
    
    Args:
        claim_tokens: Claim tokens
        snippet_tokens: Snippet tokens
    
    Returns:
        Overlap count (0-12)
    """
    claim_set = set(claim_tokens)
    snippet_set = set(snippet_tokens)
    return len(claim_set & snippet_set)


def compute_tie_break_hash(claim_id: str, source_id: str, snippet_index: int) -> str:
    """
    Compute deterministic tie-breaker hash.
    
    Args:
        claim_id: Claim ID
        source_id: Source ID
        snippet_index: Snippet index
    
    Returns:
        8-char hex hash
    """
    material = f"{claim_id}|{source_id}|{snippet_index}"
    hash_digest = hashlib.sha256(material.encode('utf-8')).hexdigest()
    return hash_digest[:8]


def bind_claims_to_sources(claims: List[Claim], sources: list) -> Dict[str, list]:
    """
    Bind claims to citations using token overlap.
    
    Args:
        claims: List of claims
        sources: List of SourceBundle or GradedSource
    
    Returns:
        Dict mapping claim_id -> list of CitationRef
    """
    from backend.app.research.citations import make_citation_ref, GRADE_TO_SCORE
    
    bindings = {}
    
    for claim in claims:
        claim_tokens = tokenize_text(claim.text)
        
        candidates = []
        
        for source in sources:
            if hasattr(source, 'source'):
                bundle = source.source
                credibility = getattr(source, 'credibility', None)
            else:
                bundle = source
                credibility = None
            
            credibility_score = 0
            if credibility:
                credibility_score = getattr(credibility, 'score', 0)
                if credibility_score is None:
                    grade = getattr(credibility, 'grade', 'UNKNOWN')
                    credibility_score = GRADE_TO_SCORE.get(grade, 0)
            
            published_date = None
            if hasattr(bundle, 'metadata') and bundle.metadata:
                for date_field in ['published_at', 'date', 'updated_at']:
                    if date_field in bundle.metadata:
                        published_date = bundle.metadata[date_field]
                        break
            
            domain_lower = bundle.domain.lower()
            
            for idx, snippet in enumerate(bundle.snippets):
                snippet_tokens = tokenize_text(snippet.text)
                overlap_score = compute_overlap_score(claim_tokens, snippet_tokens)
                
                domain_match = any(token in domain_lower for token in claim_tokens)
                
                if overlap_score >= 2 or domain_match:
                    tie_break = compute_tie_break_hash(claim.claim_id, bundle.source_id, idx)
                    
                    citation_ref = make_citation_ref(
                        source_id=bundle.source_id,
                        url=bundle.url,
                        domain=bundle.domain,
                        title=bundle.title,
                        snippet_index=idx,
                        snippet_len=len(snippet.text),
                        published_date=published_date,
                        credibility_report=credibility,
                    )
                    
                    freshness_proxy = 1 if published_date else 0
                    
                    candidates.append((
                        credibility_score,
                        overlap_score,
                        freshness_proxy,
                        bundle.domain,
                        bundle.url,
                        idx,
                        tie_break,
                        citation_ref,
                    ))
        
        candidates.sort(key=lambda x: (-x[0], -x[1], -x[2], x[3], x[4], x[5], x[6]))
        
        seen_keys = set()
        selected_citations = []
        
        for candidate in candidates:
            citation_ref = candidate[7]
            key = (citation_ref.source_id, citation_ref.snippet_index)
            
            if key not in seen_keys:
                selected_citations.append(citation_ref)
                seen_keys.add(key)
            
            if len(selected_citations) >= MAX_CITATIONS_PER_CLAIM:
                break
        
        bindings[claim.claim_id] = selected_citations
    
    return bindings


def is_clarifiable_claim(claim: Claim) -> bool:
    """
    Check if uncovered claim is clarifiable.
    
    Args:
        claim: Claim object
    
    Returns:
        True if clarifiable
    """
    text_lower = claim.text.lower()
    
    if claim.text.endswith("?"):
        return True
    
    if len(claim.text) < 120:
        if any(word in text_lower for word in CLARIFIABLE_WORDS):
            return True
        
        first_word = claim.text.split()[0].lower() if claim.text.split() else ""
        if first_word in PRONOUN_STARTS:
            return True
    
    return False


def generate_clarify_question(claim: Claim) -> str:
    """
    Generate clarification question for uncovered claim.
    
    Args:
        claim: Claim object
    
    Returns:
        Clarification question (bounded)
    """
    question = f"Could you clarify: {claim.text}"
    
    if not question.endswith("?"):
        question += "?"
    
    return question[:MAX_CLARIFY_QUESTION_LENGTH]


def enforce_coverage(claims: List[Claim], bindings: Dict[str, list]) -> Tuple[str, List[str], List[str]]:
    """
    Enforce coverage gate: required claims must have citations.
    
    Args:
        claims: List of claims
        bindings: Claim ID to citations mapping
    
    Returns:
        Tuple of (final_mode, uncovered_ids, clarify_questions)
    """
    uncovered_required = []
    clarifiable_claims = []
    
    for claim in claims:
        if claim.required:
            citations = bindings.get(claim.claim_id, [])
            if not citations:
                uncovered_required.append(claim.claim_id)
                
                if is_clarifiable_claim(claim):
                    clarifiable_claims.append(claim)
    
    if not uncovered_required:
        return ("OK", [], [])
    
    uncovered_ids = uncovered_required[:MAX_UNCOVERED_IDS]
    
    if clarifiable_claims:
        clarify_questions = [
            generate_clarify_question(claim)
            for claim in clarifiable_claims[:MAX_CLARIFY_QUESTIONS]
        ]
        return ("ASK_CLARIFY", uncovered_ids, clarify_questions)
    else:
        return ("UNKNOWN", uncovered_ids, [])


def bind_claims_and_citations(
    answer_text: str,
    sources: list,
    citations_required: bool = True,
) -> BinderOutput:
    """
    Single entrypoint: extract claims, bind to sources, enforce coverage.
    
    Args:
        answer_text: Answer text to extract claims from
        sources: List of SourceBundle or GradedSource
        citations_required: Whether to enforce coverage gate
    
    Returns:
        BinderOutput with final_mode, claims, bindings, uncovered IDs, clarify questions
    """
    try:
        if not answer_text or not answer_text.strip():
            return BinderOutput(
                final_mode="UNKNOWN",
                claims=[],
                bindings={},
                uncovered_required_claim_ids=[],
                clarify_questions=["Could you provide more details?"],
            )
        
        claims = extract_claims(answer_text)
        
        if not claims:
            return BinderOutput(
                final_mode="UNKNOWN",
                claims=[],
                bindings={},
                uncovered_required_claim_ids=[],
                clarify_questions=[],
            )
        
        if not sources and citations_required:
            required_claim_ids = [c.claim_id for c in claims if c.required]
            
            if required_claim_ids:
                clarifiable = [c for c in claims if c.required and is_clarifiable_claim(c)]
                
                if clarifiable:
                    clarify_questions = [
                        generate_clarify_question(c)
                        for c in clarifiable[:MAX_CLARIFY_QUESTIONS]
                    ]
                    return BinderOutput(
                        final_mode="ASK_CLARIFY",
                        claims=claims,
                        bindings={},
                        uncovered_required_claim_ids=required_claim_ids[:MAX_UNCOVERED_IDS],
                        clarify_questions=clarify_questions,
                    )
                else:
                    return BinderOutput(
                        final_mode="UNKNOWN",
                        claims=claims,
                        bindings={},
                        uncovered_required_claim_ids=required_claim_ids[:MAX_UNCOVERED_IDS],
                        clarify_questions=[],
                    )
        
        bindings = bind_claims_to_sources(claims, sources)
        
        if citations_required:
            final_mode, uncovered_ids, clarify_questions = enforce_coverage(claims, bindings)
        else:
            final_mode = "OK"
            uncovered_ids = []
            clarify_questions = []
        
        return BinderOutput(
            final_mode=final_mode,
            claims=claims,
            bindings=bindings,
            uncovered_required_claim_ids=uncovered_ids,
            clarify_questions=clarify_questions,
        )
    
    except Exception:
        return BinderOutput(
            final_mode="UNKNOWN",
            claims=[],
            bindings={},
            uncovered_required_claim_ids=[],
            clarify_questions=[],
        )
