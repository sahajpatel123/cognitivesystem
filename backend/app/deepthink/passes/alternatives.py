"""
Phase 17 Step 6: Alternative Plan Generation Pass

Deterministic pass that generates 2-3 ranked alternatives and selects the best
based on stable scoring criteria.

Non-agentic, deterministic, patch-only, fail-closed.
"""

from typing import Dict, Any, List, Optional, Tuple
import hashlib
from dataclasses import dataclass
from backend.app.deepthink.engine import EngineContext, PassRunResult
from backend.app.deepthink.schema import (
    PatchOp,
    DecisionDelta,
    MAX_ANSWER_CHARS,
    MAX_RATIONALE_CHARS,
    MAX_CLARIFY_QUESTION_CHARS,
    MAX_ALTERNATIVE_CHARS,
    MAX_ALTERNATIVES_COUNT,
)


# Forbidden phrases in clarify questions (no tool/file requests)
FORBIDDEN_CLARIFY_PHRASES = [
    "upload",
    "attach",
    "run",
    "command",
    "terminal",
    "log",
    "credentials",
    "token",
    "api key",
    "screenshot",
    "execute",
    "shell",
    "script",
    "install",
]


# Absolute language patterns (increase risk)
ABSOLUTE_PATTERNS = [
    "guaranteed",
    "100%",
    "always",
    "never",
    "definitely",
    "certainly",
    "absolutely",
]


# Safety-critical domain keywords
SAFETY_CRITICAL_KEYWORDS = [
    "medical", "health", "symptom", "pain", "emergency",
    "legal", "law", "contract", "liability",
    "finance", "tax", "investment", "trading",
    "security", "vulnerability", "exploit", "breach",
]


# Ambiguity indicators
AMBIGUITY_KEYWORDS = [
    "best", "which", "near me", "latest", "recommend",
    "it depends", "unclear", "not sure",
]


@dataclass
class Candidate:
    """A candidate alternative decision."""
    action: str
    answer: str
    rationale: str
    clarify_question: str
    risk_score: int
    clarity_score: int
    cost_score: int
    tie_break_hash: str
    
    def canonical_string(self) -> str:
        """Generate canonical string for hashing."""
        # Normalize whitespace
        action_norm = self.action.strip()
        answer_norm = " ".join(self.answer.split())
        rationale_norm = " ".join(self.rationale.split())
        clarify_norm = " ".join(self.clarify_question.split())
        
        return f"{action_norm}|{answer_norm}|{rationale_norm}|{clarify_norm}"
    
    def sort_key(self) -> Tuple[int, int, int, str]:
        """Return stable sort key: (risk ASC, clarity DESC, cost ASC, tie_break ASC)."""
        return (self.risk_score, -self.clarity_score, self.cost_score, self.tie_break_hash)


