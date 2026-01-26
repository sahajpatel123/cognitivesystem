#!/usr/bin/env bash
set -euo pipefail

BASE_DEFAULT="http://localhost:8000"
BASE="${BASE:-$BASE_DEFAULT}"

fail() {
  echo "[ux_gate] ERROR: $*" >&2
  exit 1
}

post_chat_ok() {
  local resp
  resp=$(curl -s -D - -o /dev/null -H "Content-Type: application/json" -d '{"user_text":"hi"}' "$BASE/api/chat")
  echo "$resp" | grep -q "HTTP/" || fail "no HTTP status on /api/chat"
  echo "$resp" | grep -q " 200 " || fail "/api/chat did not return 200"
  echo "$resp" | grep -qi "^X-UX-State:" || fail "X-UX-State missing on success"
  echo "$resp" | grep -qi "^X-Request-Id:" || fail "X-Request-Id missing on success"
}

post_chat_415() {
  local resp
  resp=$(curl -s -D - -o /dev/null -H "Content-Type: text/plain" -d 'hi' "$BASE/api/chat")
  echo "$resp" | grep -q "HTTP/" || fail "no HTTP status on 415 check"
  echo "$resp" | grep -q " 415 " || fail "expected 415 for wrong content-type"
  echo "$resp" | grep -qi "^X-UX-State:" || fail "X-UX-State missing on 415"
}

main() {
  echo "[ux_gate] base=$BASE"
  post_chat_ok
  post_chat_415
  echo "[ux_gate] PASS"
}

main "$@"
