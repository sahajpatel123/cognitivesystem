"""
Phase 17 Step 5: Assumption Stress-test Pass

Deterministic pass that classifies requests by domain and checks for missing
critical inputs. Forces ASK_CLARIFY when critical input is missing.

Non-agentic, deterministic, patch-only, fail-closed.
"""

from typing import Dict, Any, List, Optional, Set
from enum import Enum
from backend.app.deepthink.engine import EngineContext, PassRunResult
from backend.app.deepthink.schema import (
    PatchOp,
    DecisionDelta,
    MAX_ANSWER_CHARS,
    MAX_RATIONALE_CHARS,
    MAX_CLARIFY_QUESTION_CHARS,
)


# Domain classification enum (closed set)
class DomainType(str, Enum):
    """Fixed domain types for request classification."""
    GENERIC = "GENERIC"
    CODE_TECH = "CODE_TECH"
    DEPLOY_DEVOPS = "DEPLOY_DEVOPS"
    SECURITY_PRIVACY = "SECURITY_PRIVACY"
    LEGAL_POLICY = "LEGAL_POLICY"
    MEDICAL_HEALTH = "MEDICAL_HEALTH"
    FINANCE_TAX = "FINANCE_TAX"
    TRAVEL_LOCAL = "TRAVEL_LOCAL"
    PURCHASE_RECOMMENDATION = "PURCHASE_RECOMMENDATION"


# Critical input classes per domain
CRITICAL_INPUTS_MAP: Dict[DomainType, List[str]] = {
    DomainType.GENERIC: ["GOAL", "CONTEXT"],
    DomainType.CODE_TECH: ["LANG_RUNTIME", "ERROR_SYMPTOM", "ENV_CONTEXT"],
    DomainType.DEPLOY_DEVOPS: ["PLATFORM", "BUILD_STAGE", "ERROR_SYMPTOM"],
    DomainType.SECURITY_PRIVACY: ["THREAT_MODEL", "SCOPE_SYSTEM"],
    DomainType.LEGAL_POLICY: ["JURISDICTION", "FACTS_SUMMARY"],
    DomainType.MEDICAL_HEALTH: ["SYMPTOMS", "TIMELINE", "SEVERITY_RED_FLAGS"],
    DomainType.FINANCE_TAX: ["JURISDICTION", "INSTRUMENT_CONTEXT", "TIME_HORIZON"],
    DomainType.TRAVEL_LOCAL: ["LOCATION", "DATES", "PREFERENCES_CONSTRAINTS"],
    DomainType.PURCHASE_RECOMMENDATION: ["BUDGET", "REGION", "USE_CASE"],
}


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


# Domain classification keywords (ordered by priority, first match wins)
DOMAIN_KEYWORDS = [
    (DomainType.MEDICAL_HEALTH, [
        "symptom", "pain", "fever", "illness", "sick", "disease", "diagnosis",
        "doctor", "hospital", "medication", "treatment", "health", "medical",
        "injury", "bleeding", "chest pain", "breathing", "emergency",
    ]),
    (DomainType.SECURITY_PRIVACY, [
        "security", "vulnerability", "exploit", "attack", "breach", "hack",
        "privacy", "encryption", "authentication", "authorization", "threat",
        "malware", "phishing", "xss", "sql injection", "csrf",
    ]),
    (DomainType.DEPLOY_DEVOPS, [
        "deploy", "deployment", "railway", "vercel", "docker", "nixpacks",
        "build", "ci/cd", "pipeline", "kubernetes", "aws", "gcp", "azure",
        "heroku", "netlify", "container", "orchestration",
    ]),
    (DomainType.CODE_TECH, [
        "error", "exception", "traceback", "bug", "code", "function", "class",
        "import", "syntax", "runtime", "compile", "debug", "stack trace",
        "python", "javascript", "java", "typescript", "golang", "rust",
    ]),
    (DomainType.LEGAL_POLICY, [
        "legal", "law", "regulation", "compliance", "contract", "agreement",
        "terms", "policy", "liability", "lawsuit", "court", "attorney",
        "jurisdiction", "statute", "gdpr", "copyright", "trademark",
    ]),
    (DomainType.FINANCE_TAX, [
        "tax", "finance", "investment", "stock", "bond", "mutual fund",
        "portfolio", "trading", "capital gains", "deduction", "filing",
        "irs", "income", "expense", "budget", "loan", "mortgage", "interest",
    ]),
    (DomainType.TRAVEL_LOCAL, [
        "travel", "trip", "flight", "hotel", "booking", "destination",
        "vacation", "tourism", "visa", "passport", "itinerary", "route",
        "near me", "nearby", "location", "directions", "restaurant",
    ]),
    (DomainType.PURCHASE_RECOMMENDATION, [
        "buy", "purchase", "recommend", "suggestion", "best", "review",
        "product", "compare", "price", "deal", "shopping", "store",
        "laptop", "phone", "camera", "gadget", "appliance",
    ]),
]


