from __future__ import annotations

from typing import Dict


def security_headers(*, is_https: bool, is_non_local: bool) -> Dict[str, str]:
    """Return deterministic security headers for API responses."""
    headers: Dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "X-Frame-Options": "DENY",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Cache-Control": "no-store",
    }
    if is_https and is_non_local:
        headers["Strict-Transport-Security"] = "max-age=15552000; includeSubDomains"
    return headers


def apply_security_headers(response, *, is_https: bool, is_non_local: bool) -> None:
    """Mutate response headers to include required security headers."""
    hdrs = security_headers(is_https=is_https, is_non_local=is_non_local)
    for key, value in hdrs.items():
        response.headers[key] = value


def maybe_harden_cookies(response, *, should_secure: bool) -> None:
    """Append Secure and SameSite=None flags to Set-Cookie headers for cross-origin credentials."""
    if not should_secure:
        return
    cookies = response.headers.getlist("set-cookie") if hasattr(response.headers, "getlist") else []
    if not cookies:
        return
    updated = []
    for cookie in cookies:
        # Add Secure flag if missing
        if "secure" not in cookie.lower():
            cookie = f"{cookie}; Secure"
        # Add SameSite=None if no SameSite is set (required for cross-origin credentials)
        if "samesite" not in cookie.lower():
            cookie = f"{cookie}; SameSite=None"
        updated.append(cookie)
    if hasattr(response.headers, "pop"):
        response.headers.pop("set-cookie", None)
    for cookie in updated:
        response.headers.append("set-cookie", cookie)


__all__ = ["security_headers", "apply_security_headers", "maybe_harden_cookies"]
