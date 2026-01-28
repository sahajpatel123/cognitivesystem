"""
Phase 17 Step 3: Multi-pass Refinement Engine

Deterministic orchestrator that executes pass plans with strict guardrails.
Non-agentic, fail-closed, deterministic stop conditions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import hashlib
import json

from backend.app.deepthink.router import Plan, StopReason
from backend.app.deepthink.schema import PatchOp, DecisionDelta
from backend.app.deepthink.validator import validate_delta
from backend.app.deepthink.patch import apply_delta, PatchError
from backend.app.deepthink.telemetry import compute_decision_signature, build_telemetry_event


# Stop priority order (fixed, deterministic)
STOP_PRIORITY_ORDER = [
    "INTERNAL_INCONSISTENCY",
    "ABUSE",
    "ENTITLEMENT_CAP",
    "BREAKER_TRIPPED",
    "BUDGET_EXHAUSTED",
    "TIMEOUT",
    "VALIDATION_FAIL",
    "PASS_LIMIT_REACHED",
    "SUCCESS_COMPLETED",
]


@dataclass
class EngineContext:
    """
    Context for pass execution.
    Injected dependencies for determinism.
    """
    request_signature: str
    now_ms: Callable[[], int]  # Injected clock
    budget_units_remaining: int
    breaker_tripped: bool = False
    abuse_blocked: bool = False


@dataclass
class PassRunResult:
    """
    Result from a single pass execution.
    """
    pass_type: str
    delta: Optional[DecisionDelta]  # None if pass failed
    cost_units: int  # Budget consumed
    duration_ms: int  # Time consumed
    error: Optional[str] = None  # Error message if pass failed


@dataclass
class PassSummary:
    """
    Summary of a single pass execution (safe, no user text).
    """
    pass_type: str
    executed: bool
    validation_ok: bool
    patch_applied: bool
    cost_units: int
    duration_ms: int
    strikes_added: int
    error: Optional[str] = None


@dataclass
class EngineMeta:
    """
    Engine execution metadata (safe, no user text).
    """
    pass_count_executed: int
    stop_reason: str
    downgraded: bool
    validator_failures: int
    decision_signature: str
    pass_summaries: List[PassSummary] = field(default_factory=list)
    policy: Dict[str, Any] = field(default_factory=dict)
    telemetry_event: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineInput:
    """
    Input to the engine.
    """
    request_signature: str
    initial_state: Dict[str, Any]  # Baseline DecisionState
    plan: Plan  # From router
    context: EngineContext
    pass_runner: Callable[[str, Dict[str, Any], EngineContext], PassRunResult]


@dataclass
class EngineOutput:
    """
    Output from the engine.
    """
    final_state: Dict[str, Any]
    meta: EngineMeta


def run_engine(engine_input: EngineInput) -> EngineOutput:
    """
    Execute multi-pass refinement with deterministic orchestration.
    
    Args:
        engine_input: EngineInput with plan, state, context, runner
    
    Returns:
        EngineOutput with final state and metadata
    
    Guarantees:
        - Deterministic: same inputs -> same outputs
        - Fail-closed: errors -> downgrade to baseline
        - Non-agentic: no external calls, no tools
    """
    plan = engine_input.plan
    context = engine_input.context
    initial_state = engine_input.initial_state
    pass_runner = engine_input.pass_runner
    
    # Check if router already disabled deepthink
    if plan.stop_reason is not None:
        return _downgrade_output(
            initial_state=initial_state,
            stop_reason=plan.stop_reason,
            request_signature=engine_input.request_signature,
            plan=plan,
            pass_summaries=[],
            validator_failures=0,
        )
    
    # Check pass count bounds (hard max 5)
    if plan.effective_pass_count > 5:
        return _downgrade_output(
            initial_state=initial_state,
            stop_reason="PASS_LIMIT_REACHED",
            request_signature=engine_input.request_signature,
            plan=plan,
            pass_summaries=[],
            validator_failures=0,
        )
    
    # Initialize execution state
    current_state = initial_state
    pass_summaries: List[PassSummary] = []
    validator_strikes = 0
    passes_executed = 0
    start_time_ms = context.now_ms()
    applied_deltas: List[DecisionDelta] = []  # Track applied deltas for signature
    
    # Execute passes in order
    for pass_idx, pass_type in enumerate(plan.pass_plan):
        # Check stop conditions before each pass
        stop_reason = _check_stop_conditions(
            context=context,
            validator_strikes=validator_strikes,
            passes_executed=passes_executed,
            plan=plan,
            start_time_ms=start_time_ms,
        )
        
        if stop_reason:
            # Stop condition triggered
            return _finalize_output(
                final_state=current_state if stop_reason == "SUCCESS_COMPLETED" else initial_state,
                stop_reason=stop_reason,
                downgraded=(stop_reason != "SUCCESS_COMPLETED"),
                validator_failures=validator_strikes,
                pass_summaries=pass_summaries,
                passes_executed=passes_executed,
                request_signature=engine_input.request_signature,
                plan=plan,
                applied_deltas=applied_deltas,
                context=context,
            )
        
        # Get per-pass budget and timeout
        pass_budget = plan.per_pass_budget[pass_idx] if pass_idx < len(plan.per_pass_budget) else 0
        pass_timeout_ms = plan.per_pass_timeout_ms[pass_idx] if pass_idx < len(plan.per_pass_timeout_ms) else 0
        
        # Execute pass
        try:
            pass_result = pass_runner(pass_type, current_state, context)
        except Exception as e:
            # Pass runner failed -> internal inconsistency
            pass_summaries.append(PassSummary(
                pass_type=pass_type,
                executed=False,
                validation_ok=False,
                patch_applied=False,
                cost_units=0,
                duration_ms=0,
                strikes_added=0,
                error=f"Runner exception: {type(e).__name__}",
            ))
            return _downgrade_output(
                initial_state=initial_state,
                stop_reason="INTERNAL_INCONSISTENCY",
                request_signature=engine_input.request_signature,
                plan=plan,
                pass_summaries=pass_summaries,
                validator_failures=validator_strikes,
            )
        
        # Update budget
        context.budget_units_remaining -= pass_result.cost_units
        
        # Check if pass returned error
        if pass_result.error or pass_result.delta is None:
            pass_summaries.append(PassSummary(
                pass_type=pass_type,
                executed=True,
                validation_ok=False,
                patch_applied=False,
                cost_units=pass_result.cost_units,
                duration_ms=pass_result.duration_ms,
                strikes_added=0,
                error=pass_result.error or "No delta returned",
            ))
            passes_executed += 1
            continue
        
        # Validate delta
        validation_result = validate_delta(pass_result.delta, current_strikes=validator_strikes)
        validator_strikes = validation_result.total_strikes
        
        # Check if validation triggered downgrade (2 strikes)
        if validation_result.downgrade:
            pass_summaries.append(PassSummary(
                pass_type=pass_type,
                executed=True,
                validation_ok=False,
                patch_applied=False,
                cost_units=pass_result.cost_units,
                duration_ms=pass_result.duration_ms,
                strikes_added=validation_result.strikes_added,
                error="; ".join(validation_result.errors),
            ))
            return _downgrade_output(
                initial_state=initial_state,
                stop_reason="VALIDATION_FAIL",
                request_signature=engine_input.request_signature,
                plan=plan,
                pass_summaries=pass_summaries,
                validator_failures=validator_strikes,
            )
        
        # Apply delta if validation passed
        patch_applied = False
        if validation_result.ok:
            try:
                current_state = apply_delta(current_state, pass_result.delta)
                patch_applied = True
                applied_deltas.extend(pass_result.delta)  # Track for signature
            except PatchError as e:
                # Patch application failed -> treat as validation strike
                validator_strikes += 1
                if validator_strikes >= 2:
                    pass_summaries.append(PassSummary(
                        pass_type=pass_type,
                        executed=True,
                        validation_ok=False,
                        patch_applied=False,
                        cost_units=pass_result.cost_units,
                        duration_ms=pass_result.duration_ms,
                        strikes_added=1,
                        error=f"Patch error: {str(e)}",
                    ))
                    return _downgrade_output(
                        initial_state=initial_state,
                        stop_reason="VALIDATION_FAIL",
                        request_signature=engine_input.request_signature,
                        plan=plan,
                        pass_summaries=pass_summaries,
                        validator_failures=validator_strikes,
                    )
        
        # Record pass summary
        pass_summaries.append(PassSummary(
            pass_type=pass_type,
            executed=True,
            validation_ok=validation_result.ok,
            patch_applied=patch_applied,
            cost_units=pass_result.cost_units,
            duration_ms=pass_result.duration_ms,
            strikes_added=validation_result.strikes_added,
            error="; ".join(validation_result.errors) if not validation_result.ok else None,
        ))
        
        passes_executed += 1
    
    # All passes completed successfully
    return _finalize_output(
        final_state=current_state,
        stop_reason="SUCCESS_COMPLETED",
        downgraded=False,
        validator_failures=validator_strikes,
        pass_summaries=pass_summaries,
        passes_executed=passes_executed,
        request_signature=engine_input.request_signature,
        plan=plan,
        applied_deltas=applied_deltas,
        context=context,
    )


def _check_stop_conditions(
    context: EngineContext,
    validator_strikes: int,
    passes_executed: int,
    plan: Plan,
    start_time_ms: int,
) -> Optional[str]:
    """
    Check stop conditions in priority order.
    Returns first matching stop reason, or None if no stop.
    """
    # Check in STOP_PRIORITY_ORDER
    for stop_reason in STOP_PRIORITY_ORDER:
        if stop_reason == "ABUSE" and context.abuse_blocked:
            return "ABUSE"
        elif stop_reason == "BREAKER_TRIPPED" and context.breaker_tripped:
            return "BREAKER_TRIPPED"
        elif stop_reason == "BUDGET_EXHAUSTED" and context.budget_units_remaining <= 0:
            return "BUDGET_EXHAUSTED"
        elif stop_reason == "TIMEOUT":
            # Check global timeout (sum of per_pass_timeout_ms)
            total_timeout_ms = sum(plan.per_pass_timeout_ms)
            elapsed_ms = context.now_ms() - start_time_ms
            if elapsed_ms >= total_timeout_ms:
                return "TIMEOUT"
        elif stop_reason == "VALIDATION_FAIL" and validator_strikes >= 2:
            return "VALIDATION_FAIL"
        elif stop_reason == "PASS_LIMIT_REACHED" and passes_executed >= 5:
            return "PASS_LIMIT_REACHED"
    
    return None


def _downgrade_output(
    initial_state: Dict[str, Any],
    stop_reason: str,
    request_signature: str,
    plan: Plan,
    pass_summaries: List[PassSummary],
    validator_failures: int,
    applied_deltas: Optional[List[DecisionDelta]] = None,
    context: Optional[EngineContext] = None,
) -> EngineOutput:
    """
    Create downgraded output (return baseline state).
    """
    # Compute safe decision signature (no user text)
    stable_inputs = _extract_stable_inputs(context) if context else {}
    decision_sig = compute_decision_signature(
        stable_inputs=stable_inputs,
        pass_plan=plan.pass_plan,
        deltas=applied_deltas or [],
        meta={"validator_failures": validator_failures, "stop_reason": stop_reason},
    )
    
    # Build telemetry event
    final_action = initial_state.get("decision", {}).get("action", "")
    telemetry_event = build_telemetry_event(
        pass_count=len(pass_summaries),
        stop_reason=stop_reason,
        validator_failures=validator_failures,
        downgraded=True,
        decision_signature=decision_sig,
        pass_summaries=pass_summaries,
        final_action=final_action if final_action else None,
    )
    
    meta = EngineMeta(
        pass_count_executed=len(pass_summaries),
        stop_reason=stop_reason,
        downgraded=True,
        validator_failures=validator_failures,
        decision_signature=decision_sig,
        pass_summaries=pass_summaries,
        policy={"downgrade_reason": stop_reason},
        telemetry_event=telemetry_event,
    )
    
    return EngineOutput(
        final_state=initial_state,
        meta=meta,
    )


def _finalize_output(
    final_state: Dict[str, Any],
    stop_reason: str,
    downgraded: bool,
    validator_failures: int,
    pass_summaries: List[PassSummary],
    passes_executed: int,
    request_signature: str,
    plan: Plan,
    applied_deltas: List[DecisionDelta],
    context: EngineContext,
) -> EngineOutput:
    """
    Create final output with safe decision signature (no user text).
    """
    # Compute safe decision signature (no user text)
    stable_inputs = _extract_stable_inputs(context)
    decision_sig = compute_decision_signature(
        stable_inputs=stable_inputs,
        pass_plan=plan.pass_plan,
        deltas=applied_deltas,
        meta={"validator_failures": validator_failures, "stop_reason": stop_reason},
    )
    
    # Build telemetry event
    final_action = final_state.get("decision", {}).get("action", "")
    telemetry_event = build_telemetry_event(
        pass_count=passes_executed,
        stop_reason=stop_reason,
        validator_failures=validator_failures,
        downgraded=downgraded,
        decision_signature=decision_sig,
        pass_summaries=pass_summaries,
        final_action=final_action if final_action else None,
    )
    
    meta = EngineMeta(
        pass_count_executed=passes_executed,
        stop_reason=stop_reason,
        downgraded=downgraded,
        validator_failures=validator_failures,
        decision_signature=decision_sig,
        pass_summaries=pass_summaries,
        policy={
            "plan_pass_count": plan.effective_pass_count,
            "executed_pass_count": passes_executed,
        },
        telemetry_event=telemetry_event,
    )
    
    return EngineOutput(
        final_state=final_state,
        meta=meta,
    )


def _extract_stable_inputs(context: EngineContext) -> Dict[str, Any]:
    """
    Extract safe stable inputs from context (no user text).
    """
    stable_inputs = {
        "budget_units_remaining": context.budget_units_remaining,
        "breaker_tripped": context.breaker_tripped,
        "abuse_blocked": context.abuse_blocked,
    }
    
    # Note: request_signature is excluded as it may contain text
    # Only include truly text-free fields
    
    return stable_inputs