def run_alternatives_pass(
    pass_type: str,
    state: Dict[str, Any],
    context: EngineContext,
) -> PassRunResult:
    """
    Run alternatives pass on decision state.
    
    Generates 2-3 ranked alternatives and selects the best based on
    deterministic scoring.
    
    Args:
        pass_type: Pass type identifier (should be "ALTERNATIVES")
        state: Current decision state
        context: Engine context
    
    Returns:
        PassRunResult with delta ops, cost, duration
    
    Guarantees:
        - Deterministic: same inputs -> same outputs
        - Non-agentic: no external calls
        - Patch-only: returns DecisionDelta
        - Fail-closed: errors return empty delta with error message
    """
    # Extract decision from state
    decision = state.get("decision", {})
    
    # Validate decision structure
    if not isinstance(decision, dict):
        return PassRunResult(
            pass_type=pass_type,
            delta=None,
            cost_units=10,
            duration_ms=50,
            error="Invalid decision structure",
        )
    
    # Extract current decision fields
    current_action = decision.get("action", "")
    current_answer = decision.get("answer", "")
    current_rationale = decision.get("rationale", "")
    current_clarify = decision.get("clarify_question", "")
    
    # Extract request text for context
    request_text = _extract_request_text(state, context)
    
    # Generate candidate alternatives
    candidates = _generate_candidates(
        current_action,
        current_answer,
        current_rationale,
        current_clarify,
        request_text,
    )
    
    # Score candidates
    scored_candidates = []
    for candidate in candidates:
        risk = _compute_risk_score(candidate, request_text)
        clarity = _compute_clarity_score(candidate)
        cost = _compute_cost_score(candidate)
        tie_break = _compute_tie_break_hash(candidate.canonical_string())
        
        candidate.risk_score = risk
        candidate.clarity_score = clarity
        candidate.cost_score = cost
        candidate.tie_break_hash = tie_break
        
        scored_candidates.append(candidate)
    
    # Sort by stable key
    scored_candidates.sort(key=lambda c: c.sort_key())
    
    # Select top 2-3 distinct candidates
    distinct_candidates = _select_distinct_candidates(scored_candidates, max_count=3)
    
    # Ensure we have 2-3 candidates
    if len(distinct_candidates) < 2:
        # Fallback: add a safe FALLBACK candidate
        fallback = Candidate(
            action="FALLBACK",
            answer="",
            rationale="Insufficient information for safe response.",
            clarify_question="",
            risk_score=0,
            clarity_score=50,
            cost_score=0,
            tie_break_hash="",
        )
        distinct_candidates.append(fallback)
    
    # Take top 2-3
    final_candidates = distinct_candidates[:3]
    
    # Choose best (first after sorting)
    best_candidate = final_candidates[0]
    
    # Generate delta ops to transform to best candidate
    ops: List[PatchOp] = []
    
    if best_candidate.action != current_action:
        ops.append(PatchOp(op="set", path="decision.action", value=best_candidate.action))
    
    if best_candidate.answer != current_answer:
        bounded_answer = best_candidate.answer[:MAX_ANSWER_CHARS]
        ops.append(PatchOp(op="set", path="decision.answer", value=bounded_answer))
    
    if best_candidate.rationale != current_rationale:
        bounded_rationale = best_candidate.rationale[:MAX_RATIONALE_CHARS]
        ops.append(PatchOp(op="set", path="decision.rationale", value=bounded_rationale))
    
    if best_candidate.clarify_question != current_clarify:
        bounded_clarify = best_candidate.clarify_question[:MAX_CLARIFY_QUESTION_CHARS]
        ops.append(PatchOp(op="set", path="decision.clarify_question", value=bounded_clarify))
    
    # Optionally add alternatives summary
    alternatives_summary = _generate_alternatives_summary(final_candidates)
    if alternatives_summary:
        ops.append(PatchOp(op="set", path="decision.alternatives", value=alternatives_summary))
    
    # Sort ops by path for deterministic ordering
    ops.sort(key=lambda op: op.path)
    
    # Compute deterministic cost and duration
    cost_units = _compute_pass_cost(request_text, len(final_candidates))
    duration_ms = _compute_pass_duration(request_text, len(final_candidates))
    
    return PassRunResult(
        pass_type=pass_type,
        delta=ops,
        cost_units=cost_units,
        duration_ms=duration_ms,
        error=None,
    )


def _extract_request_text(state: Dict[str, Any], context: EngineContext) -> str:
    """Extract request text from state or context."""
    # Try state.request_text
    request_text = state.get('request_text', '')
    if request_text:
        return request_text
    
    # Try decision fields as fallback
    decision = state.get('decision', {})
    answer = decision.get('answer', '')
    rationale = decision.get('rationale', '')
    clarify = decision.get('clarify_question', '')
    
    combined = f"{answer} {rationale} {clarify}".strip()
    return combined


