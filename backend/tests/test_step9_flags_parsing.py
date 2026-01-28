import os

from backend.app.release.flags import ReleaseFlags, load_release_flags, parse_bool, parse_int_clamped


def test_parse_bool_variants():
    assert parse_bool("1", False) is True
    assert parse_bool("true", False) is True
    assert parse_bool("yes", False) is True
    assert parse_bool("0", True) is False
    assert parse_bool("false", True) is False
    assert parse_bool("no", True) is False
    assert parse_bool("unexpected", True) is True
    assert parse_bool(None, False) is False


def test_parse_int_clamped_bounds():
    assert parse_int_clamped("-5", 10, 0, 100) == 0
    assert parse_int_clamped("250", 10, 0, 100) == 100
    assert parse_int_clamped("20", 10, 0, 100) == 20
    assert parse_int_clamped(None, 10, 0, 100) == 10
    assert parse_int_clamped("bad", 5, 0, 100) == 5


def test_allowlist_and_defaults_on_invalid(monkeypatch):
    monkeypatch.setenv("RELEASE_CANARY_ENABLED", "true")
    monkeypatch.setenv("RELEASE_CANARY_PERCENT", "25")
    monkeypatch.setenv("RELEASE_CANARY_ALLOWLIST", " user1 , ,user2,, ")
    monkeypatch.setenv("RELEASE_HEADER_BUILD_VERSION", "1")
    monkeypatch.setenv("RELEASE_HEADER_CANARY", "0")
    monkeypatch.setenv("RELEASE_CHAT_SUMMARY_CANARY", "1")
    monkeypatch.setenv("RELEASE_CHAT_SUMMARY_FLAGS", "true")
    flags = load_release_flags()
    assert flags.canary_enabled is True
    assert flags.canary_percent == 25
    assert flags.canary_allowlist == {"user1", "user2"}
    assert flags.header_build_version_enabled is True
    assert flags.header_canary_enabled is False
    assert flags.chat_summary_canary_field_enabled is True
    assert flags.chat_summary_flags_field_enabled is True

    # invalid percent should fallback to default
    monkeypatch.setenv("RELEASE_CANARY_PERCENT", "not-an-int")
    flags2 = load_release_flags()
    assert flags2.canary_percent == ReleaseFlags().canary_percent

    # invalid bool should fallback to defaults
    monkeypatch.setenv("RELEASE_HEADER_CANARY", "maybe")
    flags3 = load_release_flags()
    assert flags3.header_canary_enabled == ReleaseFlags().header_canary_enabled

    # ensure allowlist trims empties
    monkeypatch.setenv("RELEASE_CANARY_ALLOWLIST", " ,  ,  ")
    flags4 = load_release_flags()
    assert flags4.canary_allowlist == set()

    for var in list(os.environ.keys()):
        if var.startswith("RELEASE_"):
            monkeypatch.delenv(var, raising=False)
