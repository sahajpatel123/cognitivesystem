#!/usr/bin/env python3
"""
Phase 20: DB Allowlist Production Tests

Self-contained tests (no pytest) for DB_HOST_ALLOWLIST_PROD enforcement.
Tests the diagnostics module and guards.py parsing/matching logic.

Run: PYTHONPATH=. python3 backend/tests/test_phase20_db_allowlist_prod.py
"""

from __future__ import annotations

import json
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


def test_host_allowed_host_only():
    """Test 1: Host allowed (allowlist host only)."""
    print("Test 1: Host allowed (allowlist host only)")
    result = TestResult()
    
    from backend.app.config.diagnostics import db_allowlist_diagnostics
    
    diag = db_allowlist_diagnostics(
        database_url="postgresql://user:pass@aws-1-ap-south-1.pooler.supabase.com:6543/postgres",
        app_env="production",
        allowlist_csv="aws-1-ap-south-1.pooler.supabase.com",
    )
    
    result.assert_equal(diag["decision"], "ALLOW", "decision should be ALLOW")
    result.assert_equal(diag["reason_code"], "ALLOWED", "reason_code should be ALLOWED")
    result.assert_equal(diag["db_host"], "aws-1-ap-south-1.pooler.supabase.com", "db_host extracted")
    result.assert_equal(diag["db_port"], 6543, "db_port extracted")
    result.assert_equal(diag["allowlist_count"], 1, "allowlist_count")
    
    return result


def test_host_allowed_whitespace_casing():
    """Test 2: Host allowed with whitespace + casing."""
    print("Test 2: Host allowed with whitespace + casing")
    result = TestResult()
    
    from backend.app.config.diagnostics import db_allowlist_diagnostics
    
    diag = db_allowlist_diagnostics(
        database_url="postgresql://user:pass@aws-1-ap-south-1.pooler.supabase.com:6543/postgres",
        app_env="production",
        allowlist_csv="  AWS-1-AP-SOUTH-1.POOLER.SUPABASE.COM  ",
    )
    
    result.assert_equal(diag["decision"], "ALLOW", "decision should be ALLOW with whitespace/casing")
    result.assert_equal(diag["reason_code"], "ALLOWED", "reason_code should be ALLOWED")
    
    return result


def test_host_port_allowed():
    """Test 3: Host:port allowed."""
    print("Test 3: Host:port allowed")
    result = TestResult()
    
    from backend.app.config.diagnostics import db_allowlist_diagnostics
    
    diag = db_allowlist_diagnostics(
        database_url="postgresql://user:pass@aws-1-ap-south-1.pooler.supabase.com:6543/postgres",
        app_env="production",
        allowlist_csv="aws-1-ap-south-1.pooler.supabase.com:6543",
    )
    
    result.assert_equal(diag["decision"], "ALLOW", "decision should be ALLOW with matching port")
    result.assert_equal(diag["reason_code"], "ALLOWED", "reason_code should be ALLOWED")
    
    return result


def test_host_port_mismatch():
    """Test 4: Host:port mismatch."""
    print("Test 4: Host:port mismatch")
    result = TestResult()
    
    from backend.app.config.diagnostics import db_allowlist_diagnostics
    
    diag = db_allowlist_diagnostics(
        database_url="postgresql://user:pass@aws-1-ap-south-1.pooler.supabase.com:6543/postgres",
        app_env="production",
        allowlist_csv="aws-1-ap-south-1.pooler.supabase.com:5432",
    )
    
    result.assert_equal(diag["decision"], "DENY", "decision should be DENY with port mismatch")
    result.assert_equal(diag["reason_code"], "HOST_NOT_ALLOWED", "reason_code should be HOST_NOT_ALLOWED")
    
    return result


def test_missing_allowlist_production():
    """Test 5: Missing allowlist in production."""
    print("Test 5: Missing allowlist in production")
    result = TestResult()
    
    from backend.app.config.diagnostics import db_allowlist_diagnostics
    
    # Test with None
    diag = db_allowlist_diagnostics(
        database_url="postgresql://user:pass@aws-1-ap-south-1.pooler.supabase.com:6543/postgres",
        app_env="production",
        allowlist_csv=None,
    )
    
    result.assert_equal(diag["decision"], "DENY", "decision should be DENY with None allowlist")
    result.assert_equal(diag["reason_code"], "MISSING_ALLOWLIST", "reason_code should be MISSING_ALLOWLIST")
    
    # Test with empty string
    diag2 = db_allowlist_diagnostics(
        database_url="postgresql://user:pass@aws-1-ap-south-1.pooler.supabase.com:6543/postgres",
        app_env="production",
        allowlist_csv="",
    )
    
    result.assert_equal(diag2["decision"], "DENY", "decision should be DENY with empty allowlist")
    result.assert_equal(diag2["reason_code"], "MISSING_ALLOWLIST", "reason_code should be MISSING_ALLOWLIST")
    
    return result


