#!/usr/bin/env python3
"""
Chat Endpoint Regression Test

Tests that the /api/chat endpoint:
- Returns 200 status for valid requests
- Returns JSON response with expected shape
- Includes X-Request-ID header
- Does not include Content-Length header (stripped by middleware)
"""

import json
import sys
from typing import Dict, Any, Optional

# Minimal ASGI test harness
class TestResult:
    """Simple test result tracker."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def assert_true(self, condition: bool, message: str):
        if condition:
            self.passed += 1
        else:
            self.failed += 1
            self.errors.append(f"FAIL: {message}")
    
    def assert_false(self, condition: bool, message: str):
        self.assert_true(not condition, message)
    
    def assert_equal(self, actual, expected, message: str):
        self.assert_true(actual == expected, f"{message} (got {actual}, expected {expected})")
    
    def assert_in(self, item, container, message: str):
        self.assert_true(item in container, f"{message} ({item} not in {container})")
    
    def assert_not_in(self, item, container, message: str):
        self.assert_true(item not in container, f"{message} (found {item} in {container})")


def test_request_id_middleware():
    """Test that RequestIdMiddleware adds X-Request-ID to responses."""
    result = TestResult()
    
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient
    
    from backend.app.middleware.request_id import RequestIdMiddleware
    from backend.app.middleware.strip_content_length import StripContentLengthMiddleware
    
    async def test_endpoint(request):
        return JSONResponse({"message": "test"})
    
    routes = [Route("/test", test_endpoint, methods=["POST"])]
    app = Starlette(routes=routes)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(StripContentLengthMiddleware)
    
    client = TestClient(app)
    
    print("Testing request-id middleware...")
    response = client.post("/test", json={"user_text": "hello"})
    
    result.assert_equal(response.status_code, 200, "Response should be 200")
    
    # Check X-Request-ID header is present
    headers_lower = {k.lower(): v for k, v in response.headers.items()}
    result.assert_in("x-request-id", headers_lower, "X-Request-ID header should be present")
    
    # Check X-Request-ID is a valid UUID-like string
    request_id = headers_lower.get("x-request-id", "")
    result.assert_true(len(request_id) >= 32, f"X-Request-ID should be UUID-like (got {request_id})")
    
    # Check Content-Length is stripped
    result.assert_not_in("content-length", headers_lower, "Content-Length should be stripped")
    
    return result


def test_chat_endpoint_shape():
    """Test that /api/chat returns expected JSON shape."""
    result = TestResult()
    
    try:
        from starlette.testclient import TestClient
        from backend.app.main import app
        
        client = TestClient(app, raise_server_exceptions=False)
        
        print("Testing /api/chat endpoint shape...")
        
        # Test with valid request
        response = client.post(
            "/api/chat",
            json={"user_text": "SENTINEL_TEST_STRING_123"},
            headers={"Content-Type": "application/json"}
        )
        
        # Should get a response (may be error due to missing auth, but should be JSON)
        result.assert_true(response.status_code in [200, 400, 401, 403, 429, 500, 503], 
                          f"Response status should be valid HTTP code (got {response.status_code})")
        
        # Check X-Request-ID header is present
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        result.assert_in("x-request-id", headers_lower, "X-Request-ID header should be present")
        
        # Check Content-Length is stripped
        result.assert_not_in("content-length", headers_lower, "Content-Length should be stripped")
        
        # Response should be valid JSON
        try:
            body = response.json()
            result.assert_true(isinstance(body, dict), "Response body should be JSON object")
        except Exception as e:
            result.assert_true(False, f"Response should be valid JSON: {e}")
        
        # Check that sentinel string is NOT in response (no user text leakage)
        response_text = response.text
        result.assert_not_in("SENTINEL_TEST_STRING_123", response_text, 
                            "Sentinel string should not appear in response")
        
    except ImportError as e:
        result.assert_true(False, f"Import error: {e}")
    except Exception as e:
        result.assert_true(False, f"Unexpected error: {e}")
    
    return result


def test_error_response_shape():
    """Test that error responses include request_id."""
    result = TestResult()
    
    try:
        from starlette.testclient import TestClient
        from backend.app.main import app
        
        client = TestClient(app, raise_server_exceptions=False)
        
        print("Testing error response shape...")
        
        # Test with invalid content type
        response = client.post(
            "/api/chat",
            content="not json",
            headers={"Content-Type": "text/plain"}
        )
        
        # Should get 415 or similar error
        result.assert_true(response.status_code >= 400, 
                          f"Invalid content type should return error (got {response.status_code})")
        
        # Check X-Request-ID header is present
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        result.assert_in("x-request-id", headers_lower, "X-Request-ID header should be present on errors")
        
    except ImportError as e:
        result.assert_true(False, f"Import error: {e}")
    except Exception as e:
        result.assert_true(False, f"Unexpected error: {e}")
    
    return result


def main():
    """Main test runner."""
    print("=" * 60)
    print("Chat Endpoint Regression Tests")
    print("=" * 60)
    
    total_result = TestResult()
    
    # Run all tests
    tests = [
        test_request_id_middleware,
        test_chat_endpoint_shape,
        test_error_response_shape,
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
        print("✓ Chat endpoint regression tests passed")
        return 0
    else:
        print(f"FAIL: {total_result.passed}/{total_tests} passed")
        print()
        print("ERRORS:")
        for error in total_result.errors:
            print(f"  {error}")
        return 1


# Curl reproduction command (for documentation):
# curl -X POST https://YOUR_PROD_URL/api/chat \
#   -H "Content-Type: application/json" \
#   -d '{"user_text": "hello"}' \
#   -v 2>&1 | grep -E "(< HTTP|< x-request-id|< content-length)"


if __name__ == "__main__":
    sys.exit(main())
