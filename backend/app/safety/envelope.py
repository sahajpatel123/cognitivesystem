from __future__ import annotations

BLOCK_KEYWORDS = [
    "self-harm instruction",
    "commit suicide",
    "harm yourself",
]

SAFE_FALLBACK_TEXT = "Response unavailable. Safety guard active."


def apply_safety(text: str | None, force_block: bool = False) -> tuple[bool, str | None]:
    trimmed = (text or "").strip()
    if force_block:
        return False, "forced_safety_block"
    if any(keyword in trimmed.lower() for keyword in [k.lower() for k in BLOCK_KEYWORDS]):
        return False, "disallowed_content"
    return True, None


def refusal_text() -> str:
    return SAFE_FALLBACK_TEXT


__all__ = ["apply_safety", "refusal_text", "SAFE_FALLBACK_TEXT", "BLOCK_KEYWORDS"]