def run_stress_test_pass(
    pass_type: str,
    state: Dict[str, Any],
    context: EngineContext,
) -> PassRunResult:
    """
    Run stress-test pass on decision state.
    
    Classifies request by domain, checks for missing critical inputs,
    and forces ASK_CLARIFY if any critical input is missing.
    
    Args:
        pass_type: Pass type identifier (should be "STRESS_TEST")
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
    
    # Extract request_text from context or state
    request_text = _extract_request_text(state, context)
    
    # Classify domain
    domain = _classify_domain(request_text)
    
    # Get critical inputs for domain
    critical_inputs = CRITICAL_INPUTS_MAP.get(domain, [])
    
    # Check which critical inputs are missing
    missing_inputs = _check_missing_inputs(domain, critical_inputs, request_text, decision)
    
    # Generate delta ops
    ops: List[PatchOp] = []
    
    if missing_inputs:
        # Missing critical input -> force ASK_CLARIFY
        action = decision.get("action", "")
        
        if action != "ASK_CLARIFY":
            ops.append(PatchOp(op="set", path="decision.action", value="ASK_CLARIFY"))
        
        # Generate clarify question
        clarify_q = _generate_clarify_question(domain, missing_inputs)
        if clarify_q:
            ops.append(PatchOp(op="set", path="decision.clarify_question", value=clarify_q))
        
        # Generate rationale explaining missing inputs
        rationale = _generate_rationale(domain, missing_inputs)
        if rationale:
            ops.append(PatchOp(op="set", path="decision.rationale", value=rationale))
    
    # Sort ops by path for deterministic ordering
    ops.sort(key=lambda op: op.path)
    
    # Compute deterministic cost and duration
    cost_units = _compute_cost(request_text, missing_inputs)
    duration_ms = _compute_duration(request_text, missing_inputs)
    
    return PassRunResult(
        pass_type=pass_type,
        delta=ops,
        cost_units=cost_units,
        duration_ms=duration_ms,
        error=None,
    )


def _extract_request_text(state: Dict[str, Any], context: EngineContext) -> str:
    """
    Extract request text from state or context.
    
    Looks for request_text in various places (deterministic priority).
    """
    # Try context.request_signature first (may contain text)
    if hasattr(context, 'request_text'):
        return getattr(context, 'request_text', '')
    
    # Try state.request_text
    request_text = state.get('request_text', '')
    if request_text:
        return request_text
    
    # Try decision fields as fallback
    decision = state.get('decision', {})
    answer = decision.get('answer', '')
    rationale = decision.get('rationale', '')
    clarify = decision.get('clarify_question', '')
    
    # Combine available text
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


def _check_missing_inputs(
    domain: DomainType,
    critical_inputs: List[str],
    request_text: str,
    decision: Dict[str, Any],
) -> List[str]:
    """
    Check which critical inputs are missing.
    
    Returns deterministic ordered list of missing input classes.
    """
    missing: List[str] = []
    request_lower = request_text.lower()
    
    for input_class in critical_inputs:
        if not _is_input_present(input_class, request_lower, decision):
            missing.append(input_class)
    
    return missing


def _is_input_present(input_class: str, request_lower: str, decision: Dict[str, Any]) -> bool:
    """
    Check if a critical input class is present in request.
    
    Deterministic presence checks using keyword patterns.
    """
    if input_class == "GOAL":
        # Check for goal indicators
        goal_keywords = ["want", "need", "how to", "help me", "trying to", "goal", "objective"]
        return any(kw in request_lower for kw in goal_keywords)
    
    elif input_class == "CONTEXT":
        # Check for context indicators (reasonable length)
        return len(request_lower) > 20
    
    elif input_class == "LANG_RUNTIME":
        # Check for language/runtime mentions
        lang_keywords = ["python", "javascript", "java", "typescript", "node", "go", "rust", "ruby", "php", "c++", "c#"]
        return any(kw in request_lower for kw in lang_keywords)
    
    elif input_class == "ERROR_SYMPTOM":
        # Check for error indicators
        error_keywords = ["error", "exception", "traceback", "failed", "exit code", "crash", "bug", "issue"]
        return any(kw in request_lower for kw in error_keywords)
    
    elif input_class == "ENV_CONTEXT":
        # Check for environment mentions
        env_keywords = ["local", "dev", "staging", "production", "environment", "server", "machine", "os", "windows", "linux", "mac"]
        return any(kw in request_lower for kw in env_keywords)
    
    elif input_class == "PLATFORM":
        # Check for platform mentions
        platform_keywords = ["railway", "vercel", "docker", "nixpacks", "aws", "gcp", "azure", "heroku", "netlify", "kubernetes"]
        return any(kw in request_lower for kw in platform_keywords)
    
    elif input_class == "BUILD_STAGE":
        # Check for build stage mentions
        build_keywords = ["build", "compile", "deploy", "start", "runtime", "install", "setup"]
        return any(kw in request_lower for kw in build_keywords)
    
    elif input_class == "THREAT_MODEL":
        # Check for threat model mentions
        threat_keywords = ["attack", "threat", "vulnerability", "exploit", "malicious", "unauthorized"]
        return any(kw in request_lower for kw in threat_keywords)
    
    elif input_class == "SCOPE_SYSTEM":
        # Check for system scope mentions
        scope_keywords = ["system", "application", "service", "api", "database", "network", "infrastructure"]
        return any(kw in request_lower for kw in scope_keywords)
    
    elif input_class == "JURISDICTION":
        # Check for jurisdiction mentions
        jurisdiction_keywords = ["india", "us", "usa", "uk", "california", "texas", "new york", "country", "state", "jurisdiction"]
        return any(kw in request_lower for kw in jurisdiction_keywords)
    
    elif input_class == "FACTS_SUMMARY":
        # Check for facts/details (reasonable length)
        return len(request_lower) > 30
    
    elif input_class == "SYMPTOMS":
        # Check for symptom descriptions
        symptom_keywords = ["pain", "fever", "cough", "headache", "nausea", "dizzy", "symptom", "feel", "hurt"]
        return any(kw in request_lower for kw in symptom_keywords)
    
    elif input_class == "TIMELINE":
        # Check for timeline mentions
        timeline_keywords = ["since", "for", "days", "weeks", "months", "started", "began", "ago", "yesterday", "today"]
        return any(kw in request_lower for kw in timeline_keywords)
    
    elif input_class == "SEVERITY_RED_FLAGS":
        # Check for severe symptoms (conservative: treat as missing unless explicit)
        severe_keywords = ["severe", "emergency", "urgent", "chest pain", "bleeding", "unconscious", "difficulty breathing"]
        return any(kw in request_lower for kw in severe_keywords)
    
    elif input_class == "INSTRUMENT_CONTEXT":
        # Check for financial instrument mentions
        instrument_keywords = ["stock", "bond", "mutual fund", "etf", "option", "crypto", "investment", "portfolio"]
        return any(kw in request_lower for kw in instrument_keywords)
    
    elif input_class == "TIME_HORIZON":
        # Check for time horizon mentions
        horizon_keywords = ["short term", "long term", "year", "years", "month", "months", "retirement", "future"]
        return any(kw in request_lower for kw in horizon_keywords)
    
    elif input_class == "LOCATION":
        # Check for location mentions (but NOT "near me" without specifics)
        if "near me" in request_lower or "nearby" in request_lower:
            # "near me" without city name = missing LOCATION
            city_keywords = ["city", "town", "village", "bangalore", "mumbai", "delhi", "new york", "london", "san francisco"]
            return any(kw in request_lower for kw in city_keywords)
        else:
            # Check for explicit location mentions
            location_keywords = ["in", "at", "near", "city", "town", "country", "bangalore", "mumbai", "delhi"]
            return any(kw in request_lower for kw in location_keywords)
    
    elif input_class == "DATES":
        # Check for date mentions
        date_keywords = ["date", "when", "tomorrow", "next week", "next month", "january", "february", "march", "2024", "2025"]
        return any(kw in request_lower for kw in date_keywords)
    
    elif input_class == "PREFERENCES_CONSTRAINTS":
        # Check for preferences/constraints
        pref_keywords = ["prefer", "like", "want", "need", "budget", "cheap", "expensive", "luxury", "constraint"]
        return any(kw in request_lower for kw in pref_keywords)
    
    elif input_class == "BUDGET":
        # Check for budget mentions
        budget_keywords = ["budget", "price", "cost", "₹", "$", "€", "under", "below", "cheap", "expensive"]
        return any(kw in request_lower for kw in budget_keywords)
    
    elif input_class == "REGION":
        # Check for region mentions
        region_keywords = ["india", "us", "usa", "uk", "europe", "asia", "region", "country", "available in"]
        return any(kw in request_lower for kw in region_keywords)
    
    elif input_class == "USE_CASE":
        # Check for use case mentions
        usecase_keywords = ["for", "use", "purpose", "need", "want", "looking for", "use case"]
        return any(kw in request_lower for kw in usecase_keywords)
    
    # Default: treat as missing (fail-closed)
    return False


def _generate_clarify_question(domain: DomainType, missing_inputs: List[str]) -> str:
    """
    Generate deterministic clarify question for missing inputs.
    
    Asks for top 3 missing items max, stable ordering.
    Must not contain forbidden phrases.
    """
    # Take top 3 missing items
    asked_items = missing_inputs[:3]
    
    # Generate human-readable names for missing items
    item_names = [_humanize_input_class(item) for item in asked_items]
    
    # Build question template
    if len(item_names) == 1:
        question = f"To answer safely, I need: {item_names[0]}."
    elif len(item_names) == 2:
        question = f"To answer safely, I need: (1) {item_names[0]}, and (2) {item_names[1]}."
    else:
        items_str = ", ".join([f"({i+1}) {name}" for i, name in enumerate(item_names)])
        question = f"To answer safely, I need: {items_str}."
    
    # Ensure within bounds
    question = question[:MAX_CLARIFY_QUESTION_CHARS]
    
    # Verify no forbidden phrases (defensive check)
    question_lower = question.lower()
    for forbidden in FORBIDDEN_CLARIFY_PHRASES:
        if forbidden in question_lower:
            # Fallback to generic question
            return "Could you provide more specific details about your request?"[:MAX_CLARIFY_QUESTION_CHARS]
    
    return question


def _humanize_input_class(input_class: str) -> str:
    """
    Convert input class to human-readable name.
    """
    humanized = {
        "GOAL": "your specific goal or objective",
        "CONTEXT": "more context about your situation",
        "LANG_RUNTIME": "the programming language or runtime",
        "ERROR_SYMPTOM": "the specific error message or symptom",
        "ENV_CONTEXT": "your environment details (OS, version, etc.)",
        "PLATFORM": "the deployment platform you're using",
        "BUILD_STAGE": "which build stage is failing",
        "THREAT_MODEL": "the specific threat or attack vector",
        "SCOPE_SYSTEM": "which system or component is affected",
        "JURISDICTION": "your jurisdiction (country/state)",
        "FACTS_SUMMARY": "a summary of the relevant facts",
        "SYMPTOMS": "specific symptoms you're experiencing",
        "TIMELINE": "when the symptoms started",
        "SEVERITY_RED_FLAGS": "severity indicators (emergency symptoms)",
        "INSTRUMENT_CONTEXT": "the specific financial instrument",
        "TIME_HORIZON": "your investment time horizon",
        "LOCATION": "your specific location or city",
        "DATES": "your travel dates",
        "PREFERENCES_CONSTRAINTS": "your preferences or constraints",
        "BUDGET": "your budget range",
        "REGION": "your region or country",
        "USE_CASE": "your specific use case or purpose",
    }
    return humanized.get(input_class, input_class.lower().replace("_", " "))


def _generate_rationale(domain: DomainType, missing_inputs: List[str]) -> str:
    """
    Generate deterministic rationale explaining missing inputs.
    """
    if not missing_inputs:
        return ""
    
    asked_items = missing_inputs[:3]
    item_names = [_humanize_input_class(item) for item in asked_items]
    
    if len(item_names) == 1:
        rationale = f"Missing critical information: {item_names[0]}. Clarification needed for safe response."
    else:
        items_str = ", ".join(item_names)
        rationale = f"Missing critical information: {items_str}. Clarification needed for safe response."
    
    # Ensure within bounds
    return rationale[:MAX_RATIONALE_CHARS]


def _compute_cost(request_text: str, missing_inputs: List[str]) -> int:
    """
    Compute deterministic cost based on input sizes.
    """
    base_cost = 25
    text_cost = len(request_text) // 100
    missing_cost = len(missing_inputs) * 5
    
    total_cost = base_cost + text_cost + missing_cost
    
    # Cap at 150 units
    return min(total_cost, 150)


def _compute_duration(request_text: str, missing_inputs: List[str]) -> int:
    """
    Compute deterministic duration based on input sizes.
    """
    base_duration = 120
    text_duration = len(request_text) // 50
    missing_duration = len(missing_inputs) * 10
    
    total_duration = base_duration + text_duration + missing_duration
    
    # Cap at 600ms
    return min(total_duration, 600)
