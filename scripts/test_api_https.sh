#!/usr/bin/env bash
# Test script to verify HTTPS detection and /api/chat response

set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"
echo "Testing API at: $API_BASE"
echo ""

# Test 1: OPTIONS (CORS preflight)
echo "=== Test 1: OPTIONS /api/chat ==="
curl -v -X OPTIONS "$API_BASE/api/chat" \
  -H "Origin: https://example.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  2>&1 | grep -E "(< HTTP|< Access-Control|< X-)"
echo ""

# Test 2: POST with X-Forwarded-Proto (simulating Railway proxy)
echo "=== Test 2: POST /api/chat with X-Forwarded-Proto: https ==="
RESPONSE=$(curl -s -X POST "$API_BASE/api/chat" \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-Proto: https" \
  -H "X-Forwarded-Host: myapp.railway.app" \
  -H "User-Agent: Mozilla/5.0" \
  -H "Accept: application/json" \
  -d '{"user_text":"What is Bitcoin?"}')

echo "Response:"
echo "$RESPONSE" | jq '.'
echo ""

# Check if response contains real answer or fallback
if echo "$RESPONSE" | jq -e '.rendered_text' > /dev/null 2>&1; then
  RENDERED_TEXT=$(echo "$RESPONSE" | jq -r '.rendered_text')
  echo "Rendered text (first 200 chars):"
  echo "$RENDERED_TEXT" | head -c 200
  echo ""
  
  # Check for problematic fallback text
  if echo "$RENDERED_TEXT" | grep -q "limited mode"; then
    echo "❌ FAIL: Response contains 'limited mode' fallback text"
    exit 1
  elif echo "$RENDERED_TEXT" | grep -q "technical issue"; then
    echo "❌ FAIL: Response contains 'technical issue' fallback text"
    exit 1
  elif echo "$RENDERED_TEXT" | grep -q "Bitcoin"; then
    echo "✅ PASS: Response contains real answer about Bitcoin"
  else
    echo "⚠️  WARN: Response doesn't contain expected content"
  fi
else
  echo "❌ FAIL: No rendered_text in response"
  exit 1
fi

echo ""
echo "=== Test 3: POST without X-Forwarded-Proto (direct http) ==="
RESPONSE2=$(curl -s -X POST "$API_BASE/api/chat" \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0" \
  -H "Accept: application/json" \
  -d '{"user_text":"What is Ethereum?"}')

echo "Response:"
echo "$RESPONSE2" | jq '.'
echo ""

echo "✅ All tests completed"
