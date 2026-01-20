from __future__ import annotations

import re
from typing import Any, Dict

_SECRET_KEYS = {"authorization", "api_key", "token", "secret", "set-cookie", "cookie", "user_text", "prompt", "messages"}
_API_KEY_PATTERN = re.compile(r"(sk-[A-Za-z0-9]{8,})", re.IGNORECASE)


def redact_secrets(s: str) -> str:
    if not s:
        return s
    redacted = _API_KEY_PATTERN.sub("[redacted]", s)
    # Strip simple Authorization: Bearer ... patterns
    redacted = re.sub(r"(Authorization:\s*Bearer\s+)[^\s]+", r"\1[redacted]", redacted, flags=re.IGNORECASE)
    return redacted


def safe_error_detail(exc: Exception) -> str:
    text = str(exc)
    text = redact_secrets(text)
    return text[:200]


def safe_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(d, dict):
        return {}
    cleaned: Dict[str, Any] = {}
    for k, v in d.items():
        key_lower = str(k).lower()
        if key_lower in _SECRET_KEYS:
            continue
        cleaned[k] = v
    return cleaned


__all__ = ["redact_secrets", "safe_error_detail", "safe_dict"]
