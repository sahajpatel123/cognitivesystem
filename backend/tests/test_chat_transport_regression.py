#!/usr/bin/env python3
"""
Chat Transport Regression Tests

Tests CORS, credentials, request-id, and content-length handling for /api/chat.
No pytest dependency; self-contained runner style.
"""

import sys
from typing import Dict, Any, List


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
    
    def assert_false(self, condition: bool, message: str):
        self.assert_true(not condition, message)
    
    def assert_equal(self, actual, expected, message: str):
        self.assert_true(actual == expected, f"{message} (got {actual!r}, expected {expected!r})")
    
    def assert_in(self, item, container, message: str):
        self.assert_true(item in container, f"{message} ({item!r} not in container)")
    
    def assert_not_in(self, item, container, message: str):
        self.assert_true(item not in container, f"{message} (found {item!r} in container)")


def test_cors_preflight():
    """Test CORS preflight (OPTIONS) returns correct headers."""
    result = TestResult()
    
    try:
        from starlette.testclient import TestClient
        from backend.app.main import app
        
        client = TestClient(app, raise_server_exceptions=False)
        
        print("Testing CORS preflight...")
        
        # Simulate preflight from a frontend origin
        test_origin = "http://localhost:3000"
        response = client.options(
            "/api/chat",
            headers={
                "Origin": test_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            }
        )
        
        # Should get 200 for preflight
        result.assert_true(
            response.status_code in [200, 204],
            f"Preflight should return 200 or 204 (got {response.status_code})"
        )
        
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        
        # Check Access-Control-Allow-Origin
        acao = headers_lower.get("access-control-allow-origin", "")
        result.assert_true(
            acao == test_origin or acao == "*",
            f"Access-Control-Allow-Origin should match origin (got {acao})"
        )
        
        # Check Access-Control-Allow-Credentials
        acac = headers_lower.get("access-control-allow-credentials", "")
        result.assert_equal(acac.lower(), "true", "Access-Control-Allow-Credentials should be true")
        
        # Note: Access-Control-Expose-Headers is returned on actual responses, not preflight
        # We verify X-Request-ID is exposed in test_chat_post_headers instead
        
    except ImportError as e:
        result.assert_true(False, f"Import error: {e}")
    except Exception as e:
        result.assert_true(False, f"Unexpected error: {e}")
    
    return result


def test_chat_post_headers():
    """Test POST /api/chat returns correct headers."""
    result = TestResult()
    
    try:
        from starlette.testclient import TestClient
        from backend.app.main import app
        
        client = TestClient(app, raise_server_exceptions=False)
        
        print("Testing POST /api/chat headers...")
        
        test_origin = "http://localhost:3000"
        response = client.post(
            "/api/chat",
            json={"user_text": "SENSITIVE_USER_TEXT_123"},
            headers={
                "Content-Type": "application/json",
                "Origin": test_origin,
            }
        )
        
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        
        # X-Request-ID must be present
        result.assert_in("x-request-id", headers_lower, "X-Request-ID header must be present")
        
        # X-Request-ID should be UUID-like
        rid = headers_lower.get("x-request-id", "")
        result.assert_true(len(rid) >= 32, f"X-Request-ID should be UUID-like (got {rid})")
        
        # Content-Length must NOT be present (stripped by middleware)
        result.assert_not_in("content-length", headers_lower, "Content-Length should be stripped")
        
        # CORS headers should be present
        acao = headers_lower.get("access-control-allow-origin", "")
        result.assert_true(
            acao == test_origin or acao == "*",
            f"Access-Control-Allow-Origin should be set (got {acao})"
        )
        
        # Access-Control-Expose-Headers should include X-Request-ID, X-UX-State, X-Cooldown-Seconds
        aceh = headers_lower.get("access-control-expose-headers", "")
        aceh_lower = aceh.lower()
        result.assert_in(
            "x-request-id",
            aceh_lower,
            "Access-Control-Expose-Headers should contain X-Request-ID"
        )
        result.assert_in(
            "x-ux-state",
            aceh_lower,
            "Access-Control-Expose-Headers should contain X-UX-State"
        )
        result.assert_in(
            "x-cooldown-seconds",
            aceh_lower,
            "Access-Control-Expose-Headers should contain X-Cooldown-Seconds"
        )
        
    except ImportError as e:
        result.assert_true(False, f"Import error: {e}")
    except Exception as e:
        result.assert_true(False, f"Unexpected error: {e}")
    
    return result


