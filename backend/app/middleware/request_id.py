"""
Request ID middleware for observability.

Generates and propagates X-Request-ID headers for all requests.
Logs one line per request with method, path, status, duration_ms, request_id.
Never logs request body.
"""

import re
import time
import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Safe pattern for incoming X-Request-ID: hex/uuid-ish, max 64 chars
_SAFE_REQUEST_ID_PATTERN = re.compile(r"^[a-fA-F0-9\-]{1,64}$")


class RequestIdMiddleware:
    """
    ASGI middleware that:
    - Generates X-Request-ID for every request (uuid4)
    - Adds X-Request-ID to response headers
    - Logs ONE line per request: method, path, status, duration_ms, request_id
    - Never logs request body
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.monotonic()
        request_id = self._generate_request_id(scope)
        
        # Store request_id in scope for downstream access
        scope["state"] = scope.get("state", {})
        scope["state"]["request_id"] = request_id
        
        method = scope.get("method", "?")
        path = scope.get("path", "?")
        status_code: Optional[int] = None
        
        async def send_wrapper(message):
            nonlocal status_code
            
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
                
                # Add X-Request-ID to response headers
                headers = list(message.get("headers", []))
                
                # Check if X-Request-ID already exists
                has_request_id = any(
                    h[0].lower() == b"x-request-id" 
                    for h in headers 
                    if len(h) >= 2 and isinstance(h[0], bytes)
                )
                
                if not has_request_id:
                    headers.append((b"x-request-id", request_id.encode("utf-8")))
                
                new_message = message.copy()
                new_message["headers"] = headers
                await send(new_message)
            else:
                await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            # Log one line per request (no body)
            logger.info(
                "[HTTP] request",
                extra={
                    "method": method,
                    "path": path,
                    "status": status_code,
                    "duration_ms": duration_ms,
                    "request_id": request_id,
                }
            )
    
    def _generate_request_id(self, scope) -> str:
        """Generate or extract request ID with safe pattern validation."""
        # Check for existing X-Request-ID header
        headers = scope.get("headers", [])
        for name, value in headers:
            if isinstance(name, bytes) and name.lower() == b"x-request-id":
                if isinstance(value, bytes):
                    existing = value.decode("utf-8", errors="replace").strip()
                    # Only reuse if it matches safe pattern (hex/uuid-ish, max 64 chars)
                    if existing and _SAFE_REQUEST_ID_PATTERN.match(existing):
                        return existing
        
        # Generate new UUID
        return str(uuid.uuid4())
