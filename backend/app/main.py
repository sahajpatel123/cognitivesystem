from __future__ import annotations

import asyncio
import datetime
import functools
import json
import logging
import os
import re
import time
import hashlib
from logging.config import dictConfig
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Path, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from jose import jwt
from pydantic import ValidationError
from starlette.middleware.cors import ALL_METHODS
from starlette.status import HTTP_302_FOUND

from backend.app.middleware.strip_content_length import StripContentLengthMiddleware
from backend.app.middleware.request_id import RequestIdMiddleware

from backend.app.auth.identity import ANON_COOKIE_NAME, IdentityContext
from backend.app.deps.identity import identity_dependency
from backend.app.routers import auth
from backend.app.chat_contract import (
    ChatAction,
    ChatRequest as ContractChatRequest,
    ChatResponse as ContractChatResponse,
    ExpressionPlan,
    FailureType,
    MAX_PAYLOAD_BYTES,
)
from backend.app.cost import get_cost_policy
from backend.mci_backend.governed_response_runtime import render_governed_response
from backend.mci_backend.model_contract import ModelFailureType, ModelInvocationResult
from backend.app.schemas import ChatRequest, ChatResponse
from backend.app.service import ConversationService
from backend.app.config import get_settings, safe_error_detail, settings_public_summary
from backend.app.config.redaction import redact_secrets
from backend.app.config.settings import validate_for_env
from backend.app.db import check_db_connection
from backend.app.deps.plan_guard import post_accounting, precheck_plan_and_quotas
from backend.app.llm_client import LLMClient
from backend.app.observability import hash_subject, record_invocation, structured_log
from backend.app.observability.request_id import get_request_id
from backend.app.observability.logging import safe_redact
from backend.app.plans.policy import Plan
from backend.app.plans.tokens import clamp_text_to_token_limit, estimate_tokens_from_text
from backend.app.security.entitlements import EntitlementsContext, decide_entitlements
from backend.app.security.headers import apply_security_headers, maybe_harden_cookies
from backend.app.security.abuse import AbuseContext, decide_abuse
from backend.app.perf import (
    PerfTimeoutError,
    api_chat_total_timeout_ms,
    enforce_timeout,
    model_call_timeout_ms,
    outbound_http_timeout_s,
    remaining_budget_ms,
)
from backend.app.waf import WAFError, waf_dependency
from backend.app.models.policy import (
    RequestedMode,
    RoutingContext,
    Tier,
    ModelRoute,
    ModelRoutePlan,
    ModelClass,
    decide_route,
)
from backend.app.reliability import (
    FailureInfo,
    FailureType as ReliabilityFailureType,
    to_public_error,
    evaluate_breaker,
    force_budget_blocked,
)
from backend.app.reliability.engine import Step5Context, run_step5
from backend.app.ux import UXState, build_ux_headers, decide_ux_state, extract_cooldown_seconds
from backend.app.utils.request_helpers import get_request_scheme

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
}


dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

APP_VERSION = "2026.15.1"
_start_time = time.monotonic()

