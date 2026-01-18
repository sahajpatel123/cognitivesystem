from __future__ import annotations

import datetime as dt
import json
from typing import Any, Dict, Optional


def record_invocation(event: Dict[str, Any]) -> bool:
    """
    Best-effort write into invocation_logs.
    Expected columns: ts (timestamptz), route, status_code, latency_ms, error_code,
    hashed_subject, session_id, model_used.
    """
    try:
        try:
            from backend.app.db.database import get_db_connection  # type: ignore
        except Exception:
            return False

        conn = None
        try:
            conn = get_db_connection()
        except Exception:
            return False
        if conn is None:
            return False

        ts = event.get("ts") or dt.datetime.utcnow()
        route = event.get("route", "")
        status_code = int(event.get("status_code") or 0)
        latency_ms = event.get("latency_ms")
        error_code = event.get("error_code")
        hashed_subject = event.get("hashed_subject")
        session_id = event.get("session_id")
        model_used = event.get("model_used")

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO invocation_logs (ts, route, status_code, latency_ms, error_code, hashed_subject, session_id, model_used)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (ts, route, status_code, latency_ms, error_code, hashed_subject, session_id, model_used),
            )
        conn.commit()
        return True
    except Exception:
        return False


__all__ = ["record_invocation"]
