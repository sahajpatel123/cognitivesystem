#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${BASE:-}" ]]; then
  echo "ERROR: BASE env var is required (e.g., https://your-staging.railway.app)" >&2
  exit 1
fi

call_chat() {
  local desc="$1"
  shift
  echo "---- $desc"
  local resp
  resp="$(env "$@" curl -s -i -H "Content-Type: application/json" -d '{"user_text":"hi"}' "$BASE/api/chat")"
  echo "$resp"
  echo "$resp" | grep -E "$2" >/dev/null || exit 1
  echo
}

# Breaker forced open
call_chat "FORCE_BREAKER_OPEN=1" "PROVIDER_UNAVAILABLE|503" FORCE_BREAKER_OPEN=1

# Budget forced block
call_chat "FORCE_BUDGET_BLOCK=1" "BUDGET_EXCEEDED|429" FORCE_BUDGET_BLOCK=1

# Provider timeout forced
call_chat "FORCE_PROVIDER_TIMEOUT=1" "TIMEOUT" FORCE_PROVIDER_TIMEOUT=1

# Quality forced fail
call_chat "FORCE_QUALITY_FAIL=1" "ASK_CLARIFY" FORCE_QUALITY_FAIL=1

# Safety forced block
call_chat "FORCE_SAFETY_BLOCK=1" "SAFETY_BLOCK" FORCE_SAFETY_BLOCK=1

echo "Chaos gate completed. Inspect outputs above."