def _generate_candidates(
    current_action: str,
    current_answer: str,
    current_rationale: str,
    current_clarify: str,
    request_text: str,
) -> List[Candidate]:
    """
    Generate candidate alternatives in fixed order.
    
    Always generates candidates in deterministic order:
    1. Stay the course (current action, tightened)
    2. Clarify-first (ASK_CLARIFY)
    3. Fallback-safe (FALLBACK)
    """
    candidates = []
    
    # Candidate 1: Stay the course (tighten current)
    stay_answer = current_answer if current_answer else "Proceeding with current approach."
    stay_rationale = _tighten_rationale(current_rationale, current_answer)
    
    candidates.append(Candidate(
        action=current_action if current_action else "ANSWER",
        answer=stay_answer,
        rationale=stay_rationale,
        clarify_question=current_clarify,
        risk_score=0,
        clarity_score=0,
        cost_score=0,
        tie_break_hash="",
    ))
    
    # Candidate 2: Clarify-first
    if current_action != "ASK_CLARIFY":
        clarify_q = _generate_safe_clarify_question(request_text, current_answer)
        clarify_rationale = "Additional clarification needed to ensure accuracy."
        
        candidates.append(Candidate(
            action="ASK_CLARIFY",
            answer="",
            rationale=clarify_rationale,
            clarify_question=clarify_q,
            risk_score=0,
            clarity_score=0,
            cost_score=0,
            tie_break_hash="",
        ))
    else:
        # Already ASK_CLARIFY, refine question
        refined_q = _refine_clarify_question(current_clarify)
        
        candidates.append(Candidate(
            action="ASK_CLARIFY",
            answer="",
            rationale="Refining clarification request for precision.",
            clarify_question=refined_q,
            risk_score=0,
            clarity_score=0,
            cost_score=0,
            tie_break_hash="",
        ))
    
    # Candidate 3: Fallback-safe
    candidates.append(Candidate(
        action="FALLBACK",
        answer="",
        rationale="Conservative fallback to ensure safety.",
        clarify_question="",
        risk_score=0,
        clarity_score=0,
        cost_score=0,
        tie_break_hash="",
    ))
    
    return candidates


def _tighten_rationale(rationale: str, answer: str) -> str:
    """Tighten rationale by adding caveats."""
    if not rationale:
        return "This approach assumes typical conditions and may vary based on context."
    
    # Add caveat if not present
    if "assuming" not in rationale.lower() and "based on" not in rationale.lower():
        tightened = f"{rationale.strip()} This assumes standard conditions."
    else:
        tightened = rationale
    
    return tightened[:MAX_RATIONALE_CHARS]


def _generate_safe_clarify_question(request_text: str, answer: str) -> str:
    """Generate safe clarify question."""
    # Check for ambiguity
    request_lower = request_text.lower()
    
    if any(kw in request_lower for kw in ["best", "recommend", "which"]):
        question = "Could you specify your specific requirements or constraints?"
    elif "near me" in request_lower:
        question = "Could you specify your location or city?"
    elif len(answer) < 20:
        question = "Could you provide more context about your goal?"
    else:
        question = "Could you clarify which specific aspect you're asking about?"
    
    # Ensure no forbidden phrases
    question = _sanitize_clarify_question(question)
    
    return question[:MAX_CLARIFY_QUESTION_CHARS]


def _refine_clarify_question(current_clarify: str) -> str:
    """Refine existing clarify question."""
    if not current_clarify:
        return "Could you provide more specific details?"
    
    # Simplify and shorten
    refined = current_clarify.strip()
    if len(refined) > 200:
        refined = refined[:197] + "..."
    
    # Ensure no forbidden phrases
    refined = _sanitize_clarify_question(refined)
    
    return refined[:MAX_CLARIFY_QUESTION_CHARS]


def _sanitize_clarify_question(question: str) -> str:
    """Remove forbidden phrases from clarify question."""
    question_lower = question.lower()
    for forbidden in FORBIDDEN_CLARIFY_PHRASES:
        if forbidden in question_lower:
            # Replace with generic safe question
            return "Could you provide more details about your request?"
    return question


def _compute_risk_score(candidate: Candidate, request_text: str) -> int:
    """
    Compute risk score (0-100, higher = riskier).
    
    Increases risk when:
    - Action is ANSWER with absolute language
    - Domain is safety-critical
    - Clarify question missing but request ambiguous
    """
    risk = 0
    
    # Check for ANSWER with absolute language
    if candidate.action == "ANSWER":
        answer_lower = candidate.answer.lower()
        for pattern in ABSOLUTE_PATTERNS:
            if pattern in answer_lower:
                risk += 15
        
        # Check if answer is very short (risky if insufficient)
        if len(candidate.answer) < 30:
            risk += 10
    
    # Check for safety-critical domain
    request_lower = request_text.lower()
    for keyword in SAFETY_CRITICAL_KEYWORDS:
        if keyword in request_lower:
            risk += 20
            break
    
    # Check for missing clarify when ambiguous
    if candidate.action == "ANSWER" and not candidate.clarify_question:
        for keyword in AMBIGUITY_KEYWORDS:
            if keyword in request_lower:
                risk += 15
                break
    
    # ASK_CLARIFY and FALLBACK are lower risk
    if candidate.action == "ASK_CLARIFY":
        risk = max(0, risk - 20)
    elif candidate.action == "FALLBACK":
        risk = max(0, risk - 30)
    
    return min(risk, 100)


