from __future__ import annotations

"""Reasoning stage for MCI.

Single-pass reasoning that:
- Receives user message + current hypotheses.
- Produces an internal reasoning trace.
- Proposes hypothesis updates.
- Produces an ExpressionPlan.

No retries. No fallbacks. No optimizations.
"""

from .models import UserMessage, HypothesisSet, ReasoningOutput, ExpressionPlan
from . import reasoning_runtime


def call_reasoning_model(prompt: str) -> str:
    """Deterministic reasoning model adapter.

    Delegates to the reference-only deterministic backend. No retries,
    no fallbacks, and no external dependencies.
    """
    return reasoning_runtime.call_reasoning_backend(prompt)


def build_reasoning_prompt(user: UserMessage, hypotheses: HypothesisSet) -> str:
    """Build a minimal prompt that encodes the user message and hypotheses.

    Contract mapping:
    - Uses only current session hypotheses.
    - Does not include any identity information.
    """
    hyp_str = ", ".join(f"{h.key}={h.value:.2f}" for h in hypotheses.hypotheses)
    if not hyp_str:
        hyp_str = "none"
    return f"USER: {user.text}\nHYPOTHESES: {hyp_str}"


def interpret_reasoning_output(raw: str | None, current_h: HypothesisSet) -> ReasoningOutput:
    """Interpret raw reasoning into proposed hypotheses and an expression plan.

    MCI behavior:
    - Proposed hypotheses: identical to current_h (no change) for minimality.
    - Expression plan: built directly from raw reasoning text.

    Contract mapping:
    - internal_trace: kept internal only.
    - proposed_hypotheses: candidate set for clamped update.
    - plan: the only structure passed to expression.
    """
    if raw is None or not isinstance(raw, str) or not raw.strip():
        # Hard failure: empty reasoning is a contract violation.
        raise RuntimeError("Reasoning model returned empty output.")

    proposed = current_h
    plan = ExpressionPlan(segments=[raw])

    return ReasoningOutput(
        internal_trace=raw,
        proposed_hypotheses=proposed,
        plan=plan,
    )


def run_reasoning(user: UserMessage, current_h: HypothesisSet) -> ReasoningOutput:
    """Run the single reasoning stage.

    Contract mapping:
    - Single call to reasoning model.
    - Input: user + session-local hypotheses.
    - Output: internal trace, proposed hypotheses, expression plan.
    """
    prompt = build_reasoning_prompt(user, current_h)
    raw = call_reasoning_model(prompt)
    return interpret_reasoning_output(raw, current_h)
