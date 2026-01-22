from __future__ import annotations

import httpx

from backend.app.perf.budgets import (
    outbound_http_connect_timeout_s,
    outbound_http_keepalive_expiry_s,
    outbound_http_max_connections,
    outbound_http_max_keepalive_connections,
    outbound_http_read_timeout_s,
    outbound_http_timeout_s,
)

_shared_client: httpx.Client | None = None


def get_shared_httpx_client() -> httpx.Client:
    global _shared_client
    if _shared_client is not None:
        return _shared_client
    timeout = httpx.Timeout(
        outbound_http_timeout_s(),
        connect=outbound_http_connect_timeout_s(),
        read=outbound_http_read_timeout_s(),
    )
    limits = httpx.Limits(
        max_connections=outbound_http_max_connections(),
        max_keepalive_connections=outbound_http_max_keepalive_connections(),
        keepalive_expiry=outbound_http_keepalive_expiry_s(),
    )
    _shared_client = httpx.Client(timeout=timeout, limits=limits)
    return _shared_client
