from __future__ import annotations

import json
import logging
import os
import time
import uuid
from logging.config import dictConfig
from typing import Any, Dict

from fastapi import FastAPI, Path, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .config import settings
from .db import check_db_connection
from .schemas import ChatRequest, ChatResponse
from .service import ConversationService
from backend.mci_backend.decision_assembly import assemble_decision_state
from backend.mci_backend.expression_assembly import assemble_output_plan
from backend.mci_backend.governed_response_runtime import render_governed_response
from backend.mci_backend.model_contract import ModelInvocationResult
from backend.mci_backend.orchestration_assembly import assemble_control_plan
from .chat_contract import (
    ChatAction,
    ChatRequest as ContractChatRequest,
    ChatResponse as ContractChatResponse,
    FailureType,
    MAX_PAYLOAD_BYTES,
)


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


def _configured_origins() -> list[str]:
    if settings.cors_origins:
        # If "*" present, permit all
        if "*" in settings.cors_origins:
            return ["*"]
        return settings.cors_origins
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


_ALLOWED_ORIGINS = _configured_origins()


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


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "version": APP_VERSION,
        "uptime_seconds": int(time.monotonic() - _start_time),
    }


def _env_missing(required: list[str]) -> list[str]:
    return [var for var in required if not os.getenv(var)]


@app.get("/ready")
async def ready() -> JSONResponse:
    try:
        current_env = os.getenv("ENV", settings.env)
        required = settings.required_env_vars()
        missing = _env_missing(required) if current_env.lower() == "production" else []

        db_status = {"configured": bool(os.getenv("DATABASE_URL") or settings.database_url), "ok": True}
        if db_status["configured"]:
            db_ok, db_reason = check_db_connection()
            db_status["ok"] = db_ok
            if db_reason:
                db_status["reason"] = db_reason

        model_key_present = bool(os.getenv("MODEL_PROVIDER_API_KEY") or settings.model_provider_api_key)

        if current_env.lower() == "production":
            if missing:
                return JSONResponse(
                    status_code=503,
                    content={"status": "not_ready", "missing_env": missing, "db": db_status, "model_key": model_key_present},
                )
            if not model_key_present:
                return JSONResponse(
                    status_code=503,
                    content={"status": "not_ready", "missing_env": ["MODEL_PROVIDER_API_KEY"], "db": db_status},
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
async def governed_chat(request: Request) -> ContractChatResponse | JSONResponse:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_PAYLOAD_BYTES:
                return _failure_response(
                    status_code=413,
                    failure_type=FailureType.REQUEST_TOO_LARGE,
                    reason="payload too large",
                    action=ChatAction.REFUSE,
                )
        except ValueError:
            return _failure_response(
                status_code=400,
                failure_type=FailureType.REQUEST_SCHEMA_INVALID,
                reason="invalid content-length",
                action=ChatAction.REFUSE,
            )

    raw_body = await request.body()
    if len(raw_body) > MAX_PAYLOAD_BYTES:
        return _failure_response(
            status_code=413,
            failure_type=FailureType.REQUEST_TOO_LARGE,
            reason="payload too large",
            action=ChatAction.REFUSE,
        )

    try:
        payload: Dict[str, Any] = json.loads(raw_body or "{}")
    except json.JSONDecodeError:
        return _failure_response(
            status_code=400,
            failure_type=FailureType.REQUEST_SCHEMA_INVALID,
            reason="invalid json",
            action=ChatAction.REFUSE,
        )

    if not isinstance(payload, dict):
        return _failure_response(
            status_code=400,
            failure_type=FailureType.REQUEST_SCHEMA_INVALID,
            reason="payload must be object",
            action=ChatAction.REFUSE,
        )

    if "user_text" in payload and isinstance(payload["user_text"], str) and not payload["user_text"].strip():
        return _failure_response(
            status_code=400,
            failure_type=FailureType.EMPTY_INPUT,
            reason="user_text empty",
            action=ChatAction.REFUSE,
        )

    try:
        chat_request = ContractChatRequest(**payload)
    except ValidationError:
        return _failure_response(
            status_code=400,
            failure_type=FailureType.REQUEST_SCHEMA_INVALID,
            reason="request validation failed",
            action=ChatAction.REFUSE,
        )

    try:
        trace_id = str(uuid.uuid4())
        decision_id = str(uuid.uuid4())
        decision_state = assemble_decision_state(decision_id=decision_id, trace_id=trace_id, message=chat_request.user_text)
        control_plan = assemble_control_plan(chat_request.user_text, decision_state)
        output_plan = assemble_output_plan(chat_request.user_text, decision_state, control_plan)
        result = render_governed_response(chat_request.user_text)
    except Exception:
        return _failure_response(
            status_code=500,
            failure_type=FailureType.INTERNAL_ERROR_SANITIZED,
            reason="sanitized failure",
            action=ChatAction.FALLBACK,
        )

    rendered_text = _extract_rendered_text(result) or "Governed response unavailable."
    if not result.ok and result.failure:
        failure_type = FailureType.GOVERNED_PIPELINE_ABORTED
        failure_reason = result.failure.reason_code[:200]
        response = ContractChatResponse(
            action=ChatAction.FALLBACK,
            rendered_text=rendered_text,
            failure_type=failure_type,
            failure_reason=failure_reason,
        )
        return response

    response = ContractChatResponse(
        action=ChatAction(output_plan.action.value),
        rendered_text=rendered_text if rendered_text.strip() else "Governed response unavailable.",
        failure_type=None,
        failure_reason=None,
    )
    return response
