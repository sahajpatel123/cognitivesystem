from __future__ import annotations

"""Runtime contract checks for MCI.

This module enforces invariants required by the Cognitive Contract:
- Stage isolation.
- Non-empty expression output.
- Forbidden data access checks at boundaries.

Violations must raise errors immediately.

It also exposes thin wrappers that return structured invariant results for
observability, without altering behavior.
"""

from typing import List

from .models import ReasoningOutput, ExpressionPlan, AssistantReply, UserMessage, HypothesisSet
from .debug_events import InvariantResult
from . import audit


def assert_stage_isolation(reasoning_out: ReasoningOutput) -> None:
    """Ensure stage outputs respect isolation constraints.

    Contract mapping:
    - ReasoningOutput is internal; only its ExpressionPlan may cross to expression.
    - Expression must not see internal_trace or hypotheses.

    This check confirms that the plan is present and non-empty.
    """
    if reasoning_out.plan is None:
        raise RuntimeError("Missing ExpressionPlan in reasoning output.")
    if not isinstance(reasoning_out.plan, ExpressionPlan):
        raise RuntimeError("Invalid plan type in reasoning output.")
    if not reasoning_out.plan.segments:
        raise RuntimeError("ExpressionPlan has no segments.")


def assert_expression_non_empty(reply: AssistantReply) -> None:
    """Ensure expression output is non-empty.

    Contract mapping:
    - Empty user-visible output is treated as a violation.
    """
    if not reply.text or not reply.text.strip():
        raise RuntimeError("AssistantReply is empty.")


# Optional structured invariant accessors for observability.

def request_invariant_results(user: UserMessage) -> List[InvariantResult]:
    """Return request boundary invariant results without changing behavior."""

    return audit.check_request_invariants(user)


def reasoning_invariant_results(out: ReasoningOutput) -> List[InvariantResult]:
    """Return reasoning invariant results without changing behavior."""

    return audit.check_reasoning_invariants(out)


def memory_invariant_results(before: HypothesisSet, after: HypothesisSet) -> List[InvariantResult]:
    """Return memory invariant results without changing behavior."""

    return audit.check_memory_invariants(before, after)


def expression_invariant_results(reply: AssistantReply) -> List[InvariantResult]:
    """Return expression invariant results without changing behavior."""

    return audit.check_expression_invariants(reply)
