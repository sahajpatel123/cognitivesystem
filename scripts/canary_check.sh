#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-https://cognitivesystem-staging.up.railway.app}"
MODE="${MODE:-staging}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMPDIR="${TMPDIR:-/tmp}"

info() { echo "[canary_check] $*"; }
fail() { echo "[canary_check][FAIL] $*" >&2; exit 1; }

info "mode=${MODE} base=${BASE}"

health_status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/health") || fail "health request failed"
if [[ "$health_status" != "200" ]]; then
  fail "health returned $health_status"
fi
info "health ok"

resp_headers="$(mktemp "${TMPDIR%/}/canary_headers.XXXX")"
trap 'rm -f "$resp_headers"' EXIT

chat_status=$(curl -s -D "$resp_headers" -o /dev/null -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -X POST \
  --data '{"user_text":"hi"}' \
  "$BASE/api/chat") || fail "chat request failed"
if [[ "$chat_status" != "200" ]]; then
  fail "chat returned $chat_status"
fi

norm_headers=$(tr -d '\r' < "$resp_headers")

get_header() {
  local key="$1"
  echo "$norm_headers" | grep -i "^$key:" | head -n1 | cut -d':' -f2-
}

req_id=$(get_header "x-request-id" | xargs || true)
ux_state=$(get_header "x-ux-state" | xargs || true)
canary_val=$(get_header "x-canary" | xargs || true)
build_version=$(get_header "x-build-version" | xargs || true)

[[ -n "$req_id" ]] || fail "missing x-request-id"
[[ -n "$ux_state" ]] || fail "missing x-ux-state"
if [[ "$canary_val" != "0" && "$canary_val" != "1" ]]; then
  fail "x-canary missing or invalid: '$canary_val'"
fi
[[ -n "$build_version" ]] || fail "missing x-build-version"

info "headers ok: request_id=$req_id canary=$canary_val build_version=$build_version ux_state=$ux_state"

info "determinism check: backend does not support request id override; SKIP"

info "canary_check PASSED"
