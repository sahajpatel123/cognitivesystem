from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Request


def get_request_id(request: Optional[Request]) -> str:
    if request is None:
        return str(uuid.uuid4())
    try:
        rid = request.headers.get("x-railway-request-id") or request.headers.get("x-request-id")
        if rid and isinstance(rid, str) and rid.strip():
            return rid.strip()
    except Exception:
        pass
    return str(uuid.uuid4())


__all__ = ["get_request_id"]
