"""
Phase 17 Step 7: Regret Minimization Simulation Pass

Rule-based, versioned regret scoring model that forces safer alternatives
when risk scores exceed explicit thresholds.

Non-agentic, deterministic, patch-only, fail-closed.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from backend.app.deepthink.engine import EngineContext, PassRunResult
from backend.app.deepthink.schema import (
    PatchOp,
    DecisionDelta,
    DecisionAction,
    MAX_ANSWER_CHARS,
    MAX_RATIONALE_CHARS,
    MAX_CLARIFY_QUESTION_CHARS,
)


# Regret model version (explicit, versioned)
REGRET_MODEL_VERSION = "17.7.0"


# Explicit weights for regret scoring
WEIGHTS = {
    "safety_risk": 0.40,
    "misinfo_risk": 0.30,
    "confusion": 0.20,
    "user_cost": 0.10,
}


# Explicit thresholds
THRESHOLDS = {
    "SAFETY_HARD_THRESHOLD": 70,  # Force FALLBACK if safety_risk >= this
    "FORCE_CLARIFY_THRESHOLD": 60,  # Force ASK_CLARIFY if total_regret >= this
}


# Domain types for classification
class DomainType(str, Enum):
    """Domain types for regret assessment."""
    GENERIC = "GENERIC"
    CODE_TECH = "CODE_TECH"
    DEPLOY_DEVOPS = "DEPLOY_DEVOPS"
    SECURITY_PRIVACY = "SECURITY_PRIVACY"
    LEGAL_POLICY = "LEGAL_POLICY"
    MEDICAL_HEALTH = "MEDICAL_HEALTH"
    FINANCE_TAX = "FINANCE_TAX"


# Forbidden phrases in clarify questions
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


# Absolute language markers (increase misinfo risk)
ABSOLUTE_MARKERS = [
    "definitely",
    "guaranteed",
    "100%",
    "always",
    "never",
    "certainly",
    "absolutely",
    "without doubt",
]


# Safety-critical domains
SAFETY_CRITICAL_DOMAINS = {
    DomainType.MEDICAL_HEALTH,
    DomainType.LEGAL_POLICY,
    DomainType.SECURITY_PRIVACY,
    DomainType.FINANCE_TAX,
}


# Domain classification keywords (ordered by priority)
DOMAIN_KEYWORDS = [
    (DomainType.MEDICAL_HEALTH, [
        "medical", "health", "symptom", "pain", "fever", "illness", "disease",
        "doctor", "hospital", "medication", "emergency", "injury",
    ]),
    (DomainType.SECURITY_PRIVACY, [
        "security", "vulnerability", "exploit", "attack", "breach", "hack",
        "privacy", "encryption", "authentication", "malware", "phishing",
    ]),
    (DomainType.LEGAL_POLICY, [
        "legal", "law", "regulation", "compliance", "contract", "liability",
        "lawsuit", "court", "attorney", "jurisdiction", "gdpr",
    ]),
    (DomainType.FINANCE_TAX, [
        "tax", "finance", "investment", "stock", "trading", "capital gains",
        "irs", "deduction", "loan", "mortgage", "portfolio",
    ]),
    (DomainType.DEPLOY_DEVOPS, [
        "deploy", "deployment", "railway", "vercel", "docker", "build",
        "ci/cd", "kubernetes", "aws", "gcp", "container",
    ]),
    (DomainType.CODE_TECH, [
        "error", "exception", "bug", "code", "function", "syntax",
        "python", "javascript", "java", "compile", "debug",
    ]),
]


def run_regret_pass(
    pass_type: str,
    state: Dict[str, Any],
    context: EngineContext,
) -> PassRunResult:
    """
    Run regret minimization pass on decision state.
    
    Uses explicit rule-based scoring to force safer alternatives when
    risk scores exceed thresholds.
    
    Args:
        pass_type: Pass type identifier (should be "REGRET")
        state: Current decision state
        context: Engine context
    
    Returns:
        PassRunResult with delta ops, cost, duration
    
    Guarantees:
        - Deterministic: same inputs -> same outputs
        - Non-agentic: no external calls
        - Patch-only: returns DecisionDelta
        - Fail-closed: errors return empty delta with error message
        - Versioned: uses REGRET_MODEL_VERSION
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
    
    # Classify domain
    domain = _classify_domain(request_text)
    
    # Compute regret scores
    safety_risk = _compute_safety_risk_score(
        domain, current_action, current_answer, current_rationale
    )
    misinfo_risk = _compute_misinfo_risk_score(current_answer)
    confusion = _compute_confusion_score(
        current_action, current_answer, current_rationale, current_clarify
    )
    user_cost = _compute_user_cost_score(current_action, current_clarify)
    
    # Compute total regret (weighted sum)
    total_regret = (
        WEIGHTS["safety_risk"] * safety_risk +
        WEIGHTS["misinfo_risk"] * misinfo_risk +
        WEIGHTS["confusion"] * confusion +
        WEIGHTS["user_cost"] * user_cost
    )
    
    # Apply policy based on thresholds
    ops: List[PatchOp] = []
    
    if safety_risk >= THRESHOLDS["SAFETY_HARD_THRESHOLD"]:
        # Force FALLBACK for safety
        if current_action != "FALLBACK":
            ops.append(PatchOp(op="set", path="decision.action", value="FALLBACK"))
        
        # Set minimal safe answer
        ops.append(PatchOp(op="set", path="decision.answer", value=""))
        
        # Set safety rationale
        safety_rationale = f"Safety threshold exceeded (score: {int(safety_risk)}). Conservative fallback applied."
        ops.append(PatchOp(op="set", path="decision.rationale", value=safety_rationale[:MAX_RATIONALE_CHARS]))
    
    elif total_regret >= THRESHOLDS["FORCE_CLARIFY_THRESHOLD"]:
        # Force ASK_CLARIFY
        if current_action != "ASK_CLARIFY":
            ops.append(PatchOp(op="set", path="decision.action", value="ASK_CLARIFY"))
        
        # Generate clarify question
        clarify_q = _generate_clarify_question(domain, request_text, current_clarify)
        if clarify_q:
            ops.append(PatchOp(op="set", path="decision.clarify_question", value=clarify_q))
        
        # Set clarification rationale
        clarify_rationale = f"Regret score {int(total_regret)} requires clarification to minimize risk."
        ops.append(PatchOp(op="set", path="decision.rationale", value=clarify_rationale[:MAX_RATIONALE_CHARS]))
    
    else:
        # Keep current action, optionally tighten rationale
        if current_action == "ANSWER" and current_rationale:
            tightened = _tighten_rationale(current_rationale)
            if tightened != current_rationale:
                ops.append(PatchOp(op="set", path="decision.rationale", value=tightened))
    
    # Sort ops by path for deterministic ordering
    ops.sort(key=lambda op: op.path)
    
    # Compute deterministic cost and duration
    cost_units = _compute_cost(request_text, len(ops), int(total_regret))
    duration_ms = _compute_duration(request_text, len(ops), int(total_regret))
    
    return PassRunResult(
        pass_type=pass_type,
        delta=ops,
        cost_units=cost_units,
        duration_ms=duration_ms,
        error=None,
    )


