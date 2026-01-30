"""
Phase 18 Step 9: Research Integration Wiring

Policy-gated research pipeline with fail-closed, deterministic behavior.
Single chokepoint through adapter.retrieve() wrapped by sandbox.

Contract guarantees:
- Policy supremacy: policy decides if research allowed + caps
- Single chokepoint: adapter.retrieve() only path to retrieval
- Patch-only output: returns DecisionDelta patches only
- Deterministic stop reasons + fail-closed
- No user text leakage in telemetry/signature
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from backend.app.research.sandbox import (
    SandboxCaps,
    SandboxState,
    SandboxResult,
    create_sandbox_state,
    run_sandboxed_call,
)
from backend.app.research.cache import (
    ResearchCache,
    canonicalize_query,
    make_cache_key,
    CacheKeyParts,
)
from backend.app.research.dedup import dedup_bundles
from backend.app.research.credibility import grade_sources, GradedSource
from backend.app.research.claim_binder import bind_claims_and_citations, BinderOutput
from backend.app.research.injection_defense import sanitize_tool_output, SanitizerResult
from backend.app.research.telemetry import (
    build_research_telemetry_event,
    compute_research_signature,
    sanitize_event,
)
from backend.app.retrieval.adapter import (
    RetrievalRequest,
    retrieve,
)
from backend.app.retrieval.types import (
    ToolKind,
    EnvMode,
    PolicyCaps,
    RequestFlags,
    SourceBundle,
    SourceSnippet,
)


# ============================================================================
# ALLOWED STOP REASONS (Phase 18 contract)
# ============================================================================

ALLOWED_STOP_REASONS = frozenset([
    "SUCCESS_COMPLETED",
    "ENTITLEMENT_CAP",
    "POLICY_DISABLED",
    "BUDGET_EXHAUSTED",
    "RATE_LIMITED",
    "TIMEOUT",
    "SANDBOX_VIOLATION",
    "INJECTION_DETECTED",
    "NO_SOURCE",
    "VALIDATION_FAIL",
    "INTERNAL_INCONSISTENCY",
])


# ============================================================================
# BOUNDS (Phase 17 schema)
# ============================================================================

MAX_ANSWER_CHARS = 1200
MAX_RATIONALE_CHARS = 600
MAX_CLARIFY_QUESTION_CHARS = 300
MAX_ALTERNATIVE_CHARS = 200
MAX_ALTERNATIVES_COUNT = 3
MAX_DOMAIN_LEN = 100
MAX_DOMAINS_COUNT = 20


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass(frozen=True)
class ResearchPolicyDecision:
    """
    Policy decision for research operations.
    
    Policy supremacy: these caps CANNOT be overridden by requested mode.
    """
    allowed: bool
    caps: SandboxCaps
    allowed_tools: List[ToolKind]
    citations_required: bool
    env_mode: EnvMode
    max_results: int
    cache_enabled: bool


@dataclass
class ResearchOutcome:
    """
    Outcome of policy-gated research execution.
    
    All fields are deterministic and structure-only (no raw text).
    """
    ok: bool
    stop_reason: str
    used_cache: bool
    tool_calls_count: int
    domains_used: List[str]
    grade_histogram: Dict[str, int]
    citation_coverage: Dict[str, int]
    research_signature: str
    telemetry_event: Dict[str, Any]
    decision_delta: List[dict]
    sandbox_state: Optional[SandboxState] = None  # For caps accumulation across calls


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _safe_stop_reason(reason: str) -> str:
    """
    Validate stop reason against allowed list.
    
    Returns INTERNAL_INCONSISTENCY if reason is invalid.
    """
    if reason in ALLOWED_STOP_REASONS:
        return reason
    return "INTERNAL_INCONSISTENCY"


def _bounded_str(s: str, max_len: int) -> str:
    """
    Bound string to max length.
    
    Returns empty string if input is None or not a string.
    """
    if not s or not isinstance(s, str):
        return ""
    return s[:max_len]


def _mk_patch(path: str, op: str, value: Any) -> dict:
    """
    Create PatchOp dict consistent with Phase17 schema.
    
    Args:
        path: Dot-notation path (e.g., "decision.action")
        op: Operation type (should be "set")
        value: Value to set
    
    Returns:
        Dict with op, path, value keys
    """
    return {
        "op": op,
        "path": path,
        "value": value,
    }


def _force_ask_clarify_delta(msg: str, rationale: str) -> List[dict]:
    """
    Create DecisionDelta that forces ASK_CLARIFY action.
    
    Args:
        msg: Clarify question (bounded to 300 chars)
        rationale: Rationale (bounded to 600 chars)
    
    Returns:
        List of PatchOp dicts
    """
    bounded_msg = _bounded_str(msg, MAX_CLARIFY_QUESTION_CHARS)
    bounded_rationale = _bounded_str(rationale, MAX_RATIONALE_CHARS)
    
    ops = [
        _mk_patch("decision.action", "set", "ASK_CLARIFY"),
        _mk_patch("decision.clarify_question", "set", bounded_msg),
        _mk_patch("decision.rationale", "set", bounded_rationale),
        _mk_patch("decision.answer", "set", ""),
    ]
    
    # Sort by path for deterministic ordering
    ops.sort(key=lambda x: x["path"])
    return ops


def _force_fallback_delta(rationale: str) -> List[dict]:
    """
    Create DecisionDelta that forces FALLBACK action.
    
    Args:
        rationale: Rationale (bounded to 600 chars)
    
    Returns:
        List of PatchOp dicts
    """
    bounded_rationale = _bounded_str(rationale, MAX_RATIONALE_CHARS)
    
    ops = [
        _mk_patch("decision.action", "set", "FALLBACK"),
        _mk_patch("decision.rationale", "set", bounded_rationale),
        _mk_patch("decision.answer", "set", ""),
    ]
    
    # Sort by path for deterministic ordering
    ops.sort(key=lambda x: x["path"])
    return ops


def _extract_decision_answer_text(state: Dict[str, Any]) -> str:
    """
    Extract answer text from decision state (read-only).
    
    Returns empty string if not found or invalid.
    """
    if not state or not isinstance(state, dict):
        return ""
    
    decision = state.get("decision")
    if not decision or not isinstance(decision, dict):
        return ""
    
    answer = decision.get("answer")
    if not answer or not isinstance(answer, str):
        return ""
    
    return answer


def _extract_domains(bundles: List[SourceBundle]) -> List[str]:
    """
    Extract unique domains from bundles (bounded, no raw text).
    """
    seen = set()
    domains = []
    
    for bundle in bundles:
        domain = _bounded_str(bundle.domain, MAX_DOMAIN_LEN).lower()
        if domain and domain not in seen:
            seen.add(domain)
            domains.append(domain)
        
        if len(domains) >= MAX_DOMAINS_COUNT:
            break
    
    return sorted(domains)


def _compute_grade_histogram(graded_sources: List[GradedSource]) -> Dict[str, int]:
    """
    Compute grade histogram from graded sources.
    """
    histogram = {
        "A": 0,
        "B": 0,
        "C": 0,
        "D": 0,
        "E": 0,
        "UNKNOWN": 0,
    }
    
    for gs in graded_sources:
        grade = gs.credibility.grade if gs.credibility else "UNKNOWN"
        if grade in histogram:
            histogram[grade] += 1
        else:
            histogram["UNKNOWN"] += 1
    
    return histogram


def _compute_citation_coverage(binder_output: BinderOutput) -> Dict[str, int]:
    """
    Compute citation coverage from binder output.
    """
    claims = binder_output.claims
    bindings = binder_output.bindings
    uncovered = binder_output.uncovered_required_claim_ids
    
    required_total = sum(1 for c in claims if c.required)
    required_covered = required_total - len(uncovered)
    
    return {
        "claims_total": len(claims),
        "claims_required": required_total,
        "claims_required_covered": max(0, required_covered),
        "uncovered_required": len(uncovered),
    }


def _build_empty_telemetry(stop_reason: str, env_mode: str) -> Dict[str, Any]:
    """
    Build empty/safe telemetry event for error cases.
    """
    return build_research_telemetry_event(
        env_mode=env_mode,
        tool_calls_count=0,
        domains_used=[],
        grade_histogram=None,
        citation_coverage=None,
        stop_reason=stop_reason,
        validator_failures=0,
        downgrade_reason=stop_reason if stop_reason != "SUCCESS_COMPLETED" else None,
    )


def _sanitize_bundles(bundles: List[SourceBundle]) -> tuple:
    """
    Sanitize all snippet texts in bundles.
    
    Returns:
        Tuple of (sanitized_bundles, had_strong_injection, all_empty)
    """
    sanitized_bundles = []
    had_strong_injection = False
    all_snippets_empty = True
    
    for bundle in bundles:
        sanitized_snippets = []
        
        for snippet in bundle.snippets:
            result: SanitizerResult = sanitize_tool_output(snippet.text)
            
            if result.event.had_injection:
                had_strong_injection = True
            
            sanitized_text = result.sanitized_text
            if sanitized_text:
                all_snippets_empty = False
            
            sanitized_snippets.append(SourceSnippet(
                text=sanitized_text,
                start=snippet.start,
                end=snippet.end,
            ))
        
        # Rebuild bundle with sanitized snippets
        sanitized_bundle = SourceBundle(
            source_id=bundle.source_id,
            tool=bundle.tool,
            url=bundle.url,
            domain=bundle.domain,
            title=bundle.title,
            retrieved_at=bundle.retrieved_at,
            snippets=sanitized_snippets,
            metadata=bundle.metadata,
        )
        sanitized_bundles.append(sanitized_bundle)
    
    return sanitized_bundles, had_strong_injection, all_snippets_empty


def _map_sandbox_stop_reason(sandbox_reason: str) -> str:
    """
    Map sandbox stop reason to Phase 18 stop reason.
    """
    mapping = {
        "TIMEOUT": "TIMEOUT",
        "BUDGET_EXHAUSTED": "BUDGET_EXHAUSTED",
        "RATE_LIMITED": "RATE_LIMITED",
        "SANDBOX_VIOLATION": "SANDBOX_VIOLATION",
    }
    return mapping.get(sandbox_reason, "INTERNAL_INCONSISTENCY")


def _delta_for_sandbox_stop(stop_reason: str) -> List[dict]:
    """
    Create delta for sandbox stop reasons.
    
    - RATE_LIMITED/BUDGET_EXHAUSTED/TIMEOUT -> ASK_CLARIFY
    - SANDBOX_VIOLATION -> FALLBACK
    """
    if stop_reason == "SANDBOX_VIOLATION":
        return _force_fallback_delta("Research unavailable due to execution error.")
    else:
        return _force_ask_clarify_delta(
            "Could you try a more specific question?",
            f"Research temporarily limited ({stop_reason})."
        )


def _delta_for_binder_mode(
    binder_output: BinderOutput,
    current_action: str,
) -> List[dict]:
    """
    Create delta based on binder final_mode.
    
    - OK: keep action, optionally tighten rationale
    - ASK_CLARIFY: patch to ASK_CLARIFY with binder questions
    - UNKNOWN: patch to FALLBACK (or ASK_CLARIFY if clarifiable)
    """
    final_mode = binder_output.final_mode
    clarify_questions = binder_output.clarify_questions
    
    if final_mode == "OK":
        # Keep current action, no patches needed for action
        # Return empty delta (no changes)
        return []
    
    elif final_mode == "ASK_CLARIFY":
        # Use first clarify question from binder
        question = clarify_questions[0] if clarify_questions else "Could you provide more details?"
        return _force_ask_clarify_delta(
            question,
            "Additional information needed to provide accurate answer."
        )
    
    else:  # UNKNOWN
        # If clarifiable questions exist, use ASK_CLARIFY; else FALLBACK
        if clarify_questions:
            question = clarify_questions[0]
            return _force_ask_clarify_delta(
                question,
                "Unable to verify claims with available sources."
            )
        else:
            return _force_fallback_delta(
                "Unable to provide verified answer with available sources."
            )


# ============================================================================
# MAIN ENTRYPOINT
# ============================================================================

def run_policy_gated_research(
    state: Dict[str, Any],
    research_query: str,
    policy: ResearchPolicyDecision,
    now_ms: int,
    tool_runner: Optional[Callable] = None,
    cache: Optional[ResearchCache] = None,
    sandbox_state: Optional[SandboxState] = None,
) -> ResearchOutcome:
    """
    Single entrypoint for policy-gated research execution.
    
    Args:
        state: Current decision state (read-only)
        research_query: Research query (NOT included in telemetry)
        policy: Policy decision with caps and allowed tools
        now_ms: Current time in milliseconds (injected for determinism)
        tool_runner: Optional tool runner for testing (monkeypatch)
        cache: Optional research cache
        sandbox_state: Optional sandbox state for caps accumulation across calls
    
    Returns:
        ResearchOutcome with patches, telemetry, and stop reason
    
    Guarantees:
        - Policy supremacy: caps cannot be overridden
        - Single chokepoint: all retrieval through adapter.retrieve()
        - Patch-only output: returns DecisionDelta only
        - Deterministic: same inputs -> same outputs
        - Fail-closed: any error -> INTERNAL_INCONSISTENCY
        - No user text in telemetry/signature
    """
    env_mode_str = policy.env_mode.value if policy.env_mode else "PROD"
    
    try:
        # ====================================================================
        # I) POLICY DISABLED
        # ====================================================================
        if not policy.allowed:
            stop_reason = "POLICY_DISABLED"
            
            delta = _force_ask_clarify_delta(
                "Research is not available for this request.",
                "Research mode not enabled by policy."
            )
            
            telemetry = _build_empty_telemetry(stop_reason, env_mode_str)
            signature = compute_research_signature(telemetry)
            
            return ResearchOutcome(
                ok=False,
                stop_reason=stop_reason,
                used_cache=False,
                tool_calls_count=0,
                domains_used=[],
                grade_histogram={},
                citation_coverage={},
                research_signature=signature,
                telemetry_event=telemetry,
                decision_delta=delta,
                sandbox_state=None,
            )
        
        # ====================================================================
        # II) POLICY ALLOWED - Execute pipeline
        # ====================================================================
        
        bundles: List[SourceBundle] = []
        used_cache = False
        tool_calls_count = 0
        
        # --------------------------------------------------------------------
        # 1) Cache lookup (if enabled)
        # --------------------------------------------------------------------
        canonical_query = canonicalize_query(research_query)
        cache_key = None
        
        if policy.cache_enabled and cache is not None:
            # Build cache key parts
            tool_kinds_str = ",".join(sorted(t.value for t in policy.allowed_tools))
            
            cache_key_parts = CacheKeyParts(
                query=canonical_query,
                tool_kind=tool_kinds_str,
                env_mode=env_mode_str,
                max_results=policy.max_results,
                citations_required=policy.citations_required,
            )
            cache_key = make_cache_key(cache_key_parts, now_ms)
            
            # Try cache lookup
            cached_bundles = cache.get(cache_key)
            if cached_bundles is not None:
                bundles = cached_bundles
                used_cache = True
        
        # --------------------------------------------------------------------
        # 2) Retrieval (if cache miss)
        # --------------------------------------------------------------------
        if not used_cache:
            # Build PolicyCaps for retrieval
            max_results = max(1, min(policy.max_results, 10))
            
            retrieval_caps = PolicyCaps(
                max_results=max_results,
                per_tool_timeout_ms=policy.caps.per_call_timeout_ms,
                total_timeout_ms=policy.caps.total_timeout_ms,
                max_tool_calls_total=policy.caps.max_calls_total,
                max_tool_calls_per_minute=policy.caps.max_calls_per_minute,
            )
            
            request_flags = RequestFlags(
                citations_required=policy.citations_required,
                allow_cache=policy.cache_enabled,
            )
            
            retrieval_request = RetrievalRequest(
                query=canonical_query,
                policy_caps=retrieval_caps,
                allowed_tools=list(policy.allowed_tools),
                env_mode=policy.env_mode,
                request_flags=request_flags,
            )
            
            # Use provided sandbox state or create new one
            current_sandbox_state = sandbox_state if sandbox_state is not None else create_sandbox_state(now_ms)
            
            # Wrap adapter.retrieve() with sandbox
            def _do_retrieve():
                return retrieve(retrieval_request)
            
            new_sandbox_state, sandbox_result = run_sandboxed_call(
                caps=policy.caps,
                state=current_sandbox_state,
                now_ms=now_ms,
                tool_call=_do_retrieve,
                call_duration_ms=0,  # Simulated for determinism
            )
            
            tool_calls_count = sandbox_result.calls_used_total
            
            # Check sandbox stop
            if not sandbox_result.ok:
                stop_reason = _map_sandbox_stop_reason(sandbox_result.stop_reason or "")
                stop_reason = _safe_stop_reason(stop_reason)
                
                delta = _delta_for_sandbox_stop(stop_reason)
                telemetry = _build_empty_telemetry(stop_reason, env_mode_str)
                signature = compute_research_signature(telemetry)
                
                return ResearchOutcome(
                    ok=False,
                    stop_reason=stop_reason,
                    used_cache=False,
                    tool_calls_count=tool_calls_count,
                    domains_used=[],
                    grade_histogram={},
                    citation_coverage={},
                    research_signature=signature,
                    telemetry_event=telemetry,
                    decision_delta=delta,
                    sandbox_state=new_sandbox_state,
                )
            
            bundles = sandbox_result.value or []
        
        # --------------------------------------------------------------------
        # 3) No source check
        # --------------------------------------------------------------------
        if not bundles:
            stop_reason = "NO_SOURCE"
            
            delta = _force_ask_clarify_delta(
                "Could you provide more context for your question?",
                "No sources found for the research query."
            )
            
            telemetry = _build_empty_telemetry(stop_reason, env_mode_str)
            signature = compute_research_signature(telemetry)
            
            # Determine sandbox state to return
            final_sandbox_state = new_sandbox_state if 'new_sandbox_state' in dir() else None
            
            return ResearchOutcome(
                ok=False,
                stop_reason=stop_reason,
                used_cache=used_cache,
                tool_calls_count=tool_calls_count,
                domains_used=[],
                grade_histogram={},
                citation_coverage={},
                research_signature=signature,
                telemetry_event=telemetry,
                decision_delta=delta,
                sandbox_state=final_sandbox_state,
            )
        
        # --------------------------------------------------------------------
        # 4) Sanitize tool output
        # --------------------------------------------------------------------
        sanitized_bundles, had_injection, all_empty = _sanitize_bundles(bundles)
        
        if had_injection and all_empty:
            stop_reason = "INJECTION_DETECTED"
            
            delta = _force_fallback_delta(
                "Content flagged for safety review."
            )
            
            telemetry = _build_empty_telemetry(stop_reason, env_mode_str)
            signature = compute_research_signature(telemetry)
            
            # Determine sandbox state to return
            final_sandbox_state = new_sandbox_state if 'new_sandbox_state' in dir() else None
            
            return ResearchOutcome(
                ok=False,
                stop_reason=stop_reason,
                used_cache=used_cache,
                tool_calls_count=tool_calls_count,
                domains_used=[],
                grade_histogram={},
                citation_coverage={},
                research_signature=signature,
                telemetry_event=telemetry,
                decision_delta=delta,
                sandbox_state=final_sandbox_state,
            )
        
        bundles = sanitized_bundles
        
        # --------------------------------------------------------------------
        # 5) Dedup + canonicalization
        # --------------------------------------------------------------------
        bundles = dedup_bundles(bundles)
        
        # --------------------------------------------------------------------
        # 6) Credibility grading
        # --------------------------------------------------------------------
        graded_sources: List[GradedSource] = grade_sources(bundles, now_ms)
        
        # --------------------------------------------------------------------
        # 7) Claim-cite binder
        # --------------------------------------------------------------------
        answer_text = _extract_decision_answer_text(state)
        
        binder_output: BinderOutput = bind_claims_and_citations(
            answer_text=answer_text,
            sources=graded_sources,
            citations_required=policy.citations_required,
        )
        
        # Get current action from state
        current_action = ""
        if state and isinstance(state, dict):
            decision = state.get("decision", {})
            if isinstance(decision, dict):
                current_action = decision.get("action", "")
        
        # Create delta based on binder mode
        delta = _delta_for_binder_mode(binder_output, current_action)
        
        # Determine stop reason based on binder mode
        if binder_output.final_mode == "OK":
            stop_reason = "SUCCESS_COMPLETED"
            ok = True
        else:
            stop_reason = "VALIDATION_FAIL"
            ok = False
        
        # --------------------------------------------------------------------
        # 8) Telemetry (structure-only, no user text)
        # --------------------------------------------------------------------
        domains_used = _extract_domains(bundles)
        grade_histogram = _compute_grade_histogram(graded_sources)
        citation_coverage = _compute_citation_coverage(binder_output)
        
        telemetry = build_research_telemetry_event(
            env_mode=env_mode_str,
            tool_calls_count=tool_calls_count,
            domains_used=domains_used,
            grade_histogram=grade_histogram,
            citation_coverage=citation_coverage,
            stop_reason=stop_reason,
            validator_failures=0,
            downgrade_reason=None if ok else stop_reason,
            sandbox_caps={
                "max_calls_total": policy.caps.max_calls_total,
                "max_calls_per_minute": policy.caps.max_calls_per_minute,
                "per_call_timeout_ms": policy.caps.per_call_timeout_ms,
                "total_timeout_ms": policy.caps.total_timeout_ms,
            },
            counters={
                "cache_hit": 1 if used_cache else 0,
                "cache_miss": 0 if used_cache else 1,
                "bundles_retrieved": len(bundles),
                "bundles_graded": len(graded_sources),
            },
        )
        
        signature = compute_research_signature(telemetry)
        
        # Store in cache if enabled and was a miss
        if policy.cache_enabled and cache is not None and not used_cache and cache_key:
            cache.put(cache_key, bundles)
        
        # Determine sandbox state to return
        final_sandbox_state = new_sandbox_state if 'new_sandbox_state' in dir() else None
        
        return ResearchOutcome(
            ok=ok,
            stop_reason=_safe_stop_reason(stop_reason),
            used_cache=used_cache,
            tool_calls_count=tool_calls_count,
            domains_used=domains_used,
            grade_histogram=grade_histogram,
            citation_coverage=citation_coverage,
            research_signature=signature,
            telemetry_event=telemetry,
            decision_delta=delta,
            sandbox_state=final_sandbox_state,
        )
    
    except Exception:
        # ====================================================================
        # III) FAIL-CLOSED
        # ====================================================================
        stop_reason = "INTERNAL_INCONSISTENCY"
        
        delta = _force_ask_clarify_delta(
            "Could you try rephrasing your question?",
            "An internal error occurred during research."
        )
        
        telemetry = _build_empty_telemetry(stop_reason, env_mode_str)
        signature = compute_research_signature(telemetry)
        
        return ResearchOutcome(
            ok=False,
            stop_reason=stop_reason,
            used_cache=False,
            tool_calls_count=0,
            domains_used=[],
            grade_histogram={},
            citation_coverage={},
            research_signature=signature,
            telemetry_event=telemetry,
            decision_delta=delta,
            sandbox_state=None,
        )
