from backend.app.security.abuse import AbuseContext, decide_abuse


def _ctx(**kwargs) -> AbuseContext:
    return AbuseContext(
        path=kwargs.get("path", "/api/chat"),
        request_id=kwargs.get("request_id", "rid"),
        ip_hash=kwargs.get("ip_hash"),
        actor_key=kwargs.get("actor_key"),
        subject_type=kwargs.get("subject_type"),
        subject_id=kwargs.get("subject_id"),
        waf_limiter=kwargs.get("waf_limiter"),
        user_agent=kwargs.get("user_agent"),
        accept=kwargs.get("accept"),
        content_type=kwargs.get("content_type"),
        method=kwargs.get("method", "POST"),
        has_auth=kwargs.get("has_auth", False),
        is_sensitive_path=kwargs.get("is_sensitive_path", True),
        request_scheme=kwargs.get("request_scheme", "https"),
        is_non_local=kwargs.get("is_non_local", True),
    )


def test_rate_limit_threshold():
    ctx = _ctx(user_agent="", accept="", has_auth=False, content_type="", request_scheme="https", is_non_local=True)
    dec = decide_abuse(ctx)
    assert dec.allowed is False
    assert dec.action == "RATE_LIMIT"
    assert 70 <= dec.score < 90


def test_block_threshold():
    ctx = _ctx(
        user_agent="",
        accept="",
        has_auth=False,
        content_type="",
        method="POST",
        waf_limiter="limited",
        request_scheme="http",
        is_non_local=True,
    )
    dec = decide_abuse(ctx)
    assert dec.allowed is False
    assert dec.action == "BLOCK"
    assert dec.score >= 90


def test_allow_normal_headers():
    ctx = _ctx(user_agent="curl/7.0", accept="application/json", content_type="application/json", has_auth=True)
    dec = decide_abuse(ctx)
    assert dec.allowed is True
    assert dec.action == "ALLOW"


def test_score_capped():
    ctx = _ctx(
        user_agent="",
        accept="",
        content_type="",
        method="TRACE",
        has_auth=False,
        waf_limiter="limited",
        request_scheme="http",
        is_non_local=True,
    )
    dec = decide_abuse(ctx)
    assert dec.score <= 100
