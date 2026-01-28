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

ATTEMPTS=8

# Check /api/chat returns security headers and X-Request-Id
echo "---- Checking /api/chat headers"
for attempt in $(seq 1 $ATTEMPTS); do
  rm -f "$headers_file"
  if curl --http1.1 -sS --connect-timeout 8 --max-time 20 \
       -H "Content-Type: application/json" \
       -H "Accept-Encoding: identity" \
       -H "Connection: close" \
       -D "$headers_file" -o /dev/null \
       -d '{"user_text":"hi"}' "$BASE/api/chat" 2>/dev/null; then
    if [[ -s "$headers_file" ]]; then
      tr -d '\r' < "$headers_file" > "${headers_file}.nocr"
      mv "${headers_file}.nocr" "$headers_file"
      break
    else
      echo "  attempt $attempt/$ATTEMPTS: empty headers, retrying..." >&2
    fi
  else
    echo "  attempt $attempt/$ATTEMPTS: curl failed, retrying..." >&2
  fi
  [[ $attempt -lt $ATTEMPTS ]] && sleep 1
done

if [[ ! -s "$headers_file" ]]; then
  echo "ERROR: failed to get /api/chat headers after $ATTEMPTS attempts" >&2
  exit 1
fi

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

echo "  all required headers present"

# Check anon/whoami cookie flags
echo "---- Checking /auth/whoami cookie flags"
for attempt in $(seq 1 $ATTEMPTS); do
  rm -f "$whoami_headers"
  if curl --http1.1 -sS --connect-timeout 8 --max-time 20 \
       -H "Accept-Encoding: identity" \
       -H "Connection: close" \
       -D "$whoami_headers" -o /dev/null \
       "$BASE/auth/whoami" 2>/dev/null; then
    if [[ -s "$whoami_headers" ]]; then
      tr -d '\r' < "$whoami_headers" > "${whoami_headers}.nocr"
      mv "${whoami_headers}.nocr" "$whoami_headers"
      break
    else
      echo "  attempt $attempt/$ATTEMPTS: empty headers, retrying..." >&2
    fi
  else
    echo "  attempt $attempt/$ATTEMPTS: curl failed, retrying..." >&2
  fi
  [[ $attempt -lt $ATTEMPTS ]] && sleep 1
done

if [[ ! -s "$whoami_headers" ]]; then
  echo "ERROR: failed to get /auth/whoami headers after $ATTEMPTS attempts" >&2
  exit 1
fi

if grep -qi "Set-Cookie:.*SameSite=Lax" "$whoami_headers" && grep -qi "Set-Cookie:.*HttpOnly" "$whoami_headers"; then
  echo "  cookie flags ok (HttpOnly + SameSite=Lax)"
else
  echo "ERROR: whoami cookie flags missing HttpOnly or SameSite=Lax" >&2
  exit 1
fi

echo
echo "Security gate completed successfully."
