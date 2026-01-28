from backend.app.release import ReleaseFlags, decide_canary, canary_bucket


def test_canary_bucket_deterministic():
    rid = "deterministic-id"
    assert canary_bucket(rid) == 43
    assert canary_bucket(rid) == canary_bucket(rid)


def test_canary_disabled_forces_false_even_with_percent_or_allowlist():
    flags = ReleaseFlags(canary_enabled=False, canary_percent=100, canary_allowlist={"user1"})
    assert decide_canary("any", "user1", flags) is False
    assert decide_canary("any", None, flags) is False


def test_allowlist_requires_enabled():
    flags = ReleaseFlags(canary_enabled=True, canary_percent=0, canary_allowlist={"user1"})
    assert decide_canary("any", "user1", flags) is True
    assert decide_canary("any", None, flags) is False


def test_percent_full_and_zero_behavior():
    flags_full = ReleaseFlags(canary_enabled=True, canary_percent=100, canary_allowlist=set())
    assert decide_canary("any", None, flags_full) is True

    flags_zero = ReleaseFlags(canary_enabled=True, canary_percent=0, canary_allowlist=set())
    assert decide_canary("any", None, flags_zero) is False


def test_percent_one_deterministic_fixed_request():
    rid = "deterministic-id"
    flags = ReleaseFlags(canary_enabled=True, canary_percent=1, canary_allowlist=set())
    bucket = canary_bucket(rid)
    expected = bucket < 1
    assert decide_canary(rid, None, flags) is expected
    # deterministic
    assert decide_canary(rid, None, flags) is expected