# Deployment marker: log build info for observability
def _get_git_sha() -> str:
    """Get current git SHA if available."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=1,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"

_git_sha = _get_git_sha()
logger.info(
    "BUILD_MARKER %s",
    json.dumps({
        "event": "build_marker",
        "git_sha": _git_sha,
        "version": APP_VERSION,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }, ensure_ascii=False)
)

app = FastAPI(title="Cognitive Conversational Prototype")
_settings = get_settings()
_settings_summary = validate_for_env(_settings)
logger.info(
    "[CFG] loaded",
    extra={
        "env": _settings_summary.get("env"),
        "provider": _settings_summary.get("model_provider"),
        "model": _settings_summary.get("model_name"),
        "enabled": _settings_summary.get("model_calls_enabled"),
        "timeouts": {
            "request": _settings_summary.get("model_timeout_seconds"),
            "connect": _settings_summary.get("model_connect_timeout_seconds"),
        },
        "token_caps": _settings_summary.get("token_caps"),
        "issues": _settings_summary.get("issues"),
        "git_sha": _git_sha,
    },
)


_ALLOWED_ORIGINS = _settings.cors_origins_list()

# Add middlewares in order (last added = first executed)
# 1. CORS (outermost) - credential-safe config
# When allow_credentials=True, origins must NOT be "*"
_cors_origins_safe = [o for o in _ALLOWED_ORIGINS if o != "*"]
if not _cors_origins_safe:
    _cors_origins_safe = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins_safe,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-UX-State", "X-Cooldown-Seconds"],
)

# 2. Request ID middleware (adds X-Request-ID to all responses)
app.add_middleware(RequestIdMiddleware)

# 3. Content-Length stripping (innermost, prevents streaming errors)
app.add_middleware(StripContentLengthMiddleware)

# Initialize service without LLM (will be set in startup event)
service = ConversationService(llm_client=None)
cost_policy = get_cost_policy()


@app.on_event("startup")
async def startup_event():
    """Initialize LLM client on startup. Never crash - store error if config missing."""
    try:
        llm_client = LLMClient()
        service.llm = llm_client
        app.state.llm_ok = True
        app.state.llm_client = llm_client
        app.state.llm_error = None
        logger.info("[LLM] Startup: LLM client initialized successfully")
    except Exception as exc:
        # Store error but don't crash - allow server to start
        app.state.llm_ok = False
        app.state.llm_client = None
        app.state.llm_error = str(exc)
        logger.warning(
            "[LLM] Startup: LLM client initialization failed - server will return 503 for /api/chat",
            extra={"error": str(exc), "error_type": type(exc).__name__}
        )

# Include auth router
app.include_router(auth.router)


@app.post("/v1/sessions/{session_id}/messages", response_model=ChatResponse)
async def post_message(
    session_id: str = Path(..., description="Session identifier"),
    payload: ChatRequest | None = None,
) -> ChatResponse:
    if payload is None or not payload.message.strip():
        return ChatResponse(message="Say a bit more about what you’re trying to figure out.")

    message_len = len(payload.message)
    logger.info(
        "[API] Incoming message",
        extra={
            "session_id": session_id,
            "event": "incoming_message",
            "message_len": message_len,
        },
    )
    response = service.handle_message(session_id=session_id, text=payload.message)
    logger.info(
        "[API] Outgoing message",
        extra={"session_id": session_id, "event": "outgoing_message"},
    )
    return response


def _extract_rendered_text(result: ModelInvocationResult) -> str:
    if result.output_json and isinstance(result.output_json, dict):
        if "question" in result.output_json:
            return str(result.output_json["question"])
    if result.output_text:
        return result.output_text
    if result.failure:
        return result.failure.message
    return ""


def _apply_ux_signals(
    resp: JSONResponse,
    *,
    status_code: int,
    payload: ContractChatResponse | None,
) -> JSONResponse:
    headers = dict(resp.headers)
    action_val = payload.action.value if payload else None
    failure_val = payload.failure_type.value if payload and payload.failure_type else None
    failure_reason = payload.failure_reason if payload else None
    ux_state = decide_ux_state(
        status_code=status_code,
        action=action_val,
        failure_type=failure_val,
        failure_reason=failure_reason,
    )

    cooldown_seconds: Optional[int] = None
    if status_code in {429, 503} or ux_state in {UXState.RATE_LIMITED, UXState.QUOTA_EXCEEDED, UXState.DEGRADED}:
        cooldown_seconds = extract_cooldown_seconds(headers)

    headers.update(build_ux_headers(ux_state, cooldown_seconds))

    if payload is not None:
        payload = payload.model_copy(update={"ux_state": ux_state.value, "cooldown_seconds": cooldown_seconds})
        content = json.loads(payload.json())
        resp = JSONResponse(status_code=status_code, content=content, headers=headers)
    else:
        resp.headers.update(headers)
        resp.status_code = status_code
    return resp


def _json_response_with_ux(
    *,
    status_code: int,
    payload: ContractChatResponse | None,
    headers: Dict[str, str] | None,
    request_id: str | None,
    body: Any = None,
) -> JSONResponse:
    content = json.loads(payload.json()) if payload is not None else body
    resp = JSONResponse(status_code=status_code, content=content, headers=headers or {})
    if request_id:
        _with_request_id(resp, request_id)
    return _apply_ux_signals(resp, status_code=status_code, payload=payload)


def _failure_response(
    status_code: int,
    failure_type: FailureType,
    reason: str,
    action: ChatAction = ChatAction.REFUSE,
    request_id: str | None = None,
    request: Request | None = None,
    headers: Dict[str, str] | None = None,
) -> JSONResponse:
    payload = ContractChatResponse(
        action=action,
        rendered_text="Governed request rejected.",
        failure_type=failure_type,
        failure_reason=reason[:200],
    )
    return _json_response_with_ux(
        status_code=status_code,
        payload=payload,
        headers=headers,
        request_id=request_id,
        body=None,
    )


def _with_request_id(response: JSONResponse, request_id: str) -> JSONResponse:
    response.headers.setdefault("X-Request-Id", request_id)
    return response


def _should_sample(request_id: str, rate: float) -> bool:
    clamped = max(0.0, min(1.0, float(rate)))
    if clamped <= 0:
        return False
    if clamped >= 1:
        return True
    h = hashlib.sha256(request_id.encode("utf-8")).digest()
    val = int.from_bytes(h, "big") / float(1 << 256)
    return val < clamped


def _emit_chat_summary(fields: dict) -> None:
    try:
        safe_fields = safe_redact(fields)
    except Exception:
        safe_fields = fields
    try:
        structured_log({"event": "chat.summary", **safe_fields})
    except Exception:
        try:
            logger.info(json.dumps({"event": "chat.summary", **safe_fields}, separators=(",", ":")))
        except Exception:
            return


def _request_id(request: Request) -> str:
    try:
        existing = getattr(request.state, "request_id", None)
        if isinstance(existing, str) and existing.strip():
            return existing.strip()
    except Exception:
        pass
    try:
        rid = get_request_id(request)
    except Exception as exc:
        logger.info("[API] request_id fallback", extra={"error": str(exc)})
        import uuid

        rid = str(uuid.uuid4())
    try:
        request.state.request_id = rid
    except Exception:
        pass
    return rid


def _debug_enabled() -> bool:
    val = str(getattr(_settings, "debug_errors", "0")).lower()
    return val in {"1", "true", "yes"}


_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{8,}"),
    re.compile(r"[A-Za-z0-9_\-]{24,}"),
]


def _redact_debug_detail(message: str) -> str:
    redacted = message
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _internal_error_reason(exc: Exception, request_id: str) -> str:
    if not _debug_enabled():
        return "sanitized failure"
    exc_name = type(exc).__name__
    if isinstance(exc, NameError):
        missing = ""
        try:
            missing = getattr(exc, "name", "") or ""
        except Exception:
            missing = ""
        missing = (missing or "").strip()
        detail = missing if missing else _redact_debug_detail(str(exc))
        detail = detail[:300]
        return f"debug:{exc_name}: {detail} request_id={request_id}"
    message = _redact_debug_detail(str(exc))[:300]
    return f"debug:{exc_name}: {message} request_id={request_id}"


def _waf_meta(request: Request) -> dict:
    try:
        meta = getattr(request.state, "waf_meta", None)
        return meta if isinstance(meta, dict) else {}
    except Exception:
        return {}


def _plan_meta(request: Request) -> dict:
    try:
        meta = getattr(request.state, "plan_meta", None)
        return meta if isinstance(meta, dict) else {}
    except Exception:
        return {}


def _actor_key(identity: IdentityContext) -> str:
    if identity.user_id:
        return f"user:{identity.user_id}"
    if identity.anon_id:
        return f"anon:{identity.anon_id}"
    return f"ip:{identity.ip_hash}"


def _hash_actor_key(actor_key: str) -> str:
    try:
        return hashlib.sha256(actor_key.encode("utf-8")).hexdigest()[:16]
    except Exception:
        return "unknown"


def _requested_mode(request: Request, payload: dict | None) -> RequestedMode:
    # Optional JSON field "mode" or header "X-Mode"; defaults to DEFAULT
    header_mode = request.headers.get("X-Mode") if hasattr(request, "headers") else None
    candidate = None
    if isinstance(payload, dict):
        candidate = payload.get("mode") or header_mode
    else:
        candidate = header_mode
    if isinstance(candidate, str):
        lowered = candidate.lower().strip()
        if lowered in RequestedMode._value2member_map_:
            return RequestedMode(lowered)
    return RequestedMode.DEFAULT


def _tier_from_plan(plan: Plan) -> Tier:
    if plan == Plan.PRO:
        return Tier.PRO
    if plan == Plan.MAX:
        return Tier.MAX
    return Tier.FREE


async def _invoke_with_route_plan(user_text: str, route_plan: ModelRoutePlan, timeout_ms: int) -> ModelInvocationResult:
    last_result: ModelInvocationResult | None = None
    for route in route_plan.routes:
        try:
            result = await enforce_timeout(
                lambda: asyncio.to_thread(render_governed_response, user_text),
                timeout_ms,
            )
        except Exception as exc:
            if isinstance(exc, (asyncio.TimeoutError, PerfTimeoutError)):
                failure = type(
                    "Failure",
                    (),
                    {"failure_type": ModelFailureType.TIMEOUT, "reason_code": "TIMEOUT", "message": "timeout"},
                )()
                result = ModelInvocationResult(
                    request_id="",
                    ok=False,
                    output_text=None,
                    output_json=None,
                    failure=failure,  # type: ignore[arg-type]
                )
            else:
                raise
        last_result = result
        if result.ok:
            return result
        if result.failure and result.failure.failure_type in (ModelFailureType.TIMEOUT, ModelFailureType.PROVIDER_ERROR):
            continue
        return result
    return last_result  # type: ignore[return-value]


def _log_chat_summary(
    *,
    request: Request,
    request_id: str,
    status_code: int,
    latency_ms: float,
    plan_value: str,
    subject_type: str,
    subject_id: str,
    input_tokens: int | None,
    output_tokens_est: int | None,
    error_code: str | None,
    waf_limiter: str | None,
    budget_ms_total: int | None = None,
    budget_ms_remaining_at_model_start: int | None = None,
    timeout_where: str | None = None,
    model_timeout_ms: int | None = None,
    http_timeout_ms: int | None = None,
    action: str | None = None,
    failure_type: str | None = None,
    failure_reason: str | None = None,
    requested_mode: str | None = None,
    granted_mode: str | None = None,
    model_class: str | None = None,
    model_class_cap: str | None = None,
    effective_model_class: str | None = None,
    breaker_open: bool | None = None,
    budget_block: bool | None = None,
    ip_hash: str | None = None,
    budget_scope: str | None = None,
    entitlements_reason: str | None = None,
    quota_reason: str | None = None,
    actor_hash: str | None = None,
    abuse_score: int | None = None,
    abuse_action: str | None = None,
    abuse_allowed: bool | None = None,
    abuse_reason: str | None = None,
) -> None:
    waf_info = _waf_meta(request)
    plan_info = _plan_meta(request)
    hashed = hash_subject(subject_type, subject_id)
    event = {
        "type": "api_chat",
        "request_id": request_id,
        "route": "/api/chat",
        "method": "POST",
        "status_code": status_code,
        "latency_ms": int(latency_ms),
        "plan": plan_value,
        "subject_type": subject_type,
        "hashed_subject": hashed,
        "waf_decision": waf_info.get("decision"),
        "waf_error": waf_info.get("error_code"),
        "waf_limiter": waf_info.get("limiter_backend") or waf_limiter,
        "plan_decision": plan_info.get("decision"),
        "plan_error": plan_info.get("error_code"),
        "token_estimate_in": input_tokens,
        "token_estimate_out_cap": output_tokens_est,
        "error_code": error_code,
        "budget_ms_total": budget_ms_total,
        "budget_ms_remaining_at_model_start": budget_ms_remaining_at_model_start,
        "timeout_where": timeout_where,
        "model_timeout_ms": model_timeout_ms,
        "http_timeout_ms": http_timeout_ms,
        "abuse_score": abuse_score,
        "abuse_action": abuse_action,
        "abuse_allowed": abuse_allowed,
        "abuse_reason": abuse_reason,
    }
    invocation_written = record_invocation(
        {
            "ts": datetime.datetime.utcnow(),
            "route": "/api/chat",
            "status_code": status_code,
            "latency_ms": int(latency_ms),
            "error_code": error_code,
            "hashed_subject": hashed,
            "session_id": getattr(getattr(request.state, "identity", None), "anon_id", None),
        }
    )
    event["invocation_log_written"] = invocation_written
    structured_log(event)

    effective_action = action or "unknown"
    effective_failure_type = failure_type or None
    sampled = True if (status_code >= 400 or failure_type is not None) else _should_sample(request_id, 0.02)
    summary_fields = {
        "request_id": request_id,
        "endpoint": "/api/chat",
        "event": "chat.summary",
        "timestamp_utc": datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat(),
        "status_code": int(status_code),
        "latency_ms": int(latency_ms),
        "plan": plan_value,
        "requested_mode": requested_mode or "none",
        "granted_mode": granted_mode or "unknown",
        "model_class": model_class or "unknown",
        "model_class_cap": model_class_cap,
        "effective_model_class": effective_model_class,
        "action": effective_action,
        "failure_type": effective_failure_type,
        "failure_reason": (failure_reason[:200] if failure_reason else None),
        "input_tokens_est": input_tokens,
        "output_tokens_cap": output_tokens_est,
        "breaker_open": bool(breaker_open) if breaker_open is not None else False,
        "budget_block": bool(budget_block) if budget_block is not None else False,
        "budget_scope": budget_scope,
        "timeout_where": timeout_where,
        "http_timeout_ms": http_timeout_ms,
        "waf_limiter": waf_limiter,
        "subject_type": subject_type,
        "subject_id_hash": hashed,
        "ip_hash": ip_hash,
        "entitlements_reason": entitlements_reason,
        "quota_reason": quota_reason,
        "actor_hash": actor_hash,
        "sampled": sampled,
        "version": APP_VERSION,
    }

    if sampled:
        _emit_chat_summary(summary_fields)


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "version": APP_VERSION,
        "uptime_seconds": int(time.monotonic() - _start_time),
    }


@app.get("/db/health", response_model=None)
async def db_health() -> Dict[str, str] | JSONResponse:
    ok, reason = check_db_connection()
    if ok:
        return {"status": "ok", "db": "ok"}
    detail = reason or "unknown"
    return JSONResponse(status_code=503, content={"status": "error", "db": "down", "detail": detail})


@app.get("/auth/whoami")
async def whoami(identity: IdentityContext = Depends(identity_dependency)) -> Dict[str, Any]:
    return {
        "authenticated": identity.is_authenticated,
        "subject_type": identity.subject_type,
        "subject_id": identity.subject_id,
        "user_id": identity.user_id,
        "anon_id": identity.anon_id,
    }


@app.post("/auth/logout")
async def logout(response: Response) -> Dict[str, str]:
    response.delete_cookie(key=ANON_COOKIE_NAME, path="/")
    return {"status": "ok"}


def _env_missing(required: list[str]) -> list[str]:
    return [var for var in required if not getattr(_settings, var.lower(), None)]


@app.get("/ready")
async def ready() -> JSONResponse:
    try:
        current_env = _settings.app_env
        required = _settings.required_env_vars()
        missing = _env_missing(required) if current_env.lower() == "prod" else []

        db_status = {"configured": bool(_settings.database_url), "ok": True}
        if db_status["configured"]:
            db_ok, db_reason = check_db_connection()
            db_status["ok"] = db_ok
            if db_reason:
                db_status["reason"] = db_reason

        model_key_present = bool(_settings.model_provider_api_key)

        if current_env.lower() == "prod":
            if missing:
                return JSONResponse(
                    status_code=503,
                    content={"status": "not_ready", "missing_env": missing, "db": db_status, "model_key": model_key_present},
                )
            if not model_key_present:
                return JSONResponse(
                    status_code=503,
                    content={"status": "not_ready", "missing_env": ["MODEL_API_KEY"], "db": db_status},
                )
            if not db_status["ok"]:
                return JSONResponse(status_code=503, content={"status": "not_ready", "db": db_status})

        return JSONResponse(
            status_code=200,
            content={"status": "ok", "env": current_env, "db": db_status, "model_key": model_key_present},
        )
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready", "reason": "sanitized"})


@app.get("/healthz")
async def healthz() -> JSONResponse:
    """Health check endpoint - always returns 200 if server is running."""
    return JSONResponse(status_code=200, content={"ok": True})


@app.get("/readyz")
async def readyz() -> JSONResponse:
    """Readiness check endpoint - returns 200 if LLM is configured, 503 otherwise."""
    llm_ok = getattr(app.state, "llm_ok", False)
    if llm_ok:
        settings = get_settings()
        return JSONResponse(
            status_code=200,
            content={
                "ready": True,
                "provider": settings.model_provider,
            }
        )
    else:
        llm_error = getattr(app.state, "llm_error", "LLM not initialized")
        return JSONResponse(
            status_code=503,
            content={
                "ready": False,
                "error": llm_error,
            }
        )


@app.options("/api/chat")
async def chat_options() -> Response:
    """Handle CORS preflight for /api/chat"""
    return Response(status_code=204)


@app.post("/api/chat", response_model=ContractChatResponse)
async def governed_chat(request: Request, identity: IdentityContext = Depends(waf_dependency)) -> ContractChatResponse | JSONResponse:
    start_ts = time.monotonic()
    budget_ms_total = api_chat_total_timeout_ms()
    rid = _request_id(request)
    http_timeout_ms = int(outbound_http_timeout_s() * 1000)
    
    # Check LLM readiness before processing
    if not getattr(request.app.state, "llm_ok", False):
        llm_error = getattr(request.app.state, "llm_error", "LLM not configured")
        return JSONResponse(
            status_code=503,
            content={
                "error": "LLM_NOT_CONFIGURED",
                "message": "LLM provider base URL / API key not configured in environment variables.",
                "required": ["LLM_API_BASE=https://api.openai.com/v1", "OPENAI_API_KEY=***"],
                "checked_envs": ["LLM_API_BASE", "OPENAI_BASE_URL", "MODEL_BASE_URL", "MODEL_PROVIDER_BASE_URL", "API_BASE", "OPENAI_API_KEY", "LLM_API_KEY", "MODEL_API_KEY", "OPENAI_KEY", "API_KEY"],
                "detail": llm_error,
            }
        )

    async def _process() -> ContractChatResponse | JSONResponse:
        try:
            request.state.identity = identity
        except Exception:
            pass
        waf_limiter = "memory-fallback" if getattr(request.state, "waf_used_memory", False) else "db"
        logger.info(
            "[API] chat start",
            extra={
                "route": "/api/chat",
                "request_id": rid,
                "subject_type": identity.subject_type,
                "subject_id": identity.subject_id,
                "waf_limiter": waf_limiter,
                "content_length": request.headers.get("content-length"),
            },
        )

        content_type = (request.headers.get("content-type") or "").lower()
        if not content_type.startswith("application/json"):
            latency_ms = (time.monotonic() - start_ts) * 1000
            logger.info(
                "[API] chat reject",
                extra={
                    "route": "/api/chat",
                    "status_code": 415,
                    "error_code": "content_type_invalid",
                    "request_id": rid,
                    "subject_type": identity.subject_type,
                    "subject_id": identity.subject_id,
                    "waf_limiter": waf_limiter,
                },
            )
            _log_chat_summary(
                request=request,
                request_id=rid,
                status_code=415,
                latency_ms=latency_ms,
                plan_value="unknown",
                subject_type=identity.subject_type,
                subject_id=identity.subject_id,
                input_tokens=None,
                output_tokens_est=None,
                error_code="content_type_invalid",
                waf_limiter=waf_limiter,
                budget_ms_total=budget_ms_total,
                timeout_where=None,
                http_timeout_ms=http_timeout_ms,
                budget_scope=None,
            )
            resp = _json_response_with_ux(
                status_code=415,
                payload=None,
                headers={"X-UX-State": UXState.ERROR.value},
                request_id=rid,
                body={"ok": False, "error_code": "content_type_invalid", "message": "Content-Type must be application/json"},
            )
            resp.headers["X-UX-State"] = UXState.ERROR.value
            return resp

        payload = getattr(request.state, "payload", None)
        if payload is None:
            try:
                payload = await request.json()
            except Exception:
                latency_ms = (time.monotonic() - start_ts) * 1000
                logger.info(
                    "[API] chat reject",
                    extra={
                        "route": "/api/chat",
                        "status_code": 400,
                        "error_code": "json_invalid",
                        "request_id": rid,
                        "subject_type": identity.subject_type,
                        "subject_id": identity.subject_id,
                        "waf_limiter": waf_limiter,
                    },
                )
                _log_chat_summary(
                    request=request,
                    request_id=rid,
                    status_code=400,
                    latency_ms=latency_ms,
                    plan_value="unknown",
                    subject_type=identity.subject_type,
                    subject_id=identity.subject_id,
                    input_tokens=None,
                    output_tokens_est=None,
                    error_code="json_invalid",
                    waf_limiter=waf_limiter,
                    budget_ms_total=budget_ms_total,
                    timeout_where=None,
                    http_timeout_ms=http_timeout_ms,
                    budget_scope=None,
                )
                return _json_response_with_ux(
                    status_code=400,
                    payload=None,
                    headers=None,
                    request_id=rid,
                    body={"ok": False, "error_code": "json_invalid", "message": "Request body must be valid JSON."},
                )

        user_text = payload.get("user_text") if isinstance(payload, dict) else None
        if not user_text or not isinstance(user_text, str):
            latency_ms = (time.monotonic() - start_ts) * 1000
            logger.info(
                "[API] chat reject",
                extra={
                    "route": "/api/chat",
                    "status_code": 400,
                    "error_code": "user_text_missing",
                    "request_id": rid,
                    "subject_type": identity.subject_type,
                    "subject_id": identity.subject_id,
                    "waf_limiter": waf_limiter,
                },
            )
            _log_chat_summary(
                request=request,
                request_id=rid,
                status_code=400,
                latency_ms=latency_ms,
                plan_value="unknown",
                subject_type=identity.subject_type,
                subject_id=identity.subject_id,
                input_tokens=None,
                output_tokens_est=None,
                error_code="user_text_missing",
                waf_limiter=waf_limiter,
                budget_ms_total=budget_ms_total,
                timeout_where=None,
                http_timeout_ms=http_timeout_ms,
                budget_scope=None,
            )
            return _json_response_with_ux(
                status_code=400,
                payload=None,
                headers=None,
                request_id=rid,
                body={"ok": False, "error_code": "user_text_missing", "message": "user_text is required"},
            )

        chat_user_text = user_text.strip()
        requested_mode = _requested_mode(request, payload)
        requested_model_class = None
        if isinstance(payload, dict):
            maybe_model_class = payload.get("model_class")
            if isinstance(maybe_model_class, str):
                requested_model_class = maybe_model_class.strip()

        plan, limits, guard_error, input_tokens, budget_estimate = precheck_plan_and_quotas(chat_user_text, identity)
        if not plan:
            plan = Plan.FREE
        try:
            request.state.plan_meta = {"decision": "allow", "error_code": None, "plan": plan.value}
        except Exception:
            pass
        if guard_error:
            if getattr(request.state, "waf_used_memory", False) and isinstance(guard_error, JSONResponse):
                guard_error.headers["X-WAF-Limiter"] = "memory-fallback"
            if isinstance(guard_error, JSONResponse):
                _with_request_id(guard_error, rid)
                try:
                    body = guard_error.body
                    error_code = None
                    if body:
                        parsed = json.loads(body)
                        error_code = parsed.get("error_code")
                except Exception:
                    error_code = None
                logger.info(
                    "[API] chat reject",
                    extra={
                        "route": "/api/chat",
                        "status_code": guard_error.status_code,
                        "error_code": error_code,
                        "request_id": rid,
                        "subject_type": identity.subject_type,
                        "subject_id": identity.subject_id,
                        "plan": plan.value,
                        "input_chars": len(chat_user_text),
                        "input_tokens": input_tokens,
                        "budget_estimate": budget_estimate,
                        "waf_limiter": waf_limiter,
                    },
                )
                try:
                    request.state.plan_meta = {"decision": "blocked", "error_code": error_code, "plan": plan.value}
                except Exception:
                    pass
                latency_ms = (time.monotonic() - start_ts) * 1000
                _log_chat_summary(
                    request=request,
                    request_id=rid,
                    status_code=guard_error.status_code,
                    latency_ms=latency_ms,
                    plan_value=plan.value,
                    subject_type=identity.subject_type,
                    subject_id=identity.subject_id,
                    input_tokens=input_tokens,
                    output_tokens_est=limits.max_output_tokens,
                    error_code=error_code,
                    waf_limiter=waf_limiter,
                    budget_ms_total=budget_ms_total,
                    timeout_where=None,
                    http_timeout_ms=http_timeout_ms,
                    budget_scope=None,
                )
        if guard_error is not None:
            if isinstance(guard_error, JSONResponse):
                return _apply_ux_signals(guard_error, status_code=guard_error.status_code, payload=None)
            return guard_error

        # Abuse/suspicion throttle (deterministic, pre-cost)
        is_non_local = (_settings.app_env or "local").lower() in {"staging", "production", "prod"} or (
            (request.url.hostname or "").lower() not in {"localhost", "127.0.0.1", "::1"}
        )
        
        # CRITICAL: Get actual scheme respecting X-Forwarded-Proto from Railway proxy
        actual_scheme = get_request_scheme(request)
        
        abuse_ctx = AbuseContext(
            path=str(request.url.path),
            request_id=rid,
            ip_hash=identity.ip_hash,
            actor_key=_actor_key(identity),
            subject_type=identity.subject_type,
            subject_id=identity.subject_id,
            waf_limiter=waf_limiter,
            user_agent=request.headers.get("user-agent"),
            accept=request.headers.get("accept"),
            content_type=request.headers.get("content-type"),
            method=request.method,
            has_auth=bool(identity.is_authenticated),
            is_sensitive_path=True,
            request_scheme=actual_scheme,  # Use actual scheme from proxy headers
            is_non_local=is_non_local,
        )
        abuse_decision = decide_abuse(abuse_ctx)
        
        # DIAGNOSTIC: Log scheme detection for debugging
        logger.info(
            "[HTTPS] Scheme detection",
            extra={
                "request_id": rid,
                "direct_scheme": request.url.scheme,
                "x_forwarded_proto": request.headers.get("x-forwarded-proto"),
                "actual_scheme": actual_scheme,
                "is_https": actual_scheme == "https",
                "abuse_score": abuse_decision.score,
                "abuse_reason": abuse_decision.reason,
                "abuse_action": abuse_decision.action,
            },
        )
        abuse_score = abuse_decision.score
        abuse_action = abuse_decision.action
        abuse_allowed = abuse_decision.allowed
        abuse_reason = (abuse_decision.reason or "")[:200]
        if not abuse_decision.allowed:
            status_code = 403 if abuse_decision.action == "BLOCK" else 429
            headers = {}
            if abuse_decision.retry_after_s is not None:
                headers["Retry-After"] = str(abuse_decision.retry_after_s)
            latency_ms = (time.monotonic() - start_ts) * 1000
            reason = abuse_reason if abuse_reason else "abuse"
            failure_type = FailureType.ABUSE_BLOCKED if abuse_decision.action == "BLOCK" else FailureType.RATE_LIMITED
            payload_resp = ContractChatResponse(
                action=ChatAction.FALLBACK,
                rendered_text=(
                    "Request blocked by security policy." if abuse_decision.action == "BLOCK" else "Too many suspicious requests. Please retry shortly."
                ),
                failure_type=failure_type,
                failure_reason=reason,
            )
            _log_chat_summary(
                request=request,
                request_id=rid,
                status_code=status_code,
                latency_ms=latency_ms,
                plan_value=plan.value,
                subject_type=identity.subject_type,
                subject_id=identity.subject_id,
                input_tokens=input_tokens,
                output_tokens_est=limits.max_output_tokens,
                error_code=f"abuse_{abuse_decision.action.lower()}",
                waf_limiter=waf_limiter,
                budget_ms_total=budget_ms_total,
                timeout_where=None,
                http_timeout_ms=http_timeout_ms,
                action=payload_resp.action.value,
                failure_type=payload_resp.failure_type.value if payload_resp.failure_type else None,
                failure_reason=payload_resp.failure_reason,
                requested_mode=requested_mode.value if requested_mode else None,
                granted_mode=None,
                model_class=None,
                model_class_cap=None,
                effective_model_class=None,
                breaker_open=None,
                budget_block=None,
                ip_hash=identity.ip_hash,
                budget_scope=None,
                entitlements_reason=None,
                quota_reason=None,
                actor_hash=_hash_actor_key(_actor_key(identity)),
                abuse_score=abuse_score,
                abuse_action=abuse_action,
                abuse_allowed=abuse_allowed,
                abuse_reason=abuse_reason,
            )
            return _json_response_with_ux(
                status_code=status_code,
                payload=payload_resp,
                headers=headers,
                request_id=rid,
                body=None,
            )

        actor_key = _actor_key(identity)
        actor_hash = _hash_actor_key(actor_key)

        ent_effective_mode_value = "default"
        ent_model_class_cap = "fast"
        ent_reason_code = None
        try:
            ent_ctx = EntitlementsContext(
                plan=plan.value,
                requested_mode=requested_mode.value,
                requested_model_class=requested_model_class,
                subject_type=identity.subject_type,
                subject_id=identity.subject_id,
            )
            ent_decision = decide_entitlements(ent_ctx)
            ent_effective_mode_value = (
                ent_decision.effective_mode
                if ent_decision and ent_decision.effective_mode in RequestedMode._value2member_map_
                else "default"
            )
            ent_model_class_cap = getattr(ent_decision, "model_class_cap", "fast")
            ent_reason_code = getattr(ent_decision, "reason_code", None)
        except Exception:
            ent_effective_mode_value = "default"
            ent_model_class_cap = "fast"
            ent_reason_code = "ENTITLEMENTS_ERROR_FALLBACK"

        ent_requested_mode = RequestedMode(ent_effective_mode_value)

        cost_pre = cost_policy.precheck(
            request_id=rid,
            actor_key=actor_key,
            ip_hash=identity.ip_hash,
            est_input_tokens=input_tokens,
            est_output_cap=limits.max_output_tokens,
        )
        if not cost_pre.allowed:
            status_code = 503 if cost_pre.scope == "breaker" else 429
            failure_type = FailureType.PROVIDER_UNAVAILABLE if cost_pre.scope == "breaker" else FailureType.BUDGET_EXCEEDED
            reason = "temporarily unavailable" if cost_pre.scope == "breaker" else "cost budget exceeded"
            if cost_pre.scope == "request_cap":
                reason = "request exceeds cost cap"
            retry_after = cost_pre.retry_after_s
            latency_ms = (time.monotonic() - start_ts) * 1000
            cost_policy.record_failure(
                request_id=rid,
                actor_key=actor_key,
                ip_hash=identity.ip_hash,
                outcome="breaker_open" if cost_pre.scope == "breaker" else "budget_blocked",
                latency_ms=latency_ms,
                is_provider_failure=False,
                budget_scope=cost_pre.scope,
            )
            headers = {}
            if retry_after is not None:
                headers["Retry-After"] = str(retry_after)
            _log_chat_summary(
                request=request,
                request_id=rid,
                status_code=status_code,
                latency_ms=latency_ms,
                plan_value=plan.value,
                subject_type=identity.subject_type,
                subject_id=identity.subject_id,
                input_tokens=input_tokens,
                output_tokens_est=limits.max_output_tokens,
                error_code=f"cost_{cost_pre.scope or 'block'}",
                waf_limiter=waf_limiter,
                budget_ms_total=budget_ms_total,
                timeout_where=None,
                http_timeout_ms=http_timeout_ms,
                budget_scope=cost_pre.scope,
                requested_mode=ent_requested_mode.value if ent_requested_mode else None,
                granted_mode=ent_requested_mode.value if ent_requested_mode else None,
                model_class_cap=ent_model_class_cap,
                effective_model_class=ent_model_class_cap,
                entitlements_reason=(ent_reason_code or "")[:200],
                quota_reason=None,
                actor_hash=actor_hash,
                abuse_score=abuse_score,
                abuse_action=abuse_action,
                abuse_allowed=abuse_allowed,
                abuse_reason=abuse_reason,
            )
            payload = ContractChatResponse(
                action=ChatAction.FALLBACK,
                rendered_text="Cost protection is active. Please try again later.",
                failure_type=failure_type,
                failure_reason=reason[:200],
            )
            return _json_response_with_ux(
                status_code=status_code,
                payload=payload,
                headers=headers,
                request_id=rid,
                body=None,
            )

        forced_breaker = evaluate_breaker(False)
        forced_budget = force_budget_blocked()
        route_ctx = RoutingContext(
            tier=_tier_from_plan(plan),
            requested_mode=ent_requested_mode,
            breaker_open=forced_breaker,
            budget_tight=forced_budget,
            est_input_tokens=input_tokens,
        )
        route_plan = decide_route(route_ctx)

        def _clamped(mc: ModelClass) -> ModelClass:
            order = [ModelClass.FAST.value, ModelClass.BALANCED.value, ModelClass.STRONG.value]
            cap_val = (ent_model_class_cap or ModelClass.FAST.value).lower()
            cur_val = mc.value if isinstance(mc, ModelClass) else str(mc)
            try:
                cap_idx = order.index(cap_val)
            except ValueError:
                cap_idx = 0
            try:
                cur_idx = order.index(cur_val)
            except ValueError:
                cur_idx = len(order) - 1
            return ModelClass(order[min(cur_idx, cap_idx)])

        route_plan.primary.model_class = _clamped(route_plan.primary.model_class)
        for fb in route_plan.fallbacks:
            fb.model_class = _clamped(fb.model_class)

        ent_effective_model_class = route_plan.primary.model_class.value

        logger.info(
            "[API] routing decision",
            extra={
                "request_id": rid,
                "tier": route_plan.tier.value,
                "requested_mode": route_plan.requested_mode.value,
                "effective_mode": route_plan.effective_mode.value,
                "primary_model_class": route_plan.primary.model_class.value,
                "fallback_count": len(route_plan.fallbacks),
                "breaker_open": forced_breaker,
                "budget_flag": forced_budget,
                "entitlements_reason": (ent_reason_code or "")[:200],
            },
        )
        try:
            request.state.plan_meta = {
                "decision": "allow",
                "error_code": None,
                "plan": plan.value,
                "route_plan": {
                    "tier": route_plan.tier.value,
                    "requested_mode": route_plan.requested_mode.value,
                    "effective_mode": route_plan.effective_mode.value,
                    "model_class": route_plan.primary.model_class.value,
                    "fallbacks": [
                        {"mode": fb.effective_mode.value, "model_class": fb.model_class.value} for fb in route_plan.fallbacks
                    ],
                },
            }
        except Exception:
            pass

        budget_remaining_before_model = remaining_budget_ms(start_ts, budget_ms_total)
        model_timeout_ms_value = model_call_timeout_ms()
        effective_model_timeout_ms = max(1000, min(model_timeout_ms_value, budget_remaining_before_model))

        if budget_remaining_before_model <= 0:
            latency_ms = (time.monotonic() - start_ts) * 1000
            error_code = "timeout_budget_exhausted"
            cost_policy.record_failure(
                request_id=rid,
                actor_key=actor_key,
                ip_hash=identity.ip_hash,
                outcome="budget_remaining_exhausted",
                latency_ms=latency_ms,
                is_provider_failure=False,
                budget_scope="request_budget",
            )
            _log_chat_summary(
                request=request,
                request_id=rid,
                status_code=500,
                latency_ms=latency_ms,
                plan_value=plan.value,
                subject_type=identity.subject_type,
                subject_id=identity.subject_id,
                input_tokens=input_tokens,
                output_tokens_est=limits.max_output_tokens,
                error_code=error_code,
                waf_limiter=waf_limiter,
                budget_ms_total=budget_ms_total,
                budget_ms_remaining_at_model_start=0,
                timeout_where="model",
                model_timeout_ms=effective_model_timeout_ms,
                http_timeout_ms=http_timeout_ms,
                budget_scope="request_budget",
                requested_mode=ent_requested_mode.value if ent_requested_mode else None,
                granted_mode=route_plan.effective_mode.value,
                model_class=route_plan.primary.model_class.value,
                model_class_cap=ent_model_class_cap,
                effective_model_class=ent_effective_model_class,
                entitlements_reason=(ent_reason_code or "")[:200],
                quota_reason=None,
                actor_hash=actor_hash,
                abuse_score=abuse_score,
                abuse_action=abuse_action,
                abuse_allowed=abuse_allowed,
                abuse_reason=abuse_reason,
            )
            return _failure_response(
                status_code=500,
                failure_type=FailureType.TIMEOUT,
                reason="timeout",
                action=ChatAction.FALLBACK,
                request_id=rid,
            )

        async def _invoke_attempt(attempt_idx: int) -> str:
            result = await asyncio.to_thread(render_governed_response, chat_user_text)
            if not result.ok:
                raise RuntimeError("provider_failure")
            output_text = result.output_text or ""
            if not output_text and result.output_json and isinstance(result.output_json, dict):
                maybe_text = result.output_json.get("message") or result.output_json.get("text")
                if isinstance(maybe_text, str):
                    output_text = maybe_text
            return output_text

        step5_ctx = Step5Context(
            request_id=rid,
            plan_value=plan.value,
            breaker_open=forced_breaker,
            budget_blocked=forced_budget,
            total_timeout_ms=budget_remaining_before_model,
            per_attempt_timeout_ms=effective_model_timeout_ms,
            max_attempts=2,
            mode_requested=ent_requested_mode.value if ent_requested_mode else None,
            mode_effective=route_plan.effective_mode.value,
            model_class_effective=route_plan.primary.model_class.value,
        )

        step5_result = await run_step5(step5_ctx, _invoke_attempt)

        output_tokens_est = estimate_tokens_from_text(step5_result.rendered_text)
        tokens_used = (input_tokens or 0) + (output_tokens_est or 0)
        latency_ms = int((time.monotonic() - start_ts) * 1000)

        provider_failure_types = {
            FailureType.PROVIDER_TIMEOUT,
            FailureType.PROVIDER_RATE_LIMIT,
            FailureType.PROVIDER_AUTH_ERROR,
            FailureType.PROVIDER_BAD_RESPONSE,
            FailureType.PROVIDER_UNAVAILABLE,
        }
        is_provider_failure = step5_result.failure_type in provider_failure_types

        status_code = 200
        if step5_result.failure_type == FailureType.BUDGET_EXCEEDED:
            status_code = 429
        elif step5_result.failure_type == FailureType.PROVIDER_UNAVAILABLE:
            status_code = 503

        headers = {}
        if getattr(request.state, "waf_used_memory", False):
            headers["X-WAF-Limiter"] = "memory-fallback"

        if step5_result.failure_type:
            post_accounting(identity, tokens_used)
            outcome = "provider_failure" if is_provider_failure else "step5_failure"
            cost_policy.record_failure(
                request_id=rid,
                actor_key=actor_key,
                ip_hash=identity.ip_hash,
                outcome=outcome,
                latency_ms=latency_ms,
                is_provider_failure=is_provider_failure,
                budget_scope=None,
            )
            response = ContractChatResponse(
                action=step5_result.action,
                rendered_text=step5_result.rendered_text or "Governed response unavailable.",
                failure_type=step5_result.failure_type,
                failure_reason=step5_result.failure_reason,
            )
        else:
            post_accounting(identity, tokens_used)
            cost_policy.record_success(
                request_id=rid,
                actor_key=actor_key,
                ip_hash=identity.ip_hash,
                input_tokens=input_tokens,
                output_tokens=output_tokens_est,
                latency_ms=latency_ms,
                outcome="step5_success",
                budget_scope=None,
            )
            response = ContractChatResponse(
                action=step5_result.action,
                rendered_text=step5_result.rendered_text if step5_result.rendered_text.strip() else "Governed response unavailable.",
                failure_type=None,
                failure_reason=None,
            )

        json_payload = json.loads(response.json())
        _log_chat_summary(
            request=request,
            request_id=rid,
            status_code=status_code,
            latency_ms=latency_ms,
            plan_value=plan.value,
            subject_type=identity.subject_type,
            subject_id=identity.subject_id,
            input_tokens=input_tokens,
            output_tokens_est=limits.max_output_tokens,
            error_code=step5_result.failure_type.value if step5_result.failure_type else None,
            waf_limiter=waf_limiter,
            budget_ms_total=budget_ms_total,
            budget_ms_remaining_at_model_start=budget_remaining_before_model,
            timeout_where=step5_result.timeout_where,
            model_timeout_ms=effective_model_timeout_ms,
            http_timeout_ms=http_timeout_ms,
            action=response.action.value,
            failure_type=response.failure_type.value if response.failure_type else None,
            failure_reason=response.failure_reason,
            requested_mode=ent_requested_mode.value if ent_requested_mode else None,
            granted_mode=route_plan.effective_mode.value,
            model_class=route_plan.primary.model_class.value,
            model_class_cap=ent_model_class_cap,
            effective_model_class=ent_effective_model_class,
            breaker_open=forced_breaker,
            budget_block=forced_budget,
            ip_hash=identity.ip_hash,
            budget_scope=None,
            entitlements_reason=(ent_reason_code or "")[:200],
            quota_reason=None,
            actor_hash=actor_hash,
            abuse_score=abuse_score,
            abuse_action=abuse_action,
            abuse_allowed=abuse_allowed,
            abuse_reason=abuse_reason,
        )
        logger.info(
            "[API] step5.summary",
            extra={
                "request_id": rid,
                "status_code": status_code,
                "action": response.action.value,
                "failure_type": response.failure_type.value if response.failure_type else None,
                "failure_reason": response.failure_reason[:200] if response.failure_reason else None,
                "plan_value": plan.value,
                "mode_requested": ent_requested_mode.value if ent_requested_mode else None,
                "mode_effective": route_plan.effective_mode.value,
                "model_class_effective": route_plan.primary.model_class.value,
                "attempts": step5_result.attempts,
                "breaker_open": forced_breaker,
                "budget_blocked": forced_budget,
                "timeout_where": step5_result.timeout_where,
                "latency_ms": latency_ms,
                "entitlements_reason": (ent_reason_code or "")[:200],
            },
        )
        return _json_response_with_ux(
            status_code=status_code,
            payload=response,
            headers=headers,
            request_id=rid,
            body=None,
        )

    try:
        return await enforce_timeout(_process, budget_ms_total)
    except Exception as exc:
        if isinstance(exc, (asyncio.TimeoutError, PerfTimeoutError)):
            latency_ms = (time.monotonic() - start_ts) * 1000
            cost_policy.record_failure(
                request_id=rid,
                actor_key=_actor_key(identity),
                ip_hash=identity.ip_hash,
                outcome="timeout_total",
                latency_ms=latency_ms,
                is_provider_failure=True,
                budget_scope="total_timeout",
            )
            _log_chat_summary(
                request=request,
                request_id=rid,
                status_code=500,
                latency_ms=latency_ms,
                plan_value="unknown",
                subject_type=identity.subject_type,
                subject_id=identity.subject_id,
                input_tokens=None,
                output_tokens_est=None,
                error_code="timeout",
                waf_limiter=None,
                budget_ms_total=budget_ms_total,
                budget_ms_remaining_at_model_start=None,
                timeout_where="total",
                model_timeout_ms=None,
                http_timeout_ms=http_timeout_ms,
                budget_scope="total_timeout",
            )
            return _failure_response(
                status_code=500,
                failure_type=FailureType.TIMEOUT,
                reason="timeout",
                action=ChatAction.FALLBACK,
                request_id=rid,
            )
        raise


@app.exception_handler(WAFError)
async def handle_waf_error(request: Request, exc: WAFError) -> JSONResponse:  # noqa: D401
    rid = _request_id(request)
    headers = exc.to_headers()
    headers["X-Request-Id"] = rid
    if getattr(request.state, "waf_used_memory", False):
        headers["X-WAF-Limiter"] = "memory-fallback"
    body = exc.to_body()
    if isinstance(body, dict):
        body["request_id"] = rid
    return JSONResponse(status_code=exc.status_code, content=body, headers=headers)


@app.exception_handler(Exception)
async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:  # noqa: BLE001
    rid = _request_id(request)
    logger.exception("Unhandled error in request", extra={"request_id": rid})
    content = {
        "ok": False,
        "error": {
            "code": "INTERNAL_ERROR",
            "request_id": rid,
        }
    }
    if str(_settings.debug_errors) == "1":
        content["error"]["detail"] = str(exc)[:200]
    return JSONResponse(status_code=500, content=content, headers={"X-Request-Id": rid})


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    host = (request.url.hostname or "").lower()
    env = (_settings.app_env or "local").lower()
    is_non_local = env in {"staging", "production", "prod"} or host not in {"localhost", "127.0.0.1", "::1"}
    is_https = request.url.scheme == "https"
    response = None
    try:
        response = await call_next(request)
    finally:
        if response is not None:
            apply_security_headers(response, is_https=is_https, is_non_local=is_non_local)
            if is_https and is_non_local:
                maybe_harden_cookies(response, should_secure=True)
    return response