def _extract_request_text(state: Dict[str, Any], context: EngineContext) -> str:
    """Extract request text from state or context."""
    request_text = state.get('request_text', '')
    if request_text:
        return request_text
    
    # Fallback to decision fields
    decision = state.get('decision', {})
    answer = decision.get('answer', '')
    rationale = decision.get('rationale', '')
    clarify = decision.get('clarify_question', '')
    
    combined = f"{answer} {rationale} {clarify}".strip()
    return combined


def _classify_domain(request_text: str) -> DomainType:
    """
    Classify request into domain type using deterministic keyword matching.
    
    First match wins from ordered list. Returns GENERIC if no match.
    """
    if not request_text:
        return DomainType.GENERIC
    
    request_lower = request_text.lower()
    
    # Check each domain in priority order
    for domain, keywords in DOMAIN_KEYWORDS:
        for keyword in keywords:
            if keyword in request_lower:
                return domain
    
    return DomainType.GENERIC


def _compute_safety_risk_score(
    domain: DomainType,
    action: str,
    answer: str,
    rationale: str,
) -> int:
    """
    Compute safety risk score (0-100).
    
    Increases when:
    - Domain is safety-critical AND action is ANSWER
    - Answer contains absolute language
    - Missing disclaimers in safety-critical domains
    """
    risk = 0
    
    # Safety-critical domain with ANSWER action
    if domain in SAFETY_CRITICAL_DOMAINS and action == "ANSWER":
        risk += 40
        
        # Check for absolute language
        answer_lower = answer.lower()
        for marker in ABSOLUTE_MARKERS:
            if marker in answer_lower:
                risk += 15
                break
        
        # Missing disclaimers
        disclaimer_keywords = ["may", "might", "could", "typically", "generally", "assuming"]
        has_disclaimer = any(kw in answer_lower for kw in disclaimer_keywords)
        if not has_disclaimer and len(answer) > 20:
            risk += 20
    
    return min(risk, 100)


def _compute_misinfo_risk_score(answer: str) -> int:
    """
    Compute misinformation risk score (0-100).
    
    Increases when answer contains absolute phrases without caveats.
    """
    risk = 0
    
    if not answer:
        return 0
    
    answer_lower = answer.lower()
    
    # Count absolute markers
    absolute_count = sum(1 for marker in ABSOLUTE_MARKERS if marker in answer_lower)
    risk += absolute_count * 20
    
    # Check for caveats
    caveat_keywords = ["however", "but", "although", "depending", "may vary", "typically"]
    has_caveat = any(kw in answer_lower for kw in caveat_keywords)
    
    if absolute_count > 0 and not has_caveat:
        risk += 20
    
    return min(risk, 100)


