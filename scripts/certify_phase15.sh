#!/usr/bin/env bash
set -euo pipefail

# Phase 15 certification smoke script (Step 10)
# Usage: BASE=https://cognitivesystem-production.up.railway.app ./scripts/certify_phase15.sh
# Notes:
# - Sends only the placeholder prompt "hi".
# - Does not write secrets; uses a temp cookie jar for anon cookie tests.

if [[ -z "${BASE:-}" ]]; then
  echo "ERROR: BASE env var is required (e.g., https://cognitivesystem-production.up.railway.app)" >&2
  exit 1
fi

TMP_COOKIES="$(mktemp)"
cleanup() { rm -f "$TMP_COOKIES"; }
trap cleanup EXIT

echo "Running Phase 15 certification smoke against $BASE"

run() {
  desc="$1"; shift
  echo "---- $desc"
  "$@"
  echo
}

run "Health" curl -s "$BASE/health"
run "DB health" curl -s "$BASE/db/health"
run "Identity (anon cookie)" curl -i -c "$TMP_COOKIES" "$BASE/auth/whoami"
run "Chat happy path" curl -i -b "$TMP_COOKIES" -H "Content-Type: application/json" -d '{"user_text":"hi"}' "$BASE/api/chat"
run "Chat wrong content-type (expect 415)" curl -i -H "Content-Type: text/plain" -d 'hi' "$BASE/api/chat"
run "Burst sample (expect some 429 after limits)" bash -c "for i in {1..10}; do curl -s -o /dev/null -w \"%{http_code}\n\" -X POST \"$BASE/api/chat\" -H \"Content-Type: application/json\" -d '{\"user_text\":\"hi\"}'; done"

echo "Done. Inspect status codes and responses above. No data stored beyond anon cookie."
