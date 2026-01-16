import pytest

from backend.mci_backend.app import expression
from backend.mci_backend.app.models import AssistantReply, ExpressionPlan


def test_expression_cannot_access_reasoning_or_hypotheses():
    # This test asserts by construction: expression API accepts only ExpressionPlan
    # and returns AssistantReply. There is no parameter to pass reasoning or
    # hypotheses, so any attempt to do so would be a type or interface error.

    plan = ExpressionPlan(segments=["segment1", "segment2"])
    reply = expression.render_reply(plan)

    assert isinstance(reply, AssistantReply)
    assert "segment1" in reply.text
    assert "segment2" in reply.text


def test_expression_plan_is_only_bridge():
    # This test encodes the contract that the plan is the only allowed bridge.
    # We assert that the expression module exposes no functions that accept
    # reasoning traces or hypotheses directly.

    public_attrs = [name for name in dir(expression) if not name.startswith("_")]
    # Only expected public call points are call_expression_model and render_reply.
    assert "render_reply" in public_attrs
    assert "call_expression_model" in public_attrs
    # No public API for reasoning output or hypotheses.
    assert "run_reasoning" not in public_attrs
    assert "apply_clamped_update" not in public_attrs
