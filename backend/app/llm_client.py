from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Union, Optional

import httpx

from backend.app.config import get_settings
from .enforcement import (
    ExpressionAdapterInput,
    ReasoningAdapterInput,
    ViolationClass,
    build_failure,
    enforce_pre_call,
    parse_reasoning_output,
    validate_expression_output,
)
from .schemas import (
    CognitiveStyle,
    ExpressionPlan,
    Hypothesis,
    IntermediateAnswer,
    Intent,
    ReasoningOutput,
    RenderedMessage,
    UserMessage,
)

logger = logging.getLogger(__name__)


class LLMClient:
    """Model-agnostic HTTP client for the reasoning and expression models.

    IMPORTANT:
    - `call_reasoning_model` is for hidden structured reasoning only.
    - `call_expression_model` is for user-facing expression only.
    - These roles MUST remain separate.
    """

    def __init__(
        self,
        *,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 30.0,
        connect_timeout_seconds: float = 10.0,
        request_id_header: str = "x-request-id",
        request_id_value: Optional[str] = None,
    ) -> None:
        s = get_settings()
        self.api_base = api_base or s.model_base_url or s.model_provider_base_url or s.llm_api_base
        self.api_key = api_key or s.model_api_key or s.llm_api_key
        self.timeout_seconds = timeout_seconds or float(s.model_timeout_seconds)
        self.connect_timeout_seconds = connect_timeout_seconds or float(s.model_connect_timeout_seconds)
        self.request_id_header = request_id_header or s.request_id_header
        self.request_id_value = request_id_value

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_base or not self.api_key:
            raise RuntimeError("LLM configuration missing (api_base / api_key)")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.request_id_value:
            headers[self.request_id_header] = self.request_id_value

        timeout = httpx.Timeout(self.timeout_seconds, connect=self.connect_timeout_seconds)

        with httpx.Client(timeout=timeout) as client:
            try:
                resp = client.post(self.api_base, headers=headers, json=payload)
                resp.raise_for_status()
                try:
                    data = resp.json()
                except ValueError as exc:
                    raise build_failure(
                        violation_class=ViolationClass.STRUCTURAL_VIOLATION,
                        reason="LLM adapter returned non-JSON response",
                        detail={"error": str(exc)},
                    ) from exc
            except httpx.TimeoutException as exc:
                raise build_failure(
                    violation_class=ViolationClass.EXTERNAL_DEPENDENCY_FAILURE,
                    reason="LLM adapter HTTP request timeout",
                    detail={"error": str(exc)},
                ) from exc
            except httpx.HTTPError as exc:
                raise build_failure(
                    violation_class=ViolationClass.EXTERNAL_DEPENDENCY_FAILURE,
                    reason="LLM adapter HTTP request failed",
                    detail={"error": str(exc)},
                ) from exc

        return data

    # ------------------------
    # LLM #1: Reasoning engine
    # ------------------------
    def call_reasoning_model(
        self,
        user_message: UserMessage,
        intent: Intent,
        style: CognitiveStyle,
        session_summary: Dict[str, Any],
        current_hypotheses: list[Hypothesis],
    ) -> ReasoningOutput:
        """Call the reasoning model.

        The prompt MUST instruct the model to:
        - Produce ONLY structured reasoning objects (no user-facing prose).
        - Treat conclusions as hypotheses with uncertainties.
        - Follow the ReasoningOutput schema.
        """

        adapter_input = ReasoningAdapterInput(
            user_message=user_message,
            intent=intent,
            cognitive_style=style,
            session_summary=session_summary,
            current_hypotheses=current_hypotheses,
        )
        enforce_pre_call("reasoning", adapter_input)

        logger.info(
            "[LLM#1] Reasoning input",
            extra={
                "user_message": adapter_input.user_message.model_dump(),
                "intent": adapter_input.intent.model_dump(),
                "style": adapter_input.cognitive_style.model_dump(),
                "session_summary": adapter_input.session_summary,
                "current_hypotheses": [h.model_dump() for h in adapter_input.current_hypotheses],
            },
        )

        system_prompt = (
            "You are an internal reasoning engine for a cognitive conversational system. "
            "You NEVER speak to the user and you NEVER produce user-facing prose. "
            "You only produce structured reasoning outputs that follow a JSON schema. "
            "Treat all conclusions as hypotheses with uncertainty. "
            "Do NOT use second-person language such as 'you' or 'your' in any field.\n\n"
            "Here is an EXAMPLE of the JSON SHAPE you must follow (structure only, not content):\n"
            "{"
            "  \"reasoning_trace\": {"
            "    \"steps\": ["
            "      { \"id\": \"S1\", \"description\": \"Identify core question.\", \"related_hypotheses\": [], \"status\": \"proposed\" }"
            "    ],"
            "    \"summary\": \"Short internal summary of what is going on.\""
            "  },"
            "  \"updated_hypotheses\": ["
            "    { \"id\": \"H1\", \"claim\": \"Example claim.\", \"support_score_delta\": 0.1, \"refute_score_delta\": 0.0, \"justification\": \"Why this changed.\" }"
            "  ],"
            "  \"intermediate_answer\": {"
            "    \"goals\": [\"What the expression layer should achieve.\"],"
            "    \"key_points\": [\"Key point 1.\"],"
            "    \"assumptions_and_uncertainties\": [ { \"assumption\": \"Example assumption.\", \"confidence\": 0.5 } ],"
            "    \"checks_for_understanding\": [\"Example check.\"]"
            "  }"
            "}"
        )

        reasoning_instruction = {
            "role": "system",
            "content": system_prompt,
        }

        # The content here mirrors the spec from STEP 2; we do not tune, we just enforce structure.
        user_payload = {
            "user_message": adapter_input.user_message.model_dump(),
            "intent": adapter_input.intent.model_dump(),
            "cognitive_style": adapter_input.cognitive_style.model_dump(),
            "session_summary": adapter_input.session_summary,
            "current_hypotheses": [h.model_dump() for h in adapter_input.current_hypotheses],
            "output_schema": {
                "reasoning_trace": {
                    "steps": "list of reasoning steps with id, description, related_hypotheses, status",
                    "summary": "short internal summary of what is going on",
                },
                "updated_hypotheses": "list of hypothesis deltas with id, claim, support_score_delta, refute_score_delta, justification",
                "intermediate_answer": {
                    "goals": "list of goals for what the expression layer should achieve",
                    "key_points": "list of key points to convey",
                    "assumptions_and_uncertainties": "list of assumptions with confidence",
                    "checks_for_understanding": "list of checks-for-understanding prompts",
                },
            },
        }

        payload = {
            "model": settings.llm_reasoning_model,
            "messages": [
                reasoning_instruction,
                {"role": "user", "content": json.dumps(user_payload)},
            ],
        }

        def _invoke_reasoning(p: Dict[str, Any]) -> ReasoningOutput:
            data = self._post(p)
            try:
                content = data["choices"][0]["message"]["content"]
            except Exception as exc:  # noqa: BLE001
                logger.error("[LLM#1] Unexpected response structure", exc_info=exc)
                raise build_failure(
                    ViolationClass.STRUCTURAL_VIOLATION,
                    "Reasoning adapter response missing expected choices/message/content",
                ) from exc

            return parse_reasoning_output(content)

        output = _invoke_reasoning(payload)

        # Second-person ban post-check (logging only)
        summary_text = output.reasoning_trace.summary
        step_text = " ".join(step.description for step in output.reasoning_trace.steps)
        if re.search(r"\b(you|your)\b", summary_text, flags=re.IGNORECASE) or re.search(
            r"\b(you|your)\b", step_text, flags=re.IGNORECASE
        ):
            logger.warning(
                "[LLM#1] Second-person language detected in reasoning output",
                extra={
                    "summary": summary_text,
                    "steps": [s.description for s in output.reasoning_trace.steps],
                },
            )

        logger.info("[LLM#1] Reasoning output", extra={"output": output.model_dump()})
        return output

    # ---------------------------
    # LLM #2: Expression renderer
    # ---------------------------
    def call_expression_model(
        self,
        user_message: UserMessage,
        style: CognitiveStyle,
        plan: ExpressionPlan,
        intermediate: IntermediateAnswer,
    ) -> RenderedMessage:
        """Call the expression model.

        The prompt MUST instruct the model to:
        - Use only the intermediate_answer + expression_plan + style + raw user message.
        - Preserve logic exactly, without adding new technical claims.
        - Produce a single natural-language reply string.
        """

        adapter_input = ExpressionAdapterInput(
            user_message=user_message,
            cognitive_style=style,
            expression_plan=plan,
            intermediate_answer=intermediate,
        )
        enforce_pre_call("expression", adapter_input)

        logger.info(
            "[LLM#2] Expression input",
            extra={
                "user_message": adapter_input.user_message.model_dump(),
                "style": adapter_input.cognitive_style.model_dump(),
                "plan": adapter_input.expression_plan.model_dump(),
                "intermediate_answer": adapter_input.intermediate_answer.model_dump(),
            },
        )

        system_prompt = (
            "You are the expression layer of a cognitive conversational system. "
            "You do NOT perform deep reasoning yourself. Instead, you receive a structured intermediate answer "
            "and an expression plan, and you turn them into a natural response that matches the user's style. "
            "You MUST NOT introduce new technical claims or teach unrelated material. \n"
            "Avoid tutor or lecture tone; sound like a thinking partner. Do NOT frame your response as a lesson, "
            "tutorial, course, or walkthrough. Do NOT use phrases like 'Let's learn', 'Today we will', 'Step 1', "
            "'Step 2', or 'In this tutorial', and avoid headings or numbered sections unless the user explicitly "
            "asks for them. \n"
            "Preserve the modality of the intermediate answer: if key points use words like 'often', 'usually', "
            "'can help', or 'tends to', you must NOT upgrade them to 'always', 'must', 'best practice', or "
            "'you should'. \n"
            "Stay strictly within the scope of intermediate_answer.goals and intermediate_answer.key_points. If you "
            "believe more background is needed, ask the user a short question about what they want to see next "
            "instead of starting a new explanation on your own. \n"
            "If the user has given an explicit style or length request (for example, keep it short, be casual, be "
            "formal), that explicit request takes priority over any inferred style."
        )

        expression_instruction = {"role": "system", "content": system_prompt}

        user_payload = {
            "user_message": adapter_input.user_message.model_dump(),
            "cognitive_style": adapter_input.cognitive_style.model_dump(),
            "expression_plan": adapter_input.expression_plan.model_dump(),
            "intermediate_answer": adapter_input.intermediate_answer.model_dump(),
        }

        payload = {
            "model": settings.llm_expression_model,
            "messages": [
                expression_instruction,
                {"role": "user", "content": json.dumps(user_payload)},
            ],
        }

        data = self._post(payload)

        try:
            content = data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            logger.error("[LLM#2] Unexpected response structure", exc_info=exc)
            raise build_failure(
                ViolationClass.STRUCTURAL_VIOLATION,
                "Expression adapter response missing expected choices/message/content",
            ) from exc

        rendered = validate_expression_output(content, intermediate=adapter_input.intermediate_answer)
        logger.info("[LLM#2] Expression output", extra={"rendered": rendered.model_dump()})
        return rendered
