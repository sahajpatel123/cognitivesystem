from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

_OBS_SALT = (os.getenv("IDENTITY_HASH_SALT") or os.getenv("OBS_HASH_SALT") or "obs-salt").encode("utf-8")


def hash_subject(subject_type: str | None, subject_id: str | None) -> str:
    base = f"{subject_type or 'unknown'}:{subject_id or 'anon'}"
    h = hashlib.sha256()
    h.update(_OBS_SALT)
    h.update(base.encode("utf-8"))
    return h.hexdigest()[:16]


def safe_redact(event: Dict[str, Any]) -> Dict[str, Any]:
    # Shallow redact known risky keys
    redacted = dict(event) if isinstance(event, dict) else {}
    for key in ("user_text", "payload", "raw_payload", "body"):
        if key in redacted:
            redacted.pop(key)
    return redacted


def structured_log(event: Dict[str, Any]) -> None:
    try:
        safe_event = safe_redact(event)
        logger.info(json.dumps(safe_event, separators=(",", ":")))
    except Exception:
        # logging must never break the request path
        return


__all__ = ["hash_subject", "structured_log", "safe_redact"]