def test_chat_response_shape():
    """Test POST /api/chat returns valid JSON shape."""
    result = TestResult()
    
    try:
        from starlette.testclient import TestClient
        from backend.app.main import app
        
        client = TestClient(app, raise_server_exceptions=False)
        
        print("Testing POST /api/chat response shape...")
        
        response = client.post(
            "/api/chat",
            json={"user_text": "hello"},
            headers={"Content-Type": "application/json"}
        )
        
        # Should be valid JSON
        try:
            body = response.json()
            result.assert_true(isinstance(body, dict), "Response should be JSON object")
            
            # Either success shape or error shape
            if response.status_code == 200:
                # Success: should have action, rendered_text, ux_state
                result.assert_in("action", body, "Success response should have 'action'")
                result.assert_in("rendered_text", body, "Success response should have 'rendered_text'")
                result.assert_in("ux_state", body, "Success response should have 'ux_state'")
                # Verify action is one of the allowed values
                allowed_actions = ["ANSWER", "ASK_ONE_QUESTION", "REFUSE", "CLOSE", "FALLBACK",
                                   "ANSWER_DEGRADED", "ASK_CLARIFY", "FAIL_GRACEFULLY", "BLOCK"]
                result.assert_in(body.get("action"), allowed_actions, 
                                f"action should be valid (got {body.get('action')})")
            else:
                # Error: should have error info or ok=false
                has_error_info = "error" in body or "ok" in body or "error_code" in body
                result.assert_true(has_error_info, "Error response should have error info")
                
        except Exception as e:
            result.assert_true(False, f"Response should be valid JSON: {e}")
        
    except ImportError as e:
        result.assert_true(False, f"Import error: {e}")
    except Exception as e:
        result.assert_true(False, f"Unexpected error: {e}")
    
    return result


def test_error_response_has_request_id():
    """Test error responses include request_id."""
    result = TestResult()
    
    try:
        from starlette.testclient import TestClient
        from backend.app.main import app
        
        client = TestClient(app, raise_server_exceptions=False)
        
        print("Testing error response includes request_id...")
        
        # Send invalid content type to trigger error
        response = client.post(
            "/api/chat",
            content="not json",
            headers={"Content-Type": "text/plain"}
        )
        
        # Should be error
        result.assert_true(response.status_code >= 400, "Invalid content type should return error")
        
        # X-Request-ID header must be present
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        result.assert_in("x-request-id", headers_lower, "Error response must have X-Request-ID header")
        
    except ImportError as e:
        result.assert_true(False, f"Import error: {e}")
    except Exception as e:
        result.assert_true(False, f"Unexpected error: {e}")
    
    return result


def test_sentinel_not_leaked():
    """Test that sentinel user text never appears in response."""
    result = TestResult()
    
    try:
        from starlette.testclient import TestClient
        from backend.app.main import app
        
        client = TestClient(app, raise_server_exceptions=False)
        
        print("Testing sentinel text not leaked...")
        
        sentinel = "SENSITIVE_USER_TEXT_123"
        response = client.post(
            "/api/chat",
            json={"user_text": sentinel},
            headers={"Content-Type": "application/json"}
        )
        
        # Sentinel must NOT appear in response body
        result.assert_not_in(sentinel, response.text, "Sentinel must not appear in response body")
        
        # Sentinel must NOT appear in response headers
        all_headers = str(dict(response.headers))
        result.assert_not_in(sentinel, all_headers, "Sentinel must not appear in response headers")
        
    except ImportError as e:
        result.assert_true(False, f"Import error: {e}")
    except Exception as e:
        result.assert_true(False, f"Unexpected error: {e}")
    
    return result


