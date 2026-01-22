from __future__ import annotations

from typing import Optional

from backend.app.config import get_settings

API_CHAT_TOTAL_TIMEOUT_MS_DEFAULT = 20_000
MODEL_CALL_TIMEOUT_MS_DEFAULT = 12_000
OUTBOUND_HTTP_TIMEOUT_S_DEFAULT = 8.0
OUTBOUND_HTTP_CONNECT_TIMEOUT_S_DEFAULT = 3.0
OUTBOUND_HTTP_READ_TIMEOUT_S_DEFAULT = 8.0
OUTBOUND_HTTP_MAX_CONNECTIONS_DEFAULT = 20
OUTBOUND_HTTP_MAX_KEEPALIVE_CONNECTIONS_DEFAULT = 10
OUTBOUND_HTTP_KEEPALIVE_EXPIRY_S_DEFAULT = 30.0
OUTBOUND_HTTP_MAX_REQUEST_RETRIES_DEFAULT = 0


def _clamp_positive_int(value: Optional[int], default: int) -> int:
    try:
        v = int(value)
        return v if v > 0 else default
    except Exception:
        return default


def _clamp_positive_float(value: Optional[float], default: float) -> float:
    try:
        v = float(value)
        return v if v > 0 else default
    except Exception:
        return default


def api_chat_total_timeout_ms() -> int:
    settings = get_settings()
    return _clamp_positive_int(getattr(settings, "api_chat_total_timeout_ms", API_CHAT_TOTAL_TIMEOUT_MS_DEFAULT), API_CHAT_TOTAL_TIMEOUT_MS_DEFAULT)


def model_call_timeout_ms() -> int:
    settings = get_settings()
    return _clamp_positive_int(getattr(settings, "model_call_timeout_ms", MODEL_CALL_TIMEOUT_MS_DEFAULT), MODEL_CALL_TIMEOUT_MS_DEFAULT)


def outbound_http_timeout_s() -> float:
    settings = get_settings()
    return _clamp_positive_float(getattr(settings, "outbound_http_timeout_s", OUTBOUND_HTTP_TIMEOUT_S_DEFAULT), OUTBOUND_HTTP_TIMEOUT_S_DEFAULT)


def outbound_http_connect_timeout_s() -> float:
    settings = get_settings()
    return _clamp_positive_float(
        getattr(settings, "outbound_http_connect_timeout_s", OUTBOUND_HTTP_CONNECT_TIMEOUT_S_DEFAULT),
        OUTBOUND_HTTP_CONNECT_TIMEOUT_S_DEFAULT,
    )


def outbound_http_read_timeout_s() -> float:
    settings = get_settings()
    return _clamp_positive_float(
        getattr(settings, "outbound_http_read_timeout_s", OUTBOUND_HTTP_READ_TIMEOUT_S_DEFAULT),
        OUTBOUND_HTTP_READ_TIMEOUT_S_DEFAULT,
    )


def outbound_http_max_connections() -> int:
    settings = get_settings()
    return _clamp_positive_int(
        getattr(settings, "outbound_http_max_connections", OUTBOUND_HTTP_MAX_CONNECTIONS_DEFAULT),
        OUTBOUND_HTTP_MAX_CONNECTIONS_DEFAULT,
    )


def outbound_http_max_keepalive_connections() -> int:
    settings = get_settings()
    return _clamp_positive_int(
        getattr(settings, "outbound_http_max_keepalive_connections", OUTBOUND_HTTP_MAX_KEEPALIVE_CONNECTIONS_DEFAULT),
        OUTBOUND_HTTP_MAX_KEEPALIVE_CONNECTIONS_DEFAULT,
    )


def outbound_http_keepalive_expiry_s() -> float:
    settings = get_settings()
    return _clamp_positive_float(
        getattr(settings, "outbound_http_keepalive_expiry_s", OUTBOUND_HTTP_KEEPALIVE_EXPIRY_S_DEFAULT),
        OUTBOUND_HTTP_KEEPALIVE_EXPIRY_S_DEFAULT,
    )