def _compute_confusion_score(
    action: str,
    answer: str,
    rationale: str,
    clarify_question: str,
) -> int:
    """
    Compute confusion score (0-100).
    
    Increases when:
    - Answer is long but rationale is short (imbalance)
    - Action is ANSWER but clarify_question is also set (dual-mode confusion)
    """
    confusion = 0
    
    # Imbalance: long answer, short rationale
    if len(answer) > 200 and len(rationale) < 50:
        confusion += 30
    
    # Dual-mode confusion
    if action == "ANSWER" and clarify_question and len(clarify_question) > 20:
        confusion += 40
    
    return min(confusion, 100)


def _compute_user_cost_score(action: str, clarify_question: str) -> int:
    """
    Compute user cost score (0-100).
    
    Increases when action is ASK_CLARIFY with multiple questions.
    """
    cost = 0
    
    if action == "ASK_CLARIFY":
        cost = 40  # Base cost for clarification
        
        # Check for multiple questions (count question marks or numbered items)
        if clarify_question:
            question_marks = clarify_question.count("?")
            numbered_items = sum(1 for c in ["(1)", "(2)", "(3)", "(4)"] if c in clarify_question)
            
            item_count = max(question_marks, numbered_items)
            if item_count > 3:
                cost += 20
    
    return min(cost, 100)


def _generate_clarify_question(
    domain: DomainType,
    request_text: str,
    existing_clarify: str,
) -> str:
    """
    Generate bounded clarify question (max 3 items).
    
    Must not contain forbidden phrases.
    """
    # If existing clarify is valid and safe, keep it
    if existing_clarify and len(existing_clarify) > 20:
        sanitized = _sanitize_clarify_question(existing_clarify)
        if sanitized:
            return sanitized[:MAX_CLARIFY_QUESTION_CHARS]
    
    # Generate domain-specific clarify question
    if domain == DomainType.MEDICAL_HEALTH:
        question = "To provide safe guidance, I need: (1) specific symptoms, (2) duration, (3) severity indicators."
    elif domain == DomainType.SECURITY_PRIVACY:
        question = "To assess security properly, I need: (1) threat model, (2) affected systems, (3) current safeguards."
    elif domain == DomainType.LEGAL_POLICY:
        question = "To provide accurate legal context, I need: (1) jurisdiction, (2) relevant facts, (3) specific question."
    elif domain == DomainType.FINANCE_TAX:
        question = "To provide financial guidance, I need: (1) jurisdiction, (2) instrument type, (3) time horizon."
    elif domain == DomainType.CODE_TECH:
        question = "To debug effectively, I need: (1) language/runtime, (2) error message, (3) environment context."
    elif domain == DomainType.DEPLOY_DEVOPS:
        question = "To troubleshoot deployment, I need: (1) platform, (2) build stage, (3) error details."
    else:
        question = "To answer accurately, I need: (1) your specific goal, (2) relevant context, (3) any constraints."
    
    # Ensure no forbidden phrases
    question = _sanitize_clarify_question(question)
    
    return question[:MAX_CLARIFY_QUESTION_CHARS]


def _sanitize_clarify_question(question: str) -> str:
    """Remove forbidden phrases from clarify question."""
    question_lower = question.lower()
    for forbidden in FORBIDDEN_CLARIFY_PHRASES:
        if forbidden in question_lower:
            # Replace with generic safe question
            return "Could you provide more specific details about your request?"
    return question


def _tighten_rationale(rationale: str) -> str:
    """Tighten rationale by adding caveats."""
    if not rationale:
        return rationale
    
    # Add caveat if not present
    caveat_keywords = ["assuming", "typically", "may vary", "depending"]
    has_caveat = any(kw in rationale.lower() for kw in caveat_keywords)
    
    if not has_caveat:
        tightened = f"{rationale.strip()} This assumes typical conditions and may vary."
    else:
        tightened = rationale
    
    return tightened[:MAX_RATIONALE_CHARS]


def _compute_cost(request_text: str, patch_count: int, regret_score: int) -> int:
    """Compute deterministic cost for pass execution."""
    base_cost = 35
    text_cost = len(request_text) // 100
    patch_cost = patch_count * 8
    regret_cost = regret_score // 20
    
    total_cost = base_cost + text_cost + patch_cost + regret_cost
    
    return min(total_cost, 250)


def _compute_duration(request_text: str, patch_count: int, regret_score: int) -> int:
    """Compute deterministic duration for pass execution."""
    base_duration = 180
    text_duration = len(request_text) // 50
    patch_duration = patch_count * 15
    regret_duration = regret_score // 10
    
    total_duration = base_duration + text_duration + patch_duration + regret_duration
    
    return min(total_duration, 800)