def test_missing_database_url_production():
    """Test 6: Missing database_url in production."""
    print("Test 6: Missing database_url in production")
    result = TestResult()
    
    from backend.app.config.diagnostics import db_allowlist_diagnostics
    
    # Test with None
    diag = db_allowlist_diagnostics(
        database_url=None,
        app_env="production",
        allowlist_csv="aws-1-ap-south-1.pooler.supabase.com",
    )
    
    result.assert_equal(diag["decision"], "DENY", "decision should be DENY with None database_url")
    result.assert_equal(diag["reason_code"], "MISSING_DATABASE_URL", "reason_code should be MISSING_DATABASE_URL")
    
    # Test with empty string
    diag2 = db_allowlist_diagnostics(
        database_url="",
        app_env="production",
        allowlist_csv="aws-1-ap-south-1.pooler.supabase.com",
    )
    
    result.assert_equal(diag2["decision"], "DENY", "decision should be DENY with empty database_url")
    result.assert_equal(diag2["reason_code"], "MISSING_DATABASE_URL", "reason_code should be MISSING_DATABASE_URL")
    
    return result


def test_invalid_allowlist_entry():
    """Test 7: Invalid allowlist entry => fail-closed."""
    print("Test 7: Invalid allowlist entry => fail-closed")
    result = TestResult()
    
    from backend.app.config.diagnostics import db_allowlist_diagnostics
    
    # Invalid port (not a number)
    diag = db_allowlist_diagnostics(
        database_url="postgresql://user:pass@aws-1-ap-south-1.pooler.supabase.com:6543/postgres",
        app_env="production",
        allowlist_csv="aws-1-ap-south-1.pooler.supabase.com:NOTAPORT",
    )
    
    result.assert_equal(diag["decision"], "DENY", "decision should be DENY with invalid port")
    result.assert_equal(diag["reason_code"], "INVALID_ALLOWLIST_ENTRY", "reason_code should be INVALID_ALLOWLIST_ENTRY")
    
    # Invalid port (out of range)
    diag2 = db_allowlist_diagnostics(
        database_url="postgresql://user:pass@aws-1-ap-south-1.pooler.supabase.com:6543/postgres",
        app_env="production",
        allowlist_csv="aws-1-ap-south-1.pooler.supabase.com:99999",
    )
    
    result.assert_equal(diag2["decision"], "DENY", "decision should be DENY with port out of range")
    result.assert_equal(diag2["reason_code"], "INVALID_ALLOWLIST_ENTRY", "reason_code should be INVALID_ALLOWLIST_ENTRY")
    
    return result


def test_no_sentinel_leakage():
    """Test 8: No leakage sentinel - sensitive strings must not appear in diagnostics."""
    print("Test 8: No leakage sentinel")
    result = TestResult()
    
    from backend.app.config.diagnostics import db_allowlist_diagnostics
    
    sentinel = "SENSITIVE_USER_TEXT_123"
    secret_sentinel = "SECRET_PASSWORD_456"
    private_sentinel = "PRIVATE_KEY_789"
    
    # Put sentinels in database_url
    diag1 = db_allowlist_diagnostics(
        database_url=f"postgresql://{sentinel}:{secret_sentinel}@{private_sentinel}.supabase.com:6543/postgres",
        app_env="production",
        allowlist_csv="allowed.host.com",
    )
    
    json_output1 = json.dumps(diag1)
    result.assert_true(sentinel not in json_output1, f"sentinel {sentinel} should not appear in diagnostics")
    result.assert_true(secret_sentinel not in json_output1, f"sentinel {secret_sentinel} should not appear in diagnostics")
    # Note: private_sentinel is in hostname which IS returned, but lowercased
    # The actual hostname extraction should lowercase it
    result.assert_true(private_sentinel not in json_output1, f"sentinel {private_sentinel} should not appear in diagnostics (case-sensitive)")
    
    # Put sentinels in allowlist
    diag2 = db_allowlist_diagnostics(
        database_url="postgresql://user:pass@aws-1-ap-south-1.pooler.supabase.com:6543/postgres",
        app_env="production",
        allowlist_csv=f"{sentinel},{secret_sentinel},{private_sentinel}",
    )
    
    json_output2 = json.dumps(diag2)
    result.assert_true(sentinel not in json_output2, f"sentinel {sentinel} should not appear in allowlist diagnostics")
    result.assert_true(secret_sentinel not in json_output2, f"sentinel {secret_sentinel} should not appear in allowlist diagnostics")
    result.assert_true(private_sentinel not in json_output2, f"sentinel {private_sentinel} should not appear in allowlist diagnostics")
    
    # Verify only hashes are returned for allowlist entries
    result.assert_true("allowlist_first2_hashes" in diag2, "should have allowlist_first2_hashes")
    result.assert_true(isinstance(diag2["allowlist_first2_hashes"], list), "allowlist_first2_hashes should be list")
    
    return result


