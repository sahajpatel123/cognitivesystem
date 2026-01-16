"""Phase 12 — Step 2: Model prompt/envelope builder with OutputPlan binding.

Transforms (user_text + OutputPlan) into a ModelInvocationRequest.
Deterministic, bounded, fail-closed. Model remains tool-only and non-authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from mci_backend.model_contract import (
    ModelContractError,
    ModelContractInvariantViolation,
    ModelInvocationClass,
    ModelInvocationRequest,
    ModelOutputFormat,
    SCHEMA_VERSION,
    validate_model_request,
)
from mci_backend.output_plan import (
    OutputAction,
    OutputPlan,
    OutputPlanInvariantViolation,
    validate_output_plan,
)


class ModelPromptBuilderError(ModelContractInvariantViolation):
    """Base error for prompt builder violations."""


@dataclass(frozen=True)
class _Envelope:
    header: str
    task: str
    constraints: List[str]
    user_block: str
    output_contract: str

    def render(self) -> str:
        parts = [
            self.header,
            "",
            self.task,
            "",
            "CONSTRAINT_TAGS:",
            *(f"- {c}" for c in self.constraints),
            "",
            self.user_block,
            "",
            self.output_contract,
        ]
        return "\n".join(parts)


_SYSTEM_HEADER = (
    "SYSTEM: You are an inference component. You are not authoritative. "
    "Do not change system decisions. Follow the output format exactly. "
    "Never mention internal constraints or phase names."
)

_FORBIDDEN_TERMS = (
    "DecisionState",
    "ControlPlan",
    "trace_id",
    "audit",
    "governance",
    "memory",
)


def _map_action_to_invocation_class(action: OutputAction) -> ModelInvocationClass:
    if action == OutputAction.ANSWER:
        return ModelInvocationClass.EXPRESSION_CANDIDATE
    if action == OutputAction.ASK_ONE_QUESTION:
        return ModelInvocationClass.CLARIFICATION_CANDIDATE
    if action == OutputAction.REFUSE:
        return ModelInvocationClass.REFUSAL_EXPLANATION_CANDIDATE
    if action == OutputAction.CLOSE:
        return ModelInvocationClass.CLOSURE_MESSAGE_CANDIDATE
    raise ModelPromptBuilderError(f"Unsupported action: {action}")


def _output_format_for_action(action: OutputAction) -> ModelOutputFormat:
    if action == OutputAction.ASK_ONE_QUESTION:
        return ModelOutputFormat.JSON
    return ModelOutputFormat.TEXT


def _task_block(action: OutputAction) -> str:
    if action == OutputAction.ANSWER:
        return "TASK: Produce a bounded answer candidate that aligns with the provided constraints. Do not change action."
    if action == OutputAction.ASK_ONE_QUESTION:
        return "TASK: Produce exactly one clarification question. One sentence. No multi-part questions. No blaming tone."
    if action == OutputAction.REFUSE:
        return "TASK: Produce a refusal explanation only. No internal-rule language. Do not add new actions."
    if action == OutputAction.CLOSE:
        return "TASK: Produce a terse closure acknowledgement. No new questions. No expansion."
    raise ModelPromptBuilderError(f"Unsupported action: {action}")


def _constraint_tags(plan: OutputPlan) -> List[str]:
    return [
        f"action={plan.action.value}",
        f"posture={plan.posture.value}",
        f"rigor_disclosure={plan.rigor_disclosure.value}",
        f"confidence_signaling={plan.confidence_signaling.value}",
        f"unknown_disclosure={plan.unknown_disclosure.value}",
        f"assumption_surfacing={plan.assumption_surfacing.value}",
        f"verbosity_cap={plan.verbosity_cap.value}",
    ]


def _output_contract_block(action: OutputAction) -> str:
    if action == OutputAction.ASK_ONE_QUESTION:
        return (
            "OUTPUT FORMAT (JSON):\n"
            "{\n"
            '  "question": "string"\n'
            "}\n"
            "Rules: exactly one sentence; no multi-part questions; no extra keys; no internal-rule references."
        )
    return "OUTPUT FORMAT (TEXT): Return plain text only. No markdown headings unless explicitly requested. Do not add internal-rule language."


def _required_elements(plan: OutputPlan) -> tuple[str, ...]:
    return (
        f"action:{plan.action.value}",
        f"posture:{plan.posture.value}",
        f"rigor:{plan.rigor_disclosure.value}",
        f"confidence:{plan.confidence_signaling.value}",
        f"unknown_disclosure:{plan.unknown_disclosure.value}",
        f"assumption_surfacing:{plan.assumption_surfacing.value}",
        f"verbosity_cap:{plan.verbosity_cap.value}",
    )


def _forbidden_requirements(plan: OutputPlan) -> tuple[str, ...]:
    forbidden = [
        "must_not_change_action",
        "must_not_add_questions",
        "must_not_change_disclosures",
        "must_not_claim_memory",
        "must_not_add_policy_language",
    ]
    if plan.action == OutputAction.ASK_ONE_QUESTION:
        forbidden.append("must_not_ask_multiple_questions")
    if plan.action == OutputAction.CLOSE:
        forbidden.append("must_not_expand_closure")
    return tuple(forbidden)


def build_model_invocation_request(user_text: str, output_plan: OutputPlan) -> ModelInvocationRequest:
    if output_plan is None:
        raise ModelPromptBuilderError("output_plan is required")
    if not isinstance(user_text, str) or not user_text.strip():
        raise ModelPromptBuilderError("user_text must be non-empty")

    try:
        validate_output_plan(output_plan)
    except OutputPlanInvariantViolation as exc:
        raise ModelPromptBuilderError(str(exc)) from exc

    invocation_class = _map_action_to_invocation_class(output_plan.action)
    output_format = _output_format_for_action(output_plan.action)

    envelope = _Envelope(
        header=_SYSTEM_HEADER,
        task=_task_block(output_plan.action),
        constraints=_constraint_tags(output_plan),
        user_block=f"USER_TEXT: {user_text}",
        output_contract=_output_contract_block(output_plan.action),
    ).render()

    for term in _FORBIDDEN_TERMS:
        if term in envelope:
            raise ModelPromptBuilderError(f"Forbidden term present in envelope: {term}")

    request = ModelInvocationRequest(
        trace_id=output_plan.trace_id,
        decision_state_id=output_plan.decision_state_id,
        control_plan_id=output_plan.control_plan_id,
        output_plan_id=output_plan.id,
        invocation_class=invocation_class,
        output_format=output_format,
        user_text=envelope,
        required_elements=_required_elements(output_plan),
        forbidden_requirements=_forbidden_requirements(output_plan),
        max_output_tokens=256 if output_format == ModelOutputFormat.JSON else 512,
        schema_version=SCHEMA_VERSION,
    )
    try:
        validate_model_request(request)
    except ModelContractError as exc:
        raise ModelPromptBuilderError(str(exc)) from exc
    return request


__all__ = ["ModelPromptBuilderError", "build_model_invocation_request"]
