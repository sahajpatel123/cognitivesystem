"""Phase 12 — Step 6: Deterministic fallback rendering (no model, fail-closed)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from backend.mci_backend.control_plan import ControlPlan
from backend.mci_backend.decision_state import DecisionState
from backend.mci_backend.output_plan import (
    AssumptionSurfacingMode,
    ClosureRenderingMode,
    ExpressionPosture,
    OutputAction,
    OutputPlan,
    RefusalCategory,
    RefusalExplanationMode,
    RigorDisclosureLevel,
    UnknownDisclosureMode,
    VerbosityCap,
)


class FallbackRenderingError(Exception):
    """Raised when deterministic fallback cannot render safely."""


@dataclass(frozen=True)
class FallbackContent:
    text: Optional[str]
    json: Optional[Dict[str, object]]


_VERBOSITY_CAPS = {
    VerbosityCap.TERSE: 220,
    VerbosityCap.NORMAL: 600,
    VerbosityCap.DETAILED: 1200,
}

_QUESTION_TEMPLATES = {
    "INFORMATIONAL": "What is the single most important detail I should focus on?",
    "SAFETY_GUARD": "What is the main safety or compliance concern you see here?",
    "CONSENT": "Do you consent to proceed under the current constraints?",
    "OTHER_BOUNDARY": "What boundary or constraint matters most right now?",
}

_REFUSAL_TEMPLATES = {
    RefusalCategory.RISK_REFUSAL: "I have to refuse because proceeding is unsafe.",
    RefusalCategory.IRREVERSIBILITY_REFUSAL: "I have to refuse because it seems irreversible with limited context.",
    RefusalCategory.THIRD_PARTY_REFUSAL: "I have to refuse because it affects others without clarity.",
    RefusalCategory.GOVERNANCE_REFUSAL: "I have to refuse because this request is blocked for safety reasons.",
    RefusalCategory.CAPABILITY_REFUSAL: "I have to refuse because I cannot safely provide that.",
    RefusalCategory.EPISTEMIC_REFUSAL: "I have to refuse because there is not enough reliable information.",
}


def _cap_length(text: str, verbosity: VerbosityCap) -> str:
    limit = _VERBOSITY_CAPS.get(verbosity, _VERBOSITY_CAPS[VerbosityCap.NORMAL])
    if len(text) <= limit:
        return text
    return text[:limit].rstrip()


def _sanitize(text: str) -> str:
    if text is None:
        return ""
    sanitized = text.replace("```", "")
    sanitized = sanitized.replace("\r\n", "\n").replace("\r", "\n")
    return sanitized.strip()


def _render_unknown_line(plan: OutputPlan, decision_state: DecisionState) -> Optional[str]:
    if plan.unknown_disclosure == UnknownDisclosureMode.NONE:
        return None
    if decision_state.explicit_unknown_zone:
        return "Unknown: Some factors are not yet known."
    return None


def _render_assumption_line(plan: OutputPlan) -> Optional[str]:
    if plan.assumption_surfacing == AssumptionSurfacingMode.NONE:
        return None
    if plan.assumption_surfacing in (AssumptionSurfacingMode.LIGHT, AssumptionSurfacingMode.REQUIRED):
        return "Assumption: Proceeding with limited context only."
    return None


def _render_confidence_line(plan: OutputPlan) -> Optional[str]:
    if plan.confidence_signaling.name == "EXPLICIT":
        return "Confidence: Cautious."
    if plan.confidence_signaling.name == "GUARDED":
        return "Confidence: Guarded."
    return None


def _render_answer(plan: OutputPlan, decision_state: DecisionState) -> str:
    """
    Render a helpful fallback answer when LLM is unavailable.
    CRITICAL: This must return a real answer, NOT meta scaffolding.
    The UI should never see "Answer: Providing a concise response..." text.
    """
    # Return a helpful fallback message that explains the service is temporarily limited
    # This is better than meta scaffolding which confuses users
    fallback_text = (
        "I'm currently operating in a limited mode and may not be able to provide "
        "a complete answer. Please try rephrasing your question or try again shortly."
    )
    
    return _cap_length(_sanitize(fallback_text), plan.verbosity_cap)


def _render_question(plan: OutputPlan) -> Dict[str, object]:
    spec = plan.question_spec
    if spec is None:
        raise FallbackRenderingError("question_spec required for ASK_ONE_QUESTION")
    template = _QUESTION_TEMPLATES.get(spec.question_class.value, "What is the single key detail I should know?")
    question = _sanitize(template)
    if "?" not in question:
        question = f"{question}?"
    # ensure exactly one question mark at end
    question = question.split("?")[0].strip() + "?"
    return {
        "question": question,
        "question_class": spec.question_class.value,
        "priority_reason": spec.priority_reason.value,
    }


def _render_refusal(plan: OutputPlan) -> str:
    spec = plan.refusal_spec
    if spec is None:
        raise FallbackRenderingError("refusal_spec required for REFUSE")
    template = _REFUSAL_TEMPLATES.get(spec.refusal_category, "I have to refuse because it is not safe to proceed.")
    if spec.explanation_mode == RefusalExplanationMode.REDIRECT_TO_SAFE_FRAME:
        template = f"{template} Let's stay within a safer scope."
    elif spec.explanation_mode == RefusalExplanationMode.BOUNDED_EXPLANATION:
        template = f"{template} This keeps you safe."
    rendered = _sanitize(template)
    return _cap_length(rendered, plan.verbosity_cap)


def _render_close(plan: OutputPlan) -> str:
    spec = plan.closure_spec
    if spec is None:
        raise FallbackRenderingError("closure_spec required for CLOSE")
    mode = spec.rendering_mode
    if mode == ClosureRenderingMode.SILENCE:
        return ""
    if mode == ClosureRenderingMode.CONFIRM_CLOSURE:
        return "Got it. Closing out."
    if mode == ClosureRenderingMode.BRIEF_SUMMARY_AND_STOP:
        return "Noted. Closing this interaction now."
    raise FallbackRenderingError("Unknown closure rendering mode.")


def render_fallback_content(
    *,
    user_text: str,
    decision_state: DecisionState,
    control_plan: Optional[ControlPlan],
    output_plan: OutputPlan,
) -> FallbackContent:
    """Deterministically render fallback content for the given OutputPlan."""
    if output_plan.action == OutputAction.ANSWER:
        return FallbackContent(text=_render_answer(output_plan, decision_state), json=None)
    if output_plan.action == OutputAction.ASK_ONE_QUESTION:
        return FallbackContent(text=None, json=_render_question(output_plan))
    if output_plan.action == OutputAction.REFUSE:
        return FallbackContent(text=_render_refusal(output_plan), json=None)
    if output_plan.action == OutputAction.CLOSE:
        return FallbackContent(text=_render_close(output_plan), json=None)
    raise FallbackRenderingError("Unsupported action for fallback.")


def render_fallback_text(
    user_text: str,
    decision_state: DecisionState,
    control_plan: Optional[ControlPlan],
    output_plan: OutputPlan,
) -> str:
    """Convenience wrapper returning text-only fallback (for non-question actions)."""
    content = render_fallback_content(
        user_text=user_text,
        decision_state=decision_state,
        control_plan=control_plan,
        output_plan=output_plan,
    )
    if content.text is None:
        raise FallbackRenderingError("Fallback text requested for non-text action.")
    return content.text


__all__ = ["FallbackRenderingError", "FallbackContent", "render_fallback_content", "render_fallback_text"]