def test_guards_host_matching():
    """Test guards.py _host_matches function directly."""
    print("Test 9: Guards _host_matches function")
    result = TestResult()
    
    from backend.app.config.guards import _host_matches, _parse_and_validate_allowlist
    
    # Parse allowlist
    allowlist_raw = ["aws-1-ap-south-1.pooler.supabase.com", "other.host.com:5432"]
    parsed, valid = _parse_and_validate_allowlist(allowlist_raw)
    result.assert_true(valid, "allowlist should be valid")
    result.assert_equal(len(parsed), 2, "should have 2 entries")
    
    # Test host-only match (port ignored)
    result.assert_true(
        _host_matches("aws-1-ap-south-1.pooler.supabase.com", 6543, parsed),
        "host-only entry should match regardless of port"
    )
    result.assert_true(
        _host_matches("aws-1-ap-south-1.pooler.supabase.com", 5432, parsed),
        "host-only entry should match with different port"
    )
    result.assert_true(
        _host_matches("aws-1-ap-south-1.pooler.supabase.com", None, parsed),
        "host-only entry should match with no port"
    )
    
    # Test host:port match (must match both)
    result.assert_true(
        _host_matches("other.host.com", 5432, parsed),
        "host:port entry should match with correct port"
    )
    result.assert_true(
        not _host_matches("other.host.com", 6543, parsed),
        "host:port entry should NOT match with wrong port"
    )
    result.assert_true(
        not _host_matches("other.host.com", None, parsed),
        "host:port entry should NOT match with no port"
    )
    
    # Test no match
    result.assert_true(
        not _host_matches("unknown.host.com", 5432, parsed),
        "unknown host should not match"
    )
    
    return result


def test_guards_extract_db_host_port():
    """Test guards.py _extract_db_host_port function."""
    print("Test 10: Guards _extract_db_host_port function")
    result = TestResult()
    
    from backend.app.config.guards import _extract_db_host_port
    
    # Standard Supabase URL
    host, port = _extract_db_host_port(
        "postgresql://postgres.user:password@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"
    )
    result.assert_equal(host, "aws-1-ap-south-1.pooler.supabase.com", "should extract hostname")
    result.assert_equal(port, 6543, "should extract port")
    
    # URL without port
    host2, port2 = _extract_db_host_port(
        "postgresql://user:pass@db.example.com/mydb"
    )
    result.assert_equal(host2, "db.example.com", "should extract hostname without port")
    result.assert_equal(port2, None, "port should be None when not specified")
    
    # Empty/None
    host3, port3 = _extract_db_host_port(None)
    result.assert_equal(host3, None, "None input should return None host")
    result.assert_equal(port3, None, "None input should return None port")
    
    host4, port4 = _extract_db_host_port("")
    result.assert_equal(host4, None, "empty input should return None host")
    result.assert_equal(port4, None, "empty input should return None port")
    
    # Uppercase should be lowercased
    host5, port5 = _extract_db_host_port(
        "postgresql://user:pass@AWS-1-AP-SOUTH-1.POOLER.SUPABASE.COM:6543/postgres"
    )
    result.assert_equal(host5, "aws-1-ap-south-1.pooler.supabase.com", "hostname should be lowercased")
    
    return result


def test_multiple_allowlist_entries():
    """Test multiple allowlist entries with mixed host and host:port."""
    print("Test 11: Multiple allowlist entries")
    result = TestResult()
    
    from backend.app.config.diagnostics import db_allowlist_diagnostics
    
    # First entry is host-only, second is host:port
    diag = db_allowlist_diagnostics(
        database_url="postgresql://user:pass@aws-1-ap-south-1.pooler.supabase.com:6543/postgres",
        app_env="production",
        allowlist_csv="other.host.com, aws-1-ap-south-1.pooler.supabase.com:6543",
    )
    
    result.assert_equal(diag["decision"], "ALLOW", "should match second entry with port")
    result.assert_equal(diag["allowlist_count"], 2, "should have 2 entries")
    
    # Match first entry (host-only)
    diag2 = db_allowlist_diagnostics(
        database_url="postgresql://user:pass@other.host.com:5432/postgres",
        app_env="production",
        allowlist_csv="other.host.com, aws-1-ap-south-1.pooler.supabase.com:6543",
    )
    
    result.assert_equal(diag2["decision"], "ALLOW", "should match first entry (host-only)")
    
    return result


def main():
    """Run all tests and report results."""
    print("=" * 60)
    print("PHASE 20: DB ALLOWLIST PRODUCTION TESTS")
    print("=" * 60)
    
    tests = [
        test_host_allowed_host_only,
        test_host_allowed_whitespace_casing,
        test_host_port_allowed,
        test_host_port_mismatch,
        test_missing_allowlist_production,
        test_missing_database_url_production,
        test_invalid_allowlist_entry,
        test_no_sentinel_leakage,
        test_guards_host_matching,
        test_guards_extract_db_host_port,
        test_multiple_allowlist_entries,
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
        print("✓ All DB allowlist production tests passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
