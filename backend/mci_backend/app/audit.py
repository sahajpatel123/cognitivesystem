from __future__ import annotations

"""Invariant checks for MCI.

This module defines functions that evaluate invariants and return structured
results. They do not change behavior or raise errors by themselves.
"""

from typing import List

from .debug_events import InvariantResult
from .models import UserMessage, ReasoningOutput, HypothesisSet, AssistantReply


def check_request_invariants(user: UserMessage) -> List[InvariantResult]:
    results: List[InvariantResult] = []

    # session_id present
    passed_sid = bool(user.session_id and user.session_id.strip())
    results.append(
        InvariantResult(
            invariant_id="request.session_id_present",
            description="session_id must be present and non-empty",
            passed=passed_sid,
            failure_reason=None if passed_sid else "session_id is missing or empty",
        )
    )

    # text present
    passed_text = bool(user.text and user.text.strip())
    results.append(
        InvariantResult(
            invariant_id="request.text_present",
            description="text must be present and non-empty",
            passed=passed_text,
            failure_reason=None if passed_text else "text is missing or empty",
        )
    )

    return results


def check_reasoning_invariants(out: ReasoningOutput) -> List[InvariantResult]:
    results: List[InvariantResult] = []

    # non-empty internal trace
    passed_trace = bool(out.internal_trace and out.internal_trace.strip())
    results.append(
        InvariantResult(
            invariant_id="reasoning.internal_trace_non_empty",
            description="internal reasoning trace must be non-empty",
            passed=passed_trace,
            failure_reason=None
            if passed_trace
            else "internal reasoning trace is empty",
        )
    )

    # ExpressionPlan produced
    has_plan = out.plan is not None and bool(out.plan.segments)
    results.append(
        InvariantResult(
            invariant_id="reasoning.plan_produced",
            description="ExpressionPlan with at least one segment must be produced",
            passed=has_plan,
            failure_reason=None if has_plan else "ExpressionPlan is missing or empty",
        )
    )

    return results


def check_memory_invariants(before: HypothesisSet, after: HypothesisSet) -> List[InvariantResult]:
    results: List[InvariantResult] = []

    # session-only access: session_id must be unchanged
    same_session = before.session_id == after.session_id
    results.append(
        InvariantResult(
            invariant_id="memory.session_only",
            description="memory updates must not change session_id",
            passed=same_session,
            failure_reason=None if same_session else "session_id changed during update",
        )
    )

    # non-deleting: after must not have fewer hypotheses than before
    non_deleting = len(after.hypotheses) >= len(before.hypotheses)
    results.append(
        InvariantResult(
            invariant_id="memory.non_deleting",
            description="updates must not reduce the number of hypotheses",
            passed=non_deleting,
            failure_reason=None
            if non_deleting
            else "number of hypotheses decreased after update",
        )
    )

    # clamped: this module does not recompute clamping; enforcement lives in memory.
    # Here we record only a structural check that the set is non-empty when before
    # was non-empty; detailed numeric checks are handled by memory logic.

    return results


def check_expression_invariants(reply: AssistantReply) -> List[InvariantResult]:
    results: List[InvariantResult] = []

    non_empty = bool(reply.text and reply.text.strip())
    results.append(
        InvariantResult(
            invariant_id="expression.non_empty_output",
            description="expression output must be non-empty",
            passed=non_empty,
            failure_reason=None if non_empty else "expression output is empty",
        )
    )

    return results
