from __future__ import annotations

import asyncio
import functools
import json
import logging
import os
import re
import time
from logging.config import dictConfig
from typing import Any, Dict

from fastapi import Depends, FastAPI, Path, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from jose import jwt
from pydantic import ValidationError
from starlette.middleware.cors import ALL_METHODS
from starlette.status import HTTP_302_FOUND

from backend.app.auth.identity import ANON_COOKIE_NAME, IdentityContext, identity_dependency
from backend.app.chat_contract import (
    ChatAction,
    ChatRequest as ContractChatRequest,
    ChatResponse as ContractChatResponse,
    ExpressionPlan,
    FailureType,
    MAX_PAYLOAD_BYTES,
)
from backend.app.schemas import ChatRequest, ChatResponse
from backend.app.service import ConversationService
from backend.app.config import get_settings, safe_error_detail, settings_public_summary
from backend.app.config.redaction import redact_secrets
from backend.app.config.settings import validate_for_env
from backend.app.db import check_db_connection
from backend.app.deps.plan_guard import post_accounting, precheck_plan_and_quotas
from backend.app.llm_client import LLMClient
from backend.app.observability import hash_subject, record_invocation, request_id as get_request_id, structured_log
from backend.app.observability.logging import safe_redact
from backend.app.plans.policy import Plan
from backend.app.plans.tokens import clamp_text_to_token_limit, estimate_tokens_from_text
from backend.app.perf import (
    PerfTimeoutError,
    api_chat_total_timeout_ms,
    enforce_timeout,
    model_call_timeout_ms,
    outbound_http_timeout_s,
    remaining_budget_ms,
)
from backend.app.waf import WAFError, waf_dependency


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
    },
)


_ALLOWED_ORIGINS = _settings.cors_origins_list()


app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = ConversationService()


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


def _failure_response(
    status_code: int,
    failure_type: FailureType,
    reason: str,
    action: ChatAction = ChatAction.REFUSE,
) -> JSONResponse:
    payload = ContractChatResponse(
        action=action,
        rendered_text="Governed request rejected.",
        failure_type=failure_type,
        failure_reason=reason[:200],
    )
    return JSONResponse(status_code=status_code, content=json.loads(payload.json()))


def _request_id(request: Request) -> str:
    try:
        existing = getattr(request.state, "request_id", None)
        if isinstance(existing, str) and existing.strip():
            return existing.strip()
    except Exception:
        pass
    rid = get_request_id(request)
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


