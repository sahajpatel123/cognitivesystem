"""
Phase 17 Step 4: Counterargument Pass

Deterministic pass that downgrades certainty, tightens rationale, and converts
ANSWER to ASK_CLARIFY when critical missing input is detected.

Non-agentic, deterministic, patch-only, fail-closed.
"""

from typing import Dict, Any, List, Optional
from backend.app.deepthink.engine import EngineContext, PassRunResult
from backend.app.deepthink.schema import PatchOp, DecisionDelta, MAX_ANSWER_CHARS, MAX_RATIONALE_CHARS, MAX_CLARIFY_QUESTION_CHARS


# Risky patterns that indicate overconfidence
ABSOLUTE_CLAIM_PATTERNS = [
    "definitely",
    "guaranteed",
    "100%",
    "always",
    "never",
    "certainly",
    "absolutely",
    "without doubt",
    "no question",
    "for sure",
]

# Ambiguity indicators
AMBIGUITY_PATTERNS = [
    "it depends",
    "depends on",
    "unclear",
    "ambiguous",
    "not sure",
    "might be",
    "could be",
]

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


def run_counterargument_pass(
    pass_type: str,
    state: Dict[str, Any],
    context: EngineContext,
) -> PassRunResult:
    """
    Run counterargument pass on decision state.
    
    Args:
        pass_type: Pass type identifier (should be "COUNTERARG")
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
    
    # Extract fields
    action = decision.get("action", "")
    answer = decision.get("answer", "")
    rationale = decision.get("rationale", "")
    clarify_question = decision.get("clarify_question", "")
    
    # Generate delta ops
    ops: List[PatchOp] = []
    
    # Check if critical missing input exists
    needs_clarification = _check_needs_clarification(action, answer, rationale)
    
    if needs_clarification and action == "ANSWER":
        # Convert ANSWER to ASK_CLARIFY
        ops.append(PatchOp(op="set", path="decision.action", value="ASK_CLARIFY"))
        
        # Generate clarify question
        clarify_q = _generate_clarify_question(answer, rationale, clarify_question)
        if clarify_q:
            ops.append(PatchOp(op="set", path="decision.clarify_question", value=clarify_q))
        
        # Tighten rationale to explain why clarification is needed
        tightened_rationale = _tighten_rationale_for_clarification(rationale)
        if tightened_rationale and tightened_rationale != rationale:
            ops.append(PatchOp(op="set", path="decision.rationale", value=tightened_rationale))
    
    elif action == "ANSWER":
        # Tighten rationale by removing overconfidence
        tightened_rationale = _tighten_rationale(rationale, answer)
        if tightened_rationale and tightened_rationale != rationale:
            ops.append(PatchOp(op="set", path="decision.rationale", value=tightened_rationale))
        
        # Optionally soften answer by removing absolutes
        softened_answer = _soften_answer(answer)
        if softened_answer and softened_answer != answer:
            ops.append(PatchOp(op="set", path="decision.answer", value=softened_answer))
    
    elif action in ("ASK_CLARIFY", "REFUSE", "FALLBACK"):
        # Only allow rationale tightening for non-ANSWER actions
        tightened_rationale = _tighten_rationale(rationale, answer)
        if tightened_rationale and tightened_rationale != rationale:
            ops.append(PatchOp(op="set", path="decision.rationale", value=tightened_rationale))
    
    # Sort ops by path for deterministic ordering
    ops.sort(key=lambda op: op.path)
    
    # Compute deterministic cost and duration
    cost_units = _compute_cost(answer, rationale)
    duration_ms = _compute_duration(answer, rationale)
    
    return PassRunResult(
        pass_type=pass_type,
        delta=ops,
        cost_units=cost_units,
        duration_ms=duration_ms,
        error=None,
    )


def _check_needs_clarification(action: str, answer: str, rationale: str) -> bool:
    """
    Check if decision needs clarification.
    
    Returns True if:
    - Answer is empty or very short
    - Rationale is empty
    - Answer contains ambiguity without specifics
    """
    if not answer or len(answer.strip()) < 10:
        return True
    
    if not rationale or len(rationale.strip()) < 10:
        return True
    
    # Check for ambiguity patterns without specifics
    answer_lower = answer.lower()
    for pattern in AMBIGUITY_PATTERNS:
        if pattern in answer_lower:
            # If "depends on" is present but no specifics follow, needs clarification
            if pattern == "depends on" or pattern == "it depends":
                return True
    
    return False


def _generate_clarify_question(answer: str, rationale: str, existing_clarify: str) -> Optional[str]:
    """
    Generate a bounded clarify question.
    
    Must NOT request files/tools/uploads/commands.
    Must be ONE question, bounded, within schema limit.
    """
    # If existing clarify question is present and safe, reuse it (shortened if needed)
    if existing_clarify:
        safe_clarify = _sanitize_clarify_question(existing_clarify)
        if safe_clarify:
            return safe_clarify[:MAX_CLARIFY_QUESTION_CHARS]
    
    # Generate generic clarification request based on missing info
    if not answer or len(answer.strip()) < 10:
        question = "Could you clarify what specific information or outcome you're looking for?"
    elif not rationale or len(rationale.strip()) < 10:
        question = "Could you provide more context about your goal or requirements?"
    else:
        question = "Could you specify which option or scenario you're referring to?"
    
    # Ensure within bounds
    return question[:MAX_CLARIFY_QUESTION_CHARS]


def _sanitize_clarify_question(question: str) -> Optional[str]:
    """
    Sanitize clarify question by removing forbidden phrases.
    
    Returns None if question contains forbidden phrases.
    """
    question_lower = question.lower()
    for forbidden in FORBIDDEN_CLARIFY_PHRASES:
        if forbidden in question_lower:
            return None
    return question


def _tighten_rationale_for_clarification(rationale: str) -> str:
    """
    Tighten rationale to explain why clarification is needed.
    """
    if not rationale:
        return "Additional information is needed to provide a complete answer."
    
    # Add clarification note if not present
    if "clarification" not in rationale.lower() and "more information" not in rationale.lower():
        tightened = f"{rationale.strip()} Additional clarification is needed to ensure accuracy."
    else:
        tightened = rationale
    
    # Ensure within bounds
    return tightened[:MAX_RATIONALE_CHARS]


def _tighten_rationale(rationale: str, answer: str) -> str:
    """
    Tighten rationale by adding explicit assumptions and caveats.
    
    Removes overclaims, adds bounded caveats.
    """
    if not rationale:
        return rationale
    
    tightened = rationale
    
    # Check for absolute claims and add caveats
    rationale_lower = rationale.lower()
    has_absolute = any(pattern in rationale_lower for pattern in ABSOLUTE_CLAIM_PATTERNS)
    
    if has_absolute:
        # Add caveat about assumptions
        if "assuming" not in rationale_lower and "based on" not in rationale_lower:
            tightened = f"{tightened.strip()} This assumes typical conditions and may vary based on specific context."
    
    # Ensure within bounds
    return tightened[:MAX_RATIONALE_CHARS]


def _soften_answer(answer: str) -> str:
    """
    Soften answer by removing absolute claims.
    
    Replaces absolutes with qualified language.
    """
    if not answer:
        return answer
    
    softened = answer
    
    # Replace absolute patterns with softer alternatives
    replacements = {
        "definitely": "likely",
        "guaranteed": "expected",
        "100%": "highly probable",
        "always": "typically",
        "never": "rarely",
        "certainly": "probably",
        "absolutely": "generally",
        "without doubt": "with high confidence",
        "no question": "most likely",
        "for sure": "very likely",
    }
    
    for absolute, softer in replacements.items():
        # Case-insensitive replacement
        if absolute in softened.lower():
            # Find and replace preserving case
            import re
            pattern = re.compile(re.escape(absolute), re.IGNORECASE)
            softened = pattern.sub(softer, softened, count=1)  # Only replace first occurrence
    
    # Ensure within bounds
    return softened[:MAX_ANSWER_CHARS]


def _compute_cost(answer: str, rationale: str) -> int:
    """
    Compute deterministic cost based on input sizes.
    
    Returns cost units (capped).
    """
    answer_len = len(answer) if answer else 0
    rationale_len = len(rationale) if rationale else 0
    
    # Base cost + proportional to text length
    base_cost = 20
    text_cost = (answer_len + rationale_len) // 50
    
    total_cost = base_cost + text_cost
    
    # Cap at 100 units
    return min(total_cost, 100)


def _compute_duration(answer: str, rationale: str) -> int:
    """
    Compute deterministic duration based on input sizes.
    
    Returns duration in milliseconds (capped).
    """
    answer_len = len(answer) if answer else 0
    rationale_len = len(rationale) if rationale else 0
    
    # Base duration + proportional to text length
    base_duration = 100
    text_duration = (answer_len + rationale_len) // 20
    
    total_duration = base_duration + text_duration
    
    # Cap at 500ms
    return min(total_duration, 500)
