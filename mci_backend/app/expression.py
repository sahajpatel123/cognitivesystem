from __future__ import annotations

"""Expression stage for MCI.

Single-pass expression that:
- Receives ONLY an ExpressionPlan.
- Has NO access to reasoning traces or hypotheses.
- Produces final user-visible text.

Must not introduce new claims beyond the plan.
"""

from .models import ExpressionPlan, AssistantReply


def call_expression_model(plan: ExpressionPlan) -> str:
    """Minimal stand-in for an expression model.

    Contract mapping:
    - Input: ExpressionPlan only.
    - Output: text derived directly from plan segments.
    """
    return "\n".join(plan.segments)


def render_reply(plan: ExpressionPlan) -> AssistantReply:
    """Render final user reply from an ExpressionPlan.

    Contract mapping:
    - Expression sees only the plan.
    - It must not add content beyond plan segments.
    - It must fail hard on empty output.
    """
    text = call_expression_model(plan)
    if not text.strip():
        raise RuntimeError("Expression produced empty output from plan.")
    return AssistantReply(text=text)
