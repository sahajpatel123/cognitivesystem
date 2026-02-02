#!/usr/bin/env python3
"""
Self-contained tests for DB allowlist environment mismatch detection.
Run: PYTHONPATH=. python3 backend/tests/test_db_allowlist_env_mismatch.py
"""

from __future__ import annotations

import sys
from typing import List


class TestResult:
    """Simple test result tracker."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: List[str] = []
    
    def assert_true(self, condition: bool, message: str):
        if condition:
            self.passed += 1
        else:
            self.failed += 1
            self.errors.append(f"FAIL: {message}")
    
    def assert_equal(self, actual, expected, message: str):
        self.assert_true(actual == expected, f"{message} (got {actual!r}, expected {expected!r})")


def test_exact_match_host():
    """Case A: Exact match host (allowlist has host only, no port)."""
    print("Test A: Exact match host")
    result = TestResult()
    
    from backend.app.config.diagnostics_db_allowlist import snapshot_db_allowlist_state
    
    snap = snapshot_db_allowlist_state(
        database_url="postgresql://user:pass@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres",
        allowlist_csv="aws-1-ap-southeast-2.pooler.supabase.com",
        app_env="production",
    )
    
    result.assert_equal(snap["db_hostname"], "aws-1-ap-southeast-2.pooler.supabase.com", "hostname extracted")
    result.assert_equal(snap["db_port"], 6543, "port extracted")
    result.assert_equal(snap["match"], True, "should match host-only entry")
    result.assert_equal(snap["allowlist_count"], 1, "allowlist count")
    
    return result


def test_match_host_port():
    """Case B: Match host:port (allowlist has host:port)."""
    print("Test B: Match host:port")
    result = TestResult()
    
    from backend.app.config.diagnostics_db_allowlist import snapshot_db_allowlist_state
    
    snap = snapshot_db_allowlist_state(
        database_url="postgresql://user:pass@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres",
        allowlist_csv="aws-1-ap-southeast-2.pooler.supabase.com:6543",
        app_env="production",
    )
    
    result.assert_equal(snap["match"], True, "should match host:port entry")
    
    # Test port mismatch
    snap2 = snapshot_db_allowlist_state(
        database_url="postgresql://user:pass@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres",
        allowlist_csv="aws-1-ap-southeast-2.pooler.supabase.com:5432",
        app_env="production",
    )
    
    result.assert_equal(snap2["match"], False, "should NOT match with wrong port")
    
    return result


def test_mismatch_host_region():
    """Case C: Mismatch host (ap-south-1 vs ap-southeast-2)."""
    print("Test C: Mismatch host (region mismatch)")
    result = TestResult()
    
    from backend.app.config.diagnostics_db_allowlist import snapshot_db_allowlist_state
    
    # DATABASE_URL has ap-southeast-2, allowlist has ap-south-1
    snap = snapshot_db_allowlist_state(
        database_url="postgresql://user:pass@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres",
        allowlist_csv="aws-1-ap-south-1.pooler.supabase.com,aws-1-ap-south-1.pooler.supabase.com:6543",
        app_env="production",
    )
    
    result.assert_equal(snap["db_hostname"], "aws-1-ap-southeast-2.pooler.supabase.com", "hostname extracted")
    result.assert_equal(snap["match"], False, "should NOT match - region mismatch")
    result.assert_equal(snap["allowlist_count"], 2, "allowlist has 2 entries")
    result.assert_equal(snap["allowlist_entries"], [
        "aws-1-ap-south-1.pooler.supabase.com",
        "aws-1-ap-south-1.pooler.supabase.com:6543",
    ], "allowlist entries")
    
    return result


def test_empty_allowlist_fail_closed():
    """Case D: Empty allowlist -> fail-closed."""
    print("Test D: Empty allowlist -> fail-closed")
    result = TestResult()
    
    from backend.app.config.diagnostics_db_allowlist import snapshot_db_allowlist_state
    
    # Empty allowlist
    snap = snapshot_db_allowlist_state(
        database_url="postgresql://user:pass@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres",
        allowlist_csv="",
        app_env="production",
    )
    
    result.assert_equal(snap["match"], False, "empty allowlist should not match")
    result.assert_equal(snap["allowlist_count"], 0, "allowlist count should be 0")
    
    # None allowlist
    snap2 = snapshot_db_allowlist_state(
        database_url="postgresql://user:pass@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres",
        allowlist_csv=None,
        app_env="production",
    )
    
    result.assert_equal(snap2["match"], False, "None allowlist should not match")
    result.assert_equal(snap2["allowlist_count"], 0, "allowlist count should be 0")
    
    return result


def test_malformed_database_url_fail_closed():
    """Case E: Malformed DATABASE_URL -> fail-closed."""
    print("Test E: Malformed DATABASE_URL -> fail-closed")
    result = TestResult()
    
    from backend.app.config.diagnostics_db_allowlist import snapshot_db_allowlist_state
    
    # Empty DATABASE_URL
    snap = snapshot_db_allowlist_state(
        database_url="",
        allowlist_csv="aws-1-ap-southeast-2.pooler.supabase.com",
        app_env="production",
    )
    
    result.assert_equal(snap["db_hostname"], None, "empty URL should have None hostname")
    result.assert_equal(snap["match"], False, "empty URL should not match")
    
    # None DATABASE_URL
    snap2 = snapshot_db_allowlist_state(
        database_url=None,
        allowlist_csv="aws-1-ap-southeast-2.pooler.supabase.com",
        app_env="production",
    )
    
    result.assert_equal(snap2["db_hostname"], None, "None URL should have None hostname")
    result.assert_equal(snap2["match"], False, "None URL should not match")
    
    # Malformed URL (no host)
    snap3 = snapshot_db_allowlist_state(
        database_url="not-a-url",
        allowlist_csv="aws-1-ap-southeast-2.pooler.supabase.com",
        app_env="production",
    )
    
    result.assert_equal(snap3["db_hostname"], None, "malformed URL should have None hostname")
    result.assert_equal(snap3["match"], False, "malformed URL should not match")
    
    return result


def test_no_secrets_in_snapshot():
    """Ensure snapshot does not contain secrets."""
    print("Test F: No secrets in snapshot")
    result = TestResult()
    
    import json
    from backend.app.config.diagnostics_db_allowlist import snapshot_db_allowlist_state
    
    secret_user = "SECRET_USER_123"
    secret_pass = "SECRET_PASS_456"
    
    snap = snapshot_db_allowlist_state(
        database_url=f"postgresql://{secret_user}:{secret_pass}@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres",
        allowlist_csv="aws-1-ap-southeast-2.pooler.supabase.com",
        app_env="production",
    )
    
    json_output = json.dumps(snap)
    result.assert_true(secret_user not in json_output, f"secret user should not appear in snapshot")
    result.assert_true(secret_pass not in json_output, f"secret pass should not appear in snapshot")
    result.assert_true("@" not in json_output, "@ should not appear in snapshot (no netloc)")
    
    return result


def test_guards_error_message_safe():
    """Ensure guards.py error message is safe (no secrets)."""
    print("Test G: Guards error message is safe")
    result = TestResult()
    
    from backend.app.config.guards import _extract_db_host_port, _host_matches, _parse_and_validate_allowlist
    
    secret_user = "SECRET_USER_789"
    secret_pass = "SECRET_PASS_ABC"
    database_url = f"postgresql://{secret_user}:{secret_pass}@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"
    
    db_host, db_port = _extract_db_host_port(database_url)
    
    result.assert_equal(db_host, "aws-1-ap-southeast-2.pooler.supabase.com", "host extracted correctly")
    result.assert_equal(db_port, 6543, "port extracted correctly")
    result.assert_true(secret_user not in str(db_host), "secret user not in host")
    result.assert_true(secret_pass not in str(db_host), "secret pass not in host")
    
    # Verify allowlist parsing
    allowlist_raw = ["aws-1-ap-south-1.pooler.supabase.com", "aws-1-ap-south-1.pooler.supabase.com:6543"]
    parsed, valid = _parse_and_validate_allowlist(allowlist_raw)
    result.assert_true(valid, "allowlist should be valid")
    
    # Verify mismatch
    match = _host_matches(db_host, db_port, parsed)
    result.assert_true(not match, "should not match - region mismatch")
    
    return result


def main():
    """Run all tests and report results."""
    print("=" * 60)
    print("DB ALLOWLIST ENV MISMATCH TESTS")
    print("=" * 60)
    
    tests = [
        test_exact_match_host,
        test_match_host_port,
        test_mismatch_host_region,
        test_empty_allowlist_fail_closed,
        test_malformed_database_url_fail_closed,
        test_no_secrets_in_snapshot,
        test_guards_error_message_safe,
    ]
    
    total_passed = 0
    total_failed = 0
    all_errors = []
    
    for test_fn in tests:
        try:
            result = test_fn()
            total_passed += result.passed
            total_failed += result.failed
            all_errors.extend(result.errors)
        except Exception as e:
            total_failed += 1
            all_errors.append(f"EXCEPTION in {test_fn.__name__}: {e}")
    
    print()
    print("=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    
    if all_errors:
        for error in all_errors:
            print(error)
        print()
    
    print(f"PASS: {total_passed}/{total_passed + total_failed} passed")
    
    if total_failed > 0:
        print(f"✗ {total_failed} test(s) failed")
        sys.exit(1)
    else:
        print("✓ All DB allowlist env mismatch tests passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