@app.post("/api/chat", response_model=ContractChatResponse)
async def governed_chat(request: Request, identity: IdentityContext = Depends(waf_dependency)) -> ContractChatResponse | JSONResponse:
    start_ts = time.monotonic()
    budget_ms_total = api_chat_total_timeout_ms()
    rid = _request_id(request)
    http_timeout_ms = int(outbound_http_timeout_s() * 1000)

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
                )
                return JSONResponse(
                    status_code=400,
                    content={"ok": False, "error_code": "json_invalid", "message": "Request body must be valid JSON."},
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
            )
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error_code": "user_text_missing", "message": "user_text is required"},
            )

        try:
            chat_request = ContractChatRequest(**{"user_text": user_text})
        except ValidationError:
            latency_ms = (time.monotonic() - start_ts) * 1000
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
                error_code="request_schema_invalid",
                waf_limiter=waf_limiter,
                budget_ms_total=budget_ms_total,
                timeout_where=None,
                http_timeout_ms=http_timeout_ms,
            )
            return _failure_response(
                status_code=400,
                failure_type=FailureType.REQUEST_SCHEMA_INVALID,
                reason="request validation failed",
                action=ChatAction.REFUSE,
            )

        plan, limits, guard_error, input_tokens, budget_estimate = precheck_plan_and_quotas(chat_request.user_text, identity)
        try:
            request.state.plan_meta = {"decision": "allow", "error_code": None, "plan": plan.value}
        except Exception:
            pass
        if guard_error:
            if getattr(request.state, "waf_used_memory", False) and isinstance(guard_error, JSONResponse):
                guard_error.headers["X-WAF-Limiter"] = "memory-fallback"
            if isinstance(guard_error, JSONResponse):
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
                        "input_chars": len(chat_request.user_text),
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
                )
            return guard_error

        model_timeout_ms_value = model_call_timeout_ms()
        budget_remaining_before_model = remaining_budget_ms(start_ts, budget_ms_total)
        effective_model_timeout_ms = max(1000, min(model_timeout_ms_value, budget_remaining_before_model))
        timeout_where = None

        if budget_remaining_before_model <= 0:
            latency_ms = (time.monotonic() - start_ts) * 1000
            error_code = "timeout_budget_exhausted"
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
            )
            return _failure_response(
                status_code=500,
                failure_type=FailureType.TIMEOUT,
                reason="timeout",
                action=ChatAction.FALLBACK,
            )

        try:
            result = await enforce_timeout(
                lambda: asyncio.to_thread(render_governed_response, chat_request.user_text),
                effective_model_timeout_ms,
            )
        except Exception as exc:
            timeout_where = "model" if isinstance(exc, (asyncio.TimeoutError, PerfTimeoutError)) else timeout_where
            if isinstance(exc, (asyncio.TimeoutError, PerfTimeoutError)):
                latency_ms = (time.monotonic() - start_ts) * 1000
                error_code = "timeout"
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
                    budget_ms_remaining_at_model_start=budget_remaining_before_model,
                    timeout_where="model",
                    model_timeout_ms=effective_model_timeout_ms,
                    http_timeout_ms=http_timeout_ms,
                )
                return _failure_response(
                    status_code=500,
                    failure_type=FailureType.TIMEOUT,
                    reason="timeout",
                    action=ChatAction.FALLBACK,
                )
            hashed = hash_subject(identity.subject_type, identity.subject_id)
            logger.exception(
                "[API] chat internal error",
                extra={
                    "route": "/api/chat",
                    "request_id": rid,
                    "subject_type": identity.subject_type,
                    "hashed_subject": hashed,
                    "plan": plan.value,
                    "waf_limiter": waf_limiter,
                    "exc_type": type(exc).__name__,
                },
            )
            latency_ms = (time.monotonic() - start_ts) * 1000
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
                error_code="internal_error",
                waf_limiter=waf_limiter,
                budget_ms_total=budget_ms_total,
                budget_ms_remaining_at_model_start=budget_remaining_before_model,
                timeout_where=timeout_where,
                model_timeout_ms=effective_model_timeout_ms,
                http_timeout_ms=http_timeout_ms,
            )
            return _failure_response(
                status_code=500,
                failure_type=FailureType.INTERNAL_ERROR_SANITIZED,
                reason=_internal_error_reason(exc, rid),
                action=ChatAction.FALLBACK,
            )

        rendered_text = _extract_rendered_text(result) or "Governed response unavailable."
        rendered_text = clamp_text_to_token_limit(rendered_text, limits.max_output_tokens)
        if not result.ok and result.failure:
            failure_type = FailureType.GOVERNED_PIPELINE_ABORTED
            failure_reason = result.failure.reason_code[:200]
            response = ContractChatResponse(
                action=ChatAction.FALLBACK,
                rendered_text=rendered_text,
                failure_type=failure_type,
                failure_reason=failure_reason,
            )
            tokens_used = input_tokens + estimate_tokens_from_text(rendered_text)
            post_accounting(identity, tokens_used)
            json_payload = json.loads(response.json())
            headers = {}
            if getattr(request.state, "waf_used_memory", False):
                headers["X-WAF-Limiter"] = "memory-fallback"
            latency_ms = (time.monotonic() - start_ts) * 1000
            _log_chat_summary(
                request=request,
                request_id=rid,
                status_code=200,
                latency_ms=latency_ms,
                plan_value=plan.value,
                subject_type=identity.subject_type,
                subject_id=identity.subject_id,
                input_tokens=input_tokens,
                output_tokens_est=limits.max_output_tokens,
                error_code=failure_reason,
                waf_limiter=waf_limiter,
                budget_ms_total=budget_ms_total,
                budget_ms_remaining_at_model_start=budget_remaining_before_model,
                timeout_where=timeout_where,
                model_timeout_ms=effective_model_timeout_ms,
                http_timeout_ms=http_timeout_ms,
            )
            logger.info(
                "[API] chat governed failure",
                extra={
                    "route": "/api/chat",
                    "request_id": rid,
                    "subject_type": identity.subject_type,
                    "subject_id": identity.subject_id,
                    "plan": plan.value,
                    "input_chars": len(chat_request.user_text),
                    "input_tokens": input_tokens,
                    "tokens_used": tokens_used,
                    "failure_type": failure_type.value,
                    "failure_reason": failure_reason,
                    "status_code": 200,
                    "waf_limiter": waf_limiter,
                },
            )
            return JSONResponse(status_code=200, content=json_payload, headers=headers)

        action_value = ChatAction.ANSWER.value
        if result.output_json and isinstance(result.output_json, dict) and "question" in result.output_json:
            action_value = ChatAction.ASK_ONE_QUESTION.value

        response = ContractChatResponse(
            action=ChatAction(action_value),
            rendered_text=rendered_text if rendered_text.strip() else "Governed response unavailable.",
            failure_type=None,
            failure_reason=None,
        )
        tokens_used = input_tokens + estimate_tokens_from_text(rendered_text)
        post_accounting(identity, tokens_used)
        json_payload = json.loads(response.json())
        headers = {}
        if getattr(request.state, "waf_used_memory", False):
            headers["X-WAF-Limiter"] = "memory-fallback"
        latency_ms = (time.monotonic() - start_ts) * 1000
        _log_chat_summary(
            request=request,
            request_id=rid,
            status_code=200,
            latency_ms=latency_ms,
            plan_value=plan.value,
            subject_type=identity.subject_type,
            subject_id=identity.subject_id,
            input_tokens=input_tokens,
            output_tokens_est=limits.max_output_tokens,
            error_code=None,
            waf_limiter=waf_limiter,
            budget_ms_total=budget_ms_total,
            budget_ms_remaining_at_model_start=budget_remaining_before_model,
            timeout_where=timeout_where,
            model_timeout_ms=effective_model_timeout_ms,
            http_timeout_ms=http_timeout_ms,
        )
        logger.info(
            "[API] chat success",
            extra={
                "route": "/api/chat",
                "request_id": rid,
                "subject_type": identity.subject_type,
                "subject_id": identity.subject_id,
                "plan": plan.value,
                "input_chars": len(chat_request.user_text),
                "input_tokens": input_tokens,
                "tokens_used": tokens_used,
                "status_code": 200,
                "waf_limiter": waf_limiter,
            },
        )
        return JSONResponse(status_code=200, content=json_payload, headers=headers)

    try:
        return await enforce_timeout(_process, budget_ms_total)
    except Exception as exc:
        if isinstance(exc, (asyncio.TimeoutError, PerfTimeoutError)):
            latency_ms = (time.monotonic() - start_ts) * 1000
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
            )
            return _failure_response(
                status_code=500,
                failure_type=FailureType.TIMEOUT,
                reason="timeout",
                action=ChatAction.FALLBACK,
            )
        raise


@app.exception_handler(WAFError)
async def handle_waf_error(request: Request, exc: WAFError) -> JSONResponse:  # noqa: D401
    headers = exc.to_headers()
    if getattr(request.state, "waf_used_memory", False):
        headers["X-WAF-Limiter"] = "memory-fallback"
    return JSONResponse(status_code=exc.status_code, content=exc.to_body(), headers=headers)


@app.exception_handler(Exception)
async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:  # noqa: BLE001
    logger.exception("Unhandled error in request")
    content = {"ok": False, "error_code": "internal_error", "message": "Internal server error"}
    if str(_settings.debug_errors) == "1":
        content["detail"] = str(exc)
    return JSONResponse(status_code=500, content=content)
