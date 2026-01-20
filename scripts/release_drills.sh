#!/usr/bin/env bash
set -euo pipefail

# Minimal staging drill runner (A–F). Requires curl and BASE env var.
# Usage: BASE=https://<staging-service>.up.railway.app ./scripts/release_drills.sh

if [[ -z "${BASE:-}" ]]; then
  echo "ERROR: BASE env var is required (e.g., https://<staging>.up.railway.app)" >&2
  exit 1
fi

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; }

run() {
  desc="$1"; shift
  if "$@"; then pass "$desc"; else fail "$desc"; fi
}

# Drill A: health
run "Health check" curl -sf "$BASE/health" >/dev/null
run "DB health check" curl -sf "$BASE/db/health" >/dev/null

# Drill B: identity (capture anon cookie)
run "Identity whoami" curl -sf -c /tmp/release_drills_cookies.txt "$BASE/auth/whoami" >/dev/null

# Drill C: /api/chat happy path
run "Chat happy path" curl -sf -b /tmp/release_drills_cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"user_text":"hi"}' \
  "$BASE/api/chat" >/dev/null

# Drill D: wrong content-type
run "Chat content-type rejection (expect non-2xx)" \
  bash -c "code=\$(curl -s -o /dev/null -w \"%{http_code}\" -H 'Content-Type: text/plain' -d 'hi' \"$BASE/api/chat\"); [[ \$code -eq 415 ]]"

# Drill E: invalid JSON
run "Chat invalid JSON (expect 400)" \
  bash -c "code=\$(curl -s -o /dev/null -w \"%{http_code}\" -H 'Content-Type: application/json' -d '{bad json' \"$BASE/api/chat\"); [[ \$code -eq 400 ]]"

# Drill F: missing user_text
run "Chat missing user_text (expect 400)" \
  bash -c "code=\$(curl -s -o /dev/null -w \"%{http_code}\" -H 'Content-Type: application/json' -d '{}' \"$BASE/api/chat\"); [[ \$code -eq 400 ]]"

echo "Drills A–F completed. Inspect outputs/logs manually for full verification."
