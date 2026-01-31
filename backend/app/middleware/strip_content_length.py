"""
ASGI middleware to strip Content-Length headers from HTTP responses.

This prevents "Response content longer than Content-Length" errors that can occur
with streaming responses, particularly in production environments like Railway.
"""

from typing import Callable, Dict, List, Tuple


class StripContentLengthMiddleware:
    """
    ASGI middleware that removes Content-Length headers from HTTP responses.
    
    This is safer than BaseHTTPMiddleware for streaming responses and prevents
    content length mismatch errors in production.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            # Pass through non-HTTP requests unchanged
            await self.app(scope, receive, send)
            return
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Strip Content-Length header if present
                headers = message.get("headers", [])
                filtered_headers = []
                
                for header_tuple in headers:
                    if len(header_tuple) >= 2:
                        header_name = header_tuple[0]
                        if isinstance(header_name, bytes):
                            # Check if this is a content-length header (case-insensitive)
                            if header_name.lower() != b"content-length":
                                filtered_headers.append(header_tuple)
                        else:
                            # Keep non-bytes headers as-is
                            filtered_headers.append(header_tuple)
                    else:
                        # Keep malformed headers as-is
                        filtered_headers.append(header_tuple)
                
                # Create new message with filtered headers
                new_message = message.copy()
                new_message["headers"] = filtered_headers
                await send(new_message)
            else:
                # Pass through all other message types unchanged
                await send(message)
        
        await self.app(scope, receive, send_wrapper)
