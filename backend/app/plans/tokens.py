from __future__ import annotations

from math import ceil


def estimate_tokens_from_text(text: str) -> int:
    """
    Deterministic, privacy-safe token estimator.
    Approximation: 1 token ~= 4 characters.
    """
    if not isinstance(text, str) or not text:
        return 0
    return max(1, ceil(len(text) / 4))


def estimate_total_tokens(input_tokens: int, max_output_tokens: int) -> int:
    return max(0, input_tokens) + max(0, max_output_tokens)


def clamp_text_to_token_limit(text: str, max_tokens: int) -> str:
    if max_tokens <= 0 or not isinstance(text, str):
        return ""
    # Using 4 chars/token approximation
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


__all__ = [
    "estimate_tokens_from_text",
    "estimate_total_tokens",
    "clamp_text_to_token_limit",
]
