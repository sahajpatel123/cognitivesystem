#!/usr/bin/env python3
"""
HTTP Content-Length Guard Test

Tests that the StripContentLengthMiddleware correctly removes Content-Length headers
from streaming responses to prevent "Response content longer than Content-Length" errors.
"""

import asyncio
import json
from typing import Dict, List, Tuple, Any

from starlette.applications import Starlette
from starlette.responses import StreamingResponse, JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from backend.app.middleware.strip_content_length import StripContentLengthMiddleware


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
    
    def assert_not_in(self, item, container, message: str):
        self.assert_true(item not in container, f"{message} (found {item} in {container})")


def create_test_streaming_response():
    """Create a streaming response that yields multiple chunks."""
    def generate():
        yield "chunk1\n"
        yield "chunk2\n" 
        yield "chunk3\n"
    
    return StreamingResponse(generate(), media_type="text/plain")


def create_test_json_response():
    """Create a regular JSON response."""
    return JSONResponse({"message": "test"})


async def streaming_endpoint(request):
    """Test endpoint that returns a streaming response."""
    return create_test_streaming_response()


async def json_endpoint(request):
    """Test endpoint that returns a JSON response."""
    return create_test_json_response()


def test_middleware_strips_content_length():
    """Test that middleware removes Content-Length headers from responses."""
    result = TestResult()
    
    # Create test app with middleware
    routes = [
        Route("/stream", streaming_endpoint),
        Route("/json", json_endpoint),
    ]
    
    app = Starlette(routes=routes)
    app.add_middleware(StripContentLengthMiddleware)
    
    client = TestClient(app)
    
    # Test 1: Streaming response should not have Content-Length
    print("Testing streaming response...")
    response = client.get("/stream")
    result.assert_equal(response.status_code, 200, "Streaming response should succeed")
    
    # Check that Content-Length header is not present
    headers_lower = {k.lower(): v for k, v in response.headers.items()}
    result.assert_not_in("content-length", headers_lower, "Streaming response should not have Content-Length header")
    
    # Verify content is correct
    expected_content = "chunk1\nchunk2\nchunk3\n"
    result.assert_equal(response.text, expected_content, "Streaming response content should be correct")
    
    # Test 2: JSON response should also not have Content-Length (middleware strips all)
    print("Testing JSON response...")
    response = client.get("/json")
    result.assert_equal(response.status_code, 200, "JSON response should succeed")
    
    # Check that Content-Length header is not present
    headers_lower = {k.lower(): v for k, v in response.headers.items()}
    result.assert_not_in("content-length", headers_lower, "JSON response should not have Content-Length header after middleware")
    
    # Verify JSON content is correct
    result.assert_equal(response.json(), {"message": "test"}, "JSON response content should be correct")
    
    return result


def test_middleware_preserves_other_headers():
    """Test that middleware preserves non-Content-Length headers."""
    result = TestResult()
    
    async def custom_endpoint(request):
        response = JSONResponse({"test": "data"})
        response.headers["X-Custom-Header"] = "custom-value"
        response.headers["Cache-Control"] = "no-cache"
        return response
    
    routes = [Route("/custom", custom_endpoint)]
    app = Starlette(routes=routes)
    app.add_middleware(StripContentLengthMiddleware)
    
    client = TestClient(app)
    
    print("Testing header preservation...")
    response = client.get("/custom")
    result.assert_equal(response.status_code, 200, "Custom response should succeed")
    
    # Check that custom headers are preserved
    result.assert_equal(response.headers.get("X-Custom-Header"), "custom-value", "Custom header should be preserved")
    result.assert_equal(response.headers.get("Cache-Control"), "no-cache", "Cache-Control header should be preserved")
    
    # Verify Content-Length is still stripped
    headers_lower = {k.lower(): v for k, v in response.headers.items()}
    result.assert_not_in("content-length", headers_lower, "Content-Length should still be stripped")
    
    return result


def test_middleware_with_non_http_scope():
    """Test that middleware passes through non-HTTP requests unchanged."""
    result = TestResult()
    
    # Create a minimal ASGI app that tracks calls
    call_log = []
    
    async def test_app(scope, receive, send):
        call_log.append(scope["type"])
        if scope["type"] == "websocket":
            # Simple websocket-like response
            await send({"type": "websocket.accept"})
        
    middleware = StripContentLengthMiddleware(test_app)
    
    # Simulate a websocket scope
    async def run_test():
        scope = {"type": "websocket", "path": "/ws"}
        
        async def receive():
            return {"type": "websocket.connect"}
        
        messages = []
        async def send(message):
            messages.append(message)
        
        await middleware(scope, receive, send)
        return messages
    
    print("Testing non-HTTP scope handling...")
    messages = asyncio.run(run_test())
    
    result.assert_equal(len(call_log), 1, "App should be called once")
    result.assert_equal(call_log[0], "websocket", "Websocket scope should be passed through")
    result.assert_equal(len(messages), 1, "Websocket message should be passed through")
    result.assert_equal(messages[0]["type"], "websocket.accept", "Websocket accept should be passed through")
    
    return result


def main():
    """Main test runner."""
    print("=" * 60)
    print("HTTP Content-Length Guard Tests")
    print("=" * 60)
    
    total_result = TestResult()
    
    # Run all tests
    tests = [
        test_middleware_strips_content_length,
        test_middleware_preserves_other_headers,
        test_middleware_with_non_http_scope,
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
        print("✓ StripContentLengthMiddleware working correctly")
        return 0
    else:
        print(f"FAIL: {total_result.passed}/{total_tests} passed")
        print()
        print("ERRORS:")
        for error in total_result.errors:
            print(f"  {error}")
        return 1


if __name__ == "__main__":
    exit(main())
