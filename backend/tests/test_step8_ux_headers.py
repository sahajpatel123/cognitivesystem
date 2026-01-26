from backend.app.ux.state import UXState, build_ux_headers, decide_ux_state, extract_cooldown_seconds


def test_extract_cooldown_seconds_parses_and_clamps():
    headers = {"Retry-After": "5"}
    assert extract_cooldown_seconds(headers) == 5
    headers_big = {"Retry-After": "999999"}
    assert extract_cooldown_seconds(headers_big) == 86400
    headers_invalid = {"Retry-After": "not-an-int"}
    assert extract_cooldown_seconds(headers_invalid) is None


def test_build_ux_headers_has_state_and_optional_cooldown():
    hdrs = build_ux_headers(UXState.OK, None)
    assert hdrs.get("X-UX-State") == UXState.OK.value
    assert "X-Cooldown-Seconds" not in hdrs
    hdrs_cd = build_ux_headers(UXState.RATE_LIMITED, 10)
    assert hdrs_cd["X-UX-State"] == UXState.RATE_LIMITED.value
    assert hdrs_cd["X-Cooldown-Seconds"] == "10"
    assert "user_text" not in "".join(hdrs_cd.keys()).lower()
    assert "rendered_text" not in "".join(hdrs_cd.keys()).lower()


def test_build_headers_do_not_leak_user_fields():
    ux_state = decide_ux_state(status_code=200, action="ANSWER", failure_type=None)
    hdrs = build_ux_headers(ux_state, None)
    assert hdrs["X-UX-State"] == UXState.OK.value
    header_blob = "".join(hdrs.keys()).lower()
    assert "user_text" not in header_blob
    assert "rendered_text" not in header_blob


def test_cooldown_added_when_rate_limited_with_retry_after():
    ux_state = decide_ux_state(status_code=429, action=None, failure_type=None)
    cooldown = extract_cooldown_seconds({"Retry-After": "120000"})
    assert cooldown == 86400
    hdrs = build_ux_headers(ux_state, cooldown)
    assert hdrs["X-UX-State"] == UXState.RATE_LIMITED.value
    assert hdrs["X-Cooldown-Seconds"] == "86400"
