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
chat_success=0
last_curl_exit=0
last_size=0

for attempt in $(seq 1 $ATTEMPTS); do
  > "$headers_file"
  set +e
  curl --http1.1 -sS --connect-timeout 8 --max-time 20 \
       -H "Content-Type: application/json" \
       -H "Accept-Encoding: identity" \
       -H "Connection: close" \
       -D "$headers_file" -o /dev/null \
       -d '{"user_text":"hi"}' "$BASE/api/chat" 2>/dev/null
  curl_exit=$?
  set -e
  
  file_size=$(wc -c < "$headers_file" | tr -d ' ')
  has_http=0
  has_reqid=0
  if grep -qi "^HTTP/" "$headers_file" 2>/dev/null; then has_http=1; fi
  if grep -qi "^X-Request-Id:" "$headers_file" 2>/dev/null; then has_reqid=1; fi
  
  echo "  attempt $attempt/$ATTEMPTS: curl_exit=$curl_exit size=${file_size}b has_http=$has_http has_reqid=$has_reqid"
  
  last_curl_exit=$curl_exit
  last_size=$file_size
  
  # Accept exit 0 or exit 18 (partial transfer) if headers are complete
  if [[ ($curl_exit -eq 0 || $curl_exit -eq 18) && $file_size -ge 20 && $has_http -eq 1 && $has_reqid -eq 1 ]]; then
    tr -d '\r' < "$headers_file" > "${headers_file}.nocr"
    mv "${headers_file}.nocr" "$headers_file"
    chat_success=1
    break
  fi
  
  [[ $attempt -lt $ATTEMPTS ]] && sleep 1
done

if [[ $chat_success -eq 0 ]]; then
  echo "ERROR: could not capture /api/chat headers after $ATTEMPTS attempts; last_curl_exit=$last_curl_exit; last_size=${last_size}b" >&2
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
whoami_success=0
last_curl_exit=0
last_size=0

for attempt in $(seq 1 $ATTEMPTS); do
  > "$whoami_headers"
  set +e
  curl --http1.1 -sS --connect-timeout 8 --max-time 20 \
       -H "Accept-Encoding: identity" \
       -H "Connection: close" \
       -D "$whoami_headers" -o /dev/null \
       "$BASE/auth/whoami" 2>/dev/null
  curl_exit=$?
  set -e
  
  file_size=$(wc -c < "$whoami_headers" | tr -d ' ')
  has_http=0
  has_cookie=0
  if grep -qi "^HTTP/" "$whoami_headers" 2>/dev/null; then has_http=1; fi
  if grep -qi "^Set-Cookie:" "$whoami_headers" 2>/dev/null; then has_cookie=1; fi
  
  echo "  attempt $attempt/$ATTEMPTS: curl_exit=$curl_exit size=${file_size}b has_http=$has_http has_cookie=$has_cookie"
  
  last_curl_exit=$curl_exit
  last_size=$file_size
  
  # Accept exit 0 or exit 18 (partial transfer) if headers are complete
  if [[ ($curl_exit -eq 0 || $curl_exit -eq 18) && $file_size -ge 20 && $has_http -eq 1 && $has_cookie -eq 1 ]]; then
    tr -d '\r' < "$whoami_headers" > "${whoami_headers}.nocr"
    mv "${whoami_headers}.nocr" "$whoami_headers"
    whoami_success=1
    break
  fi
  
  [[ $attempt -lt $ATTEMPTS ]] && sleep 1
done

if [[ $whoami_success -eq 0 ]]; then
  echo "ERROR: could not capture /auth/whoami headers after $ATTEMPTS attempts; last_curl_exit=$last_curl_exit; last_size=${last_size}b" >&2
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