def test_request_id_determinism():
    """Test that fixed X-Request-ID is preserved and response is stable."""
    result = TestResult()
    
    try:
        from starlette.testclient import TestClient
        from backend.app.main import app
        
        client = TestClient(app, raise_server_exceptions=False)
        
        print("Testing request-id determinism...")
        
        fixed_rid = "aaaa1111-bbbb-2222-cccc-333344445555"
        
        # First request
        response1 = client.post(
            "/api/chat",
            json={"user_text": "test"},
            headers={
                "Content-Type": "application/json",
                "X-Request-ID": fixed_rid,
            }
        )
        
        # Second request with same ID
        response2 = client.post(
            "/api/chat",
            json={"user_text": "test"},
            headers={
                "Content-Type": "application/json",
                "X-Request-ID": fixed_rid,
            }
        )
        
        headers1 = {k.lower(): v for k, v in response1.headers.items()}
        headers2 = {k.lower(): v for k, v in response2.headers.items()}
        
        # Both should have the same request ID (preserved from input)
        rid1 = headers1.get("x-request-id", "")
        rid2 = headers2.get("x-request-id", "")
        
        result.assert_equal(rid1, fixed_rid, "First response should preserve X-Request-ID")
        result.assert_equal(rid2, fixed_rid, "Second response should preserve X-Request-ID")
        
        # Response shapes should be consistent
        result.assert_equal(response1.status_code, response2.status_code, "Status codes should be consistent")
        
    except ImportError as e:
        result.assert_true(False, f"Import error: {e}")
    except Exception as e:
        result.assert_true(False, f"Unexpected error: {e}")
    
    return result


def test_request_id_safe_pattern():
    """Test that unsafe X-Request-ID is rejected and new one generated."""
    result = TestResult()
    
    try:
        from starlette.testclient import TestClient
        from backend.app.main import app
        
        client = TestClient(app, raise_server_exceptions=False)
        
        print("Testing request-id safe pattern validation...")
        
        # Unsafe request ID (contains non-hex characters)
        unsafe_rid = "<script>alert('xss')</script>"
        
        response = client.post(
            "/api/chat",
            json={"user_text": "test"},
            headers={
                "Content-Type": "application/json",
                "X-Request-ID": unsafe_rid,
            }
        )
        
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        rid = headers_lower.get("x-request-id", "")
        
        # Should NOT use the unsafe ID
        result.assert_true(rid != unsafe_rid, "Unsafe X-Request-ID should be rejected")
        
        # Should generate a new valid UUID
        result.assert_true(len(rid) >= 32, "Should generate new UUID for unsafe input")
        
    except ImportError as e:
        result.assert_true(False, f"Import error: {e}")
    except Exception as e:
        result.assert_true(False, f"Unexpected error: {e}")
    
    return result


def main():
    """Main test runner."""
    print("=" * 60)
    print("Chat Transport Regression Tests")
    print("=" * 60)
    
    total_result = TestResult()
    
    tests = [
        test_cors_preflight,
        test_chat_post_headers,
        test_chat_response_shape,
        test_error_response_has_request_id,
        test_sentinel_not_leaked,
        test_request_id_determinism,
        test_request_id_safe_pattern,
    ]
    
    for test_func in tests:
        try:
            result = test_func()
            total_result.passed += result.passed
            total_result.failed += result.failed
            total_result.errors.extend(result.errors)
        except Exception as e:
            total_result.failed += 1
            total_result.errors.append(f"FAIL: {test_func.__name__} raised exception: {e}")
    
    print()
    print("=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    
    total_tests = total_result.passed + total_result.failed
    if total_result.failed == 0:
        print(f"PASS: {total_tests}/{total_tests} passed")
        print("✓ Chat transport regression tests passed")
        return 0
    else:
        print(f"FAIL: {total_result.passed}/{total_tests} passed")
        print()
        print("ERRORS:")
        for error in total_result.errors:
            print(f"  {error}")
        return 1


# Curl reproduction commands (for documentation):
# 
# CORS preflight:
# curl -X OPTIONS https://YOUR_PROD_URL/api/chat \
#   -H "Origin: https://YOUR_FRONTEND_URL" \
#   -H "Access-Control-Request-Method: POST" \
#   -v 2>&1 | grep -i "access-control"
#
# POST with credentials:
# curl -X POST https://YOUR_PROD_URL/api/chat \
#   -H "Content-Type: application/json" \
#   -H "Origin: https://YOUR_FRONTEND_URL" \
#   -d '{"user_text": "hello"}' \
#   -v 2>&1 | grep -E "(< HTTP|< x-request-id|< content-length|< access-control)"


if __name__ == "__main__":
    sys.exit(main())