def _compute_clarity_score(candidate: Candidate) -> int:
    """
    Compute clarity score (0-100, higher = clearer).
    
    ASK_CLARIFY with good questions scores high.
    ANSWER scores lower if too hedged or empty.
    """
    clarity = 50  # Base
    
    if candidate.action == "ASK_CLARIFY":
        # Good clarify question increases clarity
        if candidate.clarify_question and len(candidate.clarify_question) > 20:
            clarity += 30
        else:
            clarity += 10
    
    elif candidate.action == "ANSWER":
        # Good answer increases clarity
        if candidate.answer and len(candidate.answer) > 50:
            clarity += 20
        else:
            clarity -= 10
        
        # Too much hedging decreases clarity
        hedge_words = ["maybe", "might", "could", "possibly", "perhaps"]
        answer_lower = candidate.answer.lower()
        hedge_count = sum(1 for word in hedge_words if word in answer_lower)
        clarity -= hedge_count * 5
    
    elif candidate.action == "FALLBACK":
        clarity -= 20
    
    return max(0, min(clarity, 100))


def _compute_cost_score(candidate: Candidate) -> int:
    """
    Compute cost score (0-100, higher = more user effort).
    
    ASK_CLARIFY costs user effort.
    REFUSE has low cost but may reduce usefulness.
    """
    cost = 0
    
    if candidate.action == "ASK_CLARIFY":
        cost = 40  # Moderate user effort
    elif candidate.action == "ANSWER":
        cost = 10  # Low user effort
    elif candidate.action == "REFUSE":
        cost = 5  # Very low user effort
    elif candidate.action == "FALLBACK":
        cost = 20  # Some user effort to rephrase
    
    return cost


def _compute_tie_break_hash(canonical_string: str) -> str:
    """
    Compute deterministic tie-break hash.
    
    Returns first 12 hex chars of SHA256.
    """
    hash_obj = hashlib.sha256(canonical_string.encode('utf-8'))
    hex_digest = hash_obj.hexdigest()
    return hex_digest[:12]


def _select_distinct_candidates(candidates: List[Candidate], max_count: int) -> List[Candidate]:
    """
    Select distinct candidates (by canonical string).
    
    Returns up to max_count distinct candidates.
    """
    seen_canonical = set()
    distinct = []
    
    for candidate in candidates:
        canonical = candidate.canonical_string()
        if canonical not in seen_canonical:
            seen_canonical.add(canonical)
            distinct.append(candidate)
            if len(distinct) >= max_count:
                break
    
    return distinct


def _generate_alternatives_summary(candidates: List[Candidate]) -> List[str]:
    """
    Generate bounded summary of alternatives.
    
    Returns list of 2-3 short strings (max 200 chars each).
    """
    summaries = []
    
    for candidate in candidates[:MAX_ALTERNATIVES_COUNT]:
        if candidate.action == "ANSWER":
            summary = f"ANSWER: {candidate.answer[:150]}"
        elif candidate.action == "ASK_CLARIFY":
            summary = f"ASK_CLARIFY: {candidate.clarify_question[:150]}"
        elif candidate.action == "FALLBACK":
            summary = "FALLBACK: Conservative safe response"
        elif candidate.action == "REFUSE":
            summary = "REFUSE: Cannot safely answer"
        else:
            summary = f"{candidate.action}: {candidate.rationale[:150]}"
        
        # Ensure within bounds
        summary = summary[:MAX_ALTERNATIVE_CHARS]
        summaries.append(summary)
    
    return summaries


def _compute_pass_cost(request_text: str, candidate_count: int) -> int:
    """Compute deterministic cost for pass execution."""
    base_cost = 30
    text_cost = len(request_text) // 100
    candidate_cost = candidate_count * 10
    
    total_cost = base_cost + text_cost + candidate_cost
    
    return min(total_cost, 200)


def _compute_pass_duration(request_text: str, candidate_count: int) -> int:
    """Compute deterministic duration for pass execution."""
    base_duration = 150
    text_duration = len(request_text) // 50
    candidate_duration = candidate_count * 20
    
    total_duration = base_duration + text_duration + candidate_duration
    
    return min(total_duration, 700)
