from __future__ import annotations

import json
import logging
import uuid
from logging.config import dictConfig
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Path, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .config import settings
from .schemas import ChatRequest, ChatResponse
from .service import ConversationService
from mci_backend.decision_assembly import assemble_decision_state
from mci_backend.expression_assembly import assemble_output_plan
from mci_backend.governed_response_runtime import render_governed_response
from mci_backend.model_contract import ModelInvocationResult
from mci_backend.orchestration_assembly import assemble_control_plan
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

app = FastAPI(title="Cognitive Conversational Prototype")

# Allow dev frontends on localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

    logger.info(
        "[API] Incoming message",
        extra={"session_id": session_id, "message": payload.message},
    )
    response = service.handle_message(session_id=session_id, text=payload.message)
    logger.info(
        "[API] Outgoing message",
        extra={"session_id": session_id, "message": response.message},
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
