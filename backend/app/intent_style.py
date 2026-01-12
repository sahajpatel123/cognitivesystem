from __future__ import annotations

import time
from typing import Tuple

from .schemas import CognitiveStyle, Intent, UserMessage


def infer_intent_and_style(message_text: str) -> Tuple[Intent, CognitiveStyle, UserMessage]:
    """Very simple heuristic-based inference for the thin slice.

    This is intentionally minimal and non-clever; the goal is to
    respect the architecture, not to perfectly classify.
    """

    now = int(time.time())
    user_message = UserMessage(id=f"msg-{now}", text=message_text, timestamp=now)

    lowered = message_text.lower()

    intent = Intent(
        type="question",
        topic_guess="python_oop" if "class" in lowered or "object" in lowered else None,
        goal_guess="when_to_use_classes_vs_functions" if "when" in lowered and "class" in lowered else None,
        confidence=0.7,
    )

    style = CognitiveStyle(
        abstraction_level="low",
        formality="casual",
        preferred_analogies="real_world_first",
        overrides=None,
    )

    return intent, style, user_message
