from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import httpx
from jose import jwt
from jose.exceptions import JWTError

try:
    from backend.app.db.database import get_db_connection
except Exception:  # pragma: no cover
    get_db_connection = None  # type: ignore

HASH_ALGO = "sha256"
JWKS_CACHE_TTL = 300  # seconds
ANON_COOKIE_NAME = "anon_id"

_jwks_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}


@dataclass
class IdentityContext:
    is_authenticated: bool
    user_id: Optional[str]
    anon_id: Optional[str]
    subject_type: str
    subject_id: str
    ip_hash: str
    user_agent_hash: str


def _hash_value(value: str, salt: str) -> str:
    hasher = hashlib.new(HASH_ALGO)
    hasher.update(salt.encode("utf-8"))
    hasher.update(value.encode("utf-8"))
    return hasher.hexdigest()


def _get_salt() -> str:
    return os.getenv("IDENTITY_HASH_SALT", "dev-salt")


def _hash_ip(ip: str | None) -> str:
    if not ip:
        return _hash_value("unknown-ip", _get_salt())
    return _hash_value(ip, _get_salt())


def _hash_ua(ua: str | None) -> str:
    if not ua:
        return _hash_value("unknown-ua", _get_salt())
    return _hash_value(ua, _get_salt())


def _load_jwks(supabase_url: str) -> Dict[str, Any]:
    now = time.time()
    cached = _jwks_cache.get(supabase_url)
    if cached and now - cached[0] < JWKS_CACHE_TTL:
        return cached[1]
    jwks_url = supabase_url.rstrip("/") + "/auth/v1/keys"
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(jwks_url)
        resp.raise_for_status()
        data = resp.json()
        _jwks_cache[supabase_url] = (now, data)
        return data


def _verify_jwt(token: str, supabase_url: str, audience: str | None, issuer: str | None) -> Optional[str]:
    try:
        jwks = _load_jwks(supabase_url)
        unverified = jwt.get_unverified_header(token)
        kid = unverified.get("kid")
        keys = jwks.get("keys", [])
        key = next((k for k in keys if k.get("kid") == kid), None)
        if not key:
            return None
        decoded = jwt.decode(
            token,
            key,
            algorithms=[key.get("alg", "RS256")],
            audience=audience or "authenticated",
            issuer=issuer or supabase_url.rstrip("/") + "/auth/v1",
            options={"verify_aud": True, "verify_iss": True},
        )
        return decoded.get("sub")
    except JWTError:
        return None
    except Exception:
        return None


def _parse_authorization(header: str | None) -> Optional[str]:
    if not header:
        return None
    parts = header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def _ensure_anon_cookie(request, response, ttl_days: int = 30) -> str:
    existing = request.cookies.get(ANON_COOKIE_NAME)
    if existing:
        return existing
    anon_id = str(uuid.uuid4())
    max_age = ttl_days * 24 * 60 * 60
    secure_flag = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
    response.set_cookie(
        key=ANON_COOKIE_NAME,
        value=anon_id,
        max_age=max_age,
        httponly=True,
        secure=secure_flag,
        samesite="lax",
        path="/",
    )
    return anon_id


def _maybe_record_session(anon_id: Optional[str], ip_hash: str, ua_hash: str, ttl_days: int) -> None:
    if not anon_id or get_db_connection is None:
        return
    try:
        expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sessions (id, anon_id, created_at, last_seen_at, expires_at, metadata)
                    VALUES (%s, %s, NOW(), NOW(), %s, %s::jsonb)
                    ON CONFLICT (id) DO UPDATE
                    SET last_seen_at = EXCLUDED.last_seen_at,
                        expires_at = EXCLUDED.expires_at,
                        metadata = EXCLUDED.metadata
                    """,
                    (
                        uuid.UUID(anon_id),
                        anon_id,
                        expires_at,
                        json.dumps({"ip_hash": ip_hash, "ua_hash": ua_hash}),
                    ),
                )
            conn.commit()
    except Exception:
        # best effort; do not crash
        return


def _build_identity_context(request, response) -> IdentityContext:
    auth_header = request.headers.get("authorization")
    token = _parse_authorization(auth_header)
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_aud = os.getenv("SUPABASE_JWT_AUD", "authenticated")
    supabase_issuer = os.getenv("SUPABASE_JWT_ISSUER")

    user_id: Optional[str] = None
    if token and supabase_url:
        user_id = _verify_jwt(token, supabase_url, supabase_aud, supabase_issuer)

    anon_ttl = int(os.getenv("ANON_SESSION_TTL_DAYS", "30"))
    anon_id = None
    if not user_id:
        anon_id = _ensure_anon_cookie(request, response, ttl_days=anon_ttl)

    ip_hash = _hash_ip(request.client.host if request.client else None)
    ua_hash = _hash_ua(request.headers.get("user-agent"))

    if user_id:
        subject_type = "user"
        subject_id = user_id
    elif anon_id:
        subject_type = "anon"
        subject_id = anon_id
    else:
        subject_type = "ip"
        subject_id = ip_hash

    return IdentityContext(
        is_authenticated=bool(user_id),
        user_id=user_id,
        anon_id=anon_id,
        subject_type=subject_type,
        subject_id=subject_id,
        ip_hash=ip_hash,
        user_agent_hash=ua_hash,
    )


def get_identity_context(request, response) -> IdentityContext:
    ctx = _build_identity_context(request, response)
    # Record anon session best-effort (bounded metadata only)
    if ctx.anon_id and not ctx.is_authenticated:
        ttl_days = int(os.getenv("ANON_SESSION_TTL_DAYS", "30"))
        _maybe_record_session(ctx.anon_id, ctx.ip_hash, ctx.user_agent_hash, ttl_days)
    return ctx
