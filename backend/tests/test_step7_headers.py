from fastapi import Response

from backend.app.security.headers import apply_security_headers, security_headers


def test_security_headers_required_keys_present():
    hdrs = security_headers(is_https=False, is_non_local=False)
    for key in [
        "X-Content-Type-Options",
        "Referrer-Policy",
        "X-Frame-Options",
        "Permissions-Policy",
        "Cache-Control",
    ]:
        assert key in hdrs
    assert hdrs["Cache-Control"] == "no-store"
    assert hdrs["X-Content-Type-Options"] == "nosniff"


def test_hsts_only_https_and_non_local():
    hdrs_http = security_headers(is_https=False, is_non_local=True)
    assert "Strict-Transport-Security" not in hdrs_http

    hdrs_local = security_headers(is_https=True, is_non_local=False)
    assert "Strict-Transport-Security" not in hdrs_local

    hdrs_prod = security_headers(is_https=True, is_non_local=True)
    assert hdrs_prod.get("Strict-Transport-Security") == "max-age=15552000; includeSubDomains"


def test_cache_control_present_for_api():
    hdrs = security_headers(is_https=False, is_non_local=False)
    assert hdrs.get("Cache-Control") == "no-store"


def test_apply_security_headers_sets_canonical_keys():
    resp = Response()
    resp.headers["Cache-Control"] = "max-age=1000"
    apply_security_headers(resp, is_https=False, is_non_local=False)
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["Cache-Control"] == "no-store"
    assert "Strict-Transport-Security" not in resp.headers


def test_apply_hsts_only_https_and_non_local():
    resp_http = Response()
    apply_security_headers(resp_http, is_https=False, is_non_local=True)
    assert "Strict-Transport-Security" not in resp_http.headers

    resp_local = Response()
    apply_security_headers(resp_local, is_https=True, is_non_local=False)
    assert "Strict-Transport-Security" not in resp_local.headers

    resp_prod = Response()
    apply_security_headers(resp_prod, is_https=True, is_non_local=True)
    assert resp_prod.headers.get("Strict-Transport-Security") == "max-age=15552000; includeSubDomains"
