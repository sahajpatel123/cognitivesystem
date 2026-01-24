from __future__ import annotations

PLACEHOLDER = "Providing a concise response based on limited details"


def evaluate_quality(rendered_text: str, force_fail: bool = False) -> tuple[bool, str | None]:
    """
    Deterministic quality gate.
    Returns (ok, reason). No randomness.
    """
    if force_fail:
        return False, "forced_quality_fail"
    if not isinstance(rendered_text, str):
        return False, "non_string"
    trimmed = rendered_text.strip()
    if not trimmed:
        return False, "empty"
    if len(trimmed) < 40:
        return False, "too_short"
    if PLACEHOLDER in trimmed:
        return False, "placeholder"
    return True, None


def clarifying_prompt() -> str:
    return (
        "I want to give a precise answer. Please share:\n"
        "- What outcome you need\n"
        "- Any constraints or examples\n"
        "- Deadline or priority"
    )


__all__ = ["evaluate_quality", "clarifying_prompt", "PLACEHOLDER"]
