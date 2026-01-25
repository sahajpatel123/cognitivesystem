#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${BASE:-}" ]]; then
  echo "ERROR: BASE env var is required (e.g., https://your-staging.railway.app)" >&2
  exit 1
fi

MODE_LOWER="${MODE:-staging}"
MODE_LOWER="$(echo "$MODE_LOWER" | tr '[:upper:]' '[:lower:]')"

printf 'Security gate start (mode=%s, base=%s)\n\n' "$MODE_LOWER" "$BASE"

headers_file="/tmp/security_gate_headers.$$"
whoami_headers="/tmp/security_gate_whoami.$$"
trap 'rm -f "$headers_file" "$whoami_headers"' EXIT

# Check /api/chat returns security headers and X-Request-Id
curl -s -D "$headers_file" -o /dev/null -H "Content-Type: application/json" -d '{"user_text":"hi"}' "$BASE/api/chat" >/dev/null

required_headers=(
  "X-Request-Id"
  "X-Content-Type-Options"
  "Referrer-Policy"
  "X-Frame-Options"
  "Permissions-Policy"
)

for h in "${required_headers[@]}"; do
  if ! grep -qi "^$h:" "$headers_file"; then
    echo "ERROR: missing header $h on /api/chat" >&2
    exit 1
  fi
done

# Check anon/whoami cookie flags
curl -s -D "$whoami_headers" -o /dev/null "$BASE/auth/whoami" >/dev/null || true
if grep -qi "Set-Cookie:.*SameSite=Lax" "$whoami_headers" && grep -qi "Set-Cookie:.*HttpOnly" "$whoami_headers"; then
  echo "Cookie flags ok"
else
  echo "ERROR: whoami cookie flags missing HttpOnly or SameSite=Lax" >&2
  exit 1
fi

echo "Security gate completed successfully."
