from __future__ import annotations

import logging
import time
from typing import List

from .intent_style import infer_intent_and_style
from .llm_client import LLMClient
from .memory import (
    load_cognitive_style,
    load_hypotheses,
    load_session_summary,
    save_cognitive_style,
    save_hypotheses,
    save_session_summary,
)
from .schemas import (
    ChatResponse,
    CognitiveStyle,
    ExpressionPlan,
    Hypothesis,
    HypothesisDelta,
    Intent,
    IntermediateAnswer,
    RenderedMessage,
)

logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(self) -> None:
        self.llm = LLMClient()

    def handle_message(self, session_id: str, text: str) -> ChatResponse:
        # 1) Intent + style + user message
        intent, inferred_style, user_message = infer_intent_and_style(text)

        # 2) Load session memory
        stored_style = load_cognitive_style(session_id)
        style = self._merge_styles(stored_style, inferred_style)
        hypotheses = load_hypotheses(session_id)
        session_summary = load_session_summary(session_id)

        logger.info(
            "[Conversation] Start",
            extra={
                "session_id": session_id,
                "user_message": user_message.model_dump(),
                "intent": intent.model_dump(),
                "style": style.model_dump(),
                "hypotheses": [h.model_dump() for h in hypotheses],
                "session_summary": session_summary.model_dump(),
            },
        )

        # 3) Hidden reasoning (LLM #1)
        reasoning_output = self.llm.call_reasoning_model(
            user_message=user_message,
            intent=intent,
            style=style,
            session_summary=session_summary.model_dump(),
            current_hypotheses=hypotheses,
        )

        # 4) Update beliefs (soft, no deletions)
        updated_hypotheses = self._apply_hypothesis_deltas(hypotheses, reasoning_output.updated_hypotheses)
        save_hypotheses(session_id, updated_hypotheses)

        # Session summary update is minimal in this slice
        save_cognitive_style(session_id, style)
        save_session_summary(session_id, session_summary)

        # 5) Build expression plan (no LLM, simple rules)
        plan = self._build_expression_plan(style)

        # 6) Expression rendering (LLM #2, user-facing only)
        rendered: RenderedMessage = self.llm.call_expression_model(
            user_message=user_message,
            style=style,
            plan=plan,
            intermediate=reasoning_output.intermediate_answer,
        )

        # Boundary drift detection: look for strong-modality language that
        # might harden or invent logic relative to the intermediate answer.
        self._detect_boundary_drift(
            rendered=rendered,
            intermediate=reasoning_output.intermediate_answer,
        )

        # Soft expression constraint: paragraph budget observation only.
        max_paragraphs = plan.constraints.get("max_paragraphs")
        if isinstance(max_paragraphs, int) and max_paragraphs > 0:
            paragraphs = [p for p in rendered.text.split("\n\n") if p.strip()]
            if len(paragraphs) > max_paragraphs:
                logger.info(
                    "[Expression] Paragraph limit exceeded",
                    extra={
                        "session_id": session_id,
                        "max_paragraphs": max_paragraphs,
                        "actual_paragraphs": len(paragraphs),
                    },
                )

        logger.info(
            "[Conversation] End",
            extra={
                "session_id": session_id,
                "rendered": rendered.model_dump(),
            },
        )

        return ChatResponse(message=rendered.text)

    @staticmethod
    def _merge_styles(
        stored: CognitiveStyle | None, inferred: CognitiveStyle
    ) -> CognitiveStyle:
        if stored is None:
            return inferred
        # Very light merge: keep stored abstraction/analogies, use latest overrides
        return CognitiveStyle(
            abstraction_level=stored.abstraction_level,
            formality=stored.formality,
            preferred_analogies=stored.preferred_analogies,
            overrides=inferred.overrides or stored.overrides,
        )

    @staticmethod
    def _apply_hypothesis_deltas(
        existing: List[Hypothesis], deltas: List[HypothesisDelta]
    ) -> List[Hypothesis]:
        """Apply hypothesis deltas with numeric safety.

        - Clamp each delta to a maximum absolute value to avoid
          overconfident jumps.
        - Never delete hypotheses; only update or create.
        """

        now = int(time.time())
        by_id = {h.id: h for h in existing}
        max_abs_delta = 0.3

        for delta in deltas:
            # Clamp suggested deltas
            orig_support = delta.support_score_delta
            orig_refute = delta.refute_score_delta
            clamped_support = max(min(orig_support, max_abs_delta), -max_abs_delta)
            clamped_refute = max(min(orig_refute, max_abs_delta), -max_abs_delta)

            if clamped_support != orig_support or clamped_refute != orig_refute:
                logger.info(
                    "[Beliefs] Clamped hypothesis delta",
                    extra={
                        "id": delta.id,
                        "orig_support_delta": orig_support,
                        "orig_refute_delta": orig_refute,
                        "clamped_support_delta": clamped_support,
                        "clamped_refute_delta": clamped_refute,
                    },
                )

            h = by_id.get(delta.id)
            if h is None:
                h = Hypothesis(
                    id=delta.id,
                    claim=delta.claim,
                    support_score=max(clamped_support, 0.0),
                    refute_score=max(clamped_refute, 0.0),
                    last_updated=now,
                )
                by_id[delta.id] = h
            else:
                h.support_score = max(h.support_score + clamped_support, 0.0)
                h.refute_score = max(h.refute_score + clamped_refute, 0.0)
                h.last_updated = now

        # No deletion: all previously seen hypotheses remain present.
        return list(by_id.values())

    @staticmethod
    def _detect_boundary_drift(
        *, rendered: RenderedMessage, intermediate: IntermediateAnswer
    ) -> None:
        """Log potential boundary drift between reasoning and expression.

        Heuristic-only: look for strong-modality language in the
        rendered message that does not appear in any key_point.
        We do NOT modify the output here, only log.
        """

        strong_terms = ["always", "never", "must", "best practice"]
        text_lower = rendered.text.lower()
        keypoints_text = " \n".join(intermediate.key_points).lower()

        for term in strong_terms:
            if term in text_lower and term not in keypoints_text:
                logger.warning(
                    "[Boundary] Strong-modality term not supported by intermediate key_points",
                    extra={
                        "term": term,
                        "rendered": rendered.text,
                        "key_points": intermediate.key_points,
                    },
                )

    @staticmethod
    def _build_expression_plan(style: CognitiveStyle) -> ExpressionPlan:
        # Defaults
        max_paragraphs = 4
        prefer_short = False

        # Respect explicit user style overrides if present. These should take
        # precedence over inferred style.
        overrides = style.overrides or {}
        if overrides:
            logger.info(
                "[Expression] User style override applied",
                extra={"overrides": overrides},
            )

        if overrides.get("keep_short") or overrides.get("prefer_short"):
            prefer_short = True
            max_paragraphs = 2

        target_tone = overrides.get("formality") or style.formality

        return ExpressionPlan(
            target_tone=target_tone,
            structure=["ack", "reframe", "concept", "example", "check_understanding"],
            analogy_style=style.preferred_analogies,
            constraints={
                "avoid_textbook_definitions": True,
                "avoid_tutor_tone": True,
                "avoid_long_disclaimers": True,
                "max_paragraphs": max_paragraphs,
                "prefer_short": prefer_short,
            },
            emphasis=[
                "Show how a class removes repeated passing of the same data.",
                "Acknowledge that sometimes functions alone are fine.",
                "Keep things concrete and small.",
            ],
        )
