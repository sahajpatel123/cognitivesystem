"""Request helper utilities for handling proxy headers and scheme detection."""

from __future__ import annotations

from fastapi import Request


def get_request_scheme(request: Request) -> str:
    """
    Get the actual request scheme, respecting proxy headers.
    
    When behind a reverse proxy (Railway, Vercel, etc.), the backend sees http
    but the actual client connection is https. We must trust X-Forwarded-Proto.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        "https" or "http" based on X-Forwarded-Proto header or request.url.scheme
    """
    # Trust X-Forwarded-Proto from proxy (Railway, Vercel, etc.)
    forwarded_proto = request.headers.get("x-forwarded-proto")
    if forwarded_proto:
        return forwarded_proto.lower().strip()
    
    # Fallback to direct scheme
    return request.url.scheme


def is_https_request(request: Request) -> bool:
    """
    Check if the request is HTTPS, respecting proxy headers.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        True if request is HTTPS (either direct or via X-Forwarded-Proto)
    """
    return get_request_scheme(request) == "https"


__all__ = ["get_request_scheme", "is_https_request"]
