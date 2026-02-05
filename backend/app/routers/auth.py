"""Authentication endpoints for email+password login/signup."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Request, Response, HTTPException
from pydantic import BaseModel, EmailStr

from backend.app.auth.password import hash_password, verify_password
from backend.app.config import get_settings
from backend.app.db.database import get_db_connection

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)
_settings = get_settings()

SESSION_COOKIE_NAME = "cs_session"
SESSION_TTL_DAYS = 7


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str


class AuthResponse(BaseModel):
    ok: bool
    user: Optional[UserResponse] = None
    error: Optional[str] = None


def _get_secure_flag() -> bool:
    """Determine if cookies should be Secure based on environment."""
    return str(_settings.auth_cookie_secure).lower() == "true"


def _set_session_cookie(response: Response, session_id: str) -> None:
    """Set secure session cookie."""
    max_age = SESSION_TTL_DAYS * 24 * 60 * 60
    secure = _get_secure_flag()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="none" if secure else "lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    """Clear session cookie."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=_get_secure_flag(),
        samesite="none" if _get_secure_flag() else "lax",
    )


def _create_session(user_id: str) -> str:
    """Create a new session in the database and return session_id."""
    session_id = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sessions (id, user_id, created_at, last_seen_at, expires_at, metadata)
                VALUES (%s, %s, NOW(), NOW(), %s, '{}'::jsonb)
                """,
                (uuid.UUID(session_id), uuid.UUID(user_id), expires_at),
            )
        conn.commit()
    
    return session_id


def _get_user_from_session(session_id: str) -> Optional[dict]:
    """Retrieve user from session_id."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.id, u.email
                    FROM sessions s
                    JOIN users u ON s.user_id = u.id
                    WHERE s.id = %s AND s.expires_at > NOW()
                    """,
                    (uuid.UUID(session_id),),
                )
                row = cur.fetchone()
                if row:
                    return {"id": str(row[0]), "email": row[1]}
    except Exception as e:
        logger.error(f"Session lookup error: {e}")
    return None


def _delete_session(session_id: str) -> None:
    """Delete session from database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM sessions WHERE id = %s", (uuid.UUID(session_id),))
            conn.commit()
    except Exception as e:
        logger.error(f"Session delete error: {e}")


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, response: Response):
    """Login with email and password."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, email, password_hash FROM users WHERE email = %s",
                    (req.email,),
                )
                row = cur.fetchone()
        
        if not row:
            return AuthResponse(ok=False, error="Invalid email or password")
        
        user_id, email, password_hash = row
        
        if not verify_password(req.password, password_hash):
            return AuthResponse(ok=False, error="Invalid email or password")
        
        # Create session
        session_id = _create_session(str(user_id))
        _set_session_cookie(response, session_id)
        
        return AuthResponse(
            ok=True,
            user=UserResponse(id=str(user_id), email=email),
        )
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        return AuthResponse(ok=False, error="Login failed")


@router.post("/signup", response_model=AuthResponse)
async def signup(req: SignupRequest, response: Response):
    """Create a new user account."""
    if len(req.password) < 8:
        return AuthResponse(ok=False, error="Password must be at least 8 characters")
    
    try:
        password_hash = hash_password(req.password)
        user_id = str(uuid.uuid4())
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        INSERT INTO users (id, email, password_hash, created_at, updated_at)
                        VALUES (%s, %s, %s, NOW(), NOW())
                        RETURNING id, email
                        """,
                        (uuid.UUID(user_id), req.email, password_hash),
                    )
                    row = cur.fetchone()
                    conn.commit()
                except Exception as e:
                    if "unique" in str(e).lower():
                        return AuthResponse(ok=False, error="Email already registered")
                    raise
        
        # Create session
        session_id = _create_session(user_id)
        _set_session_cookie(response, session_id)
        
        return AuthResponse(
            ok=True,
            user=UserResponse(id=user_id, email=req.email),
        )
    
    except Exception as e:
        logger.error(f"Signup error: {e}")
        return AuthResponse(ok=False, error="Signup failed")


@router.get("/me")
async def get_current_user(request: Request):
    """Get current authenticated user from session cookie."""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = _get_user_from_session(session_id)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return {"user": user}


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout and clear session."""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    
    if session_id:
        _delete_session(session_id)
    
    _clear_session_cookie(response)
    
    return {"ok": True}
