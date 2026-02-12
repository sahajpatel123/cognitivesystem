from __future__ import annotations


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
    # Note: Removed PLACEHOLDER check - we no longer generate meta scaffolding
    return True, None


def clarifying_prompt() -> str:
    """
    DEPRECATED: This prompt is no longer used to block answers.
    System now always answers first and asks clarifying questions within the answer if needed.
    """
    return (
        "Always answer the user's question immediately with the best possible helpful response. "
        "If additional info would improve accuracy, ask up to 3 clarifying questions at the end "
        "under a small heading like 'Quick questions (optional):'. "
        "Do NOT ask for outcome/constraints/deadline as a generic template. "
        "Do NOT refuse or stall. Be concise and actionable."
    )


__all__ = ["evaluate_quality", "clarifying_prompt"]
