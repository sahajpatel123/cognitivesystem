from __future__ import annotations

import logging
from logging.config import dictConfig

from fastapi import FastAPI, Path
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .schemas import ChatRequest, ChatResponse
from .service import ConversationService


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
