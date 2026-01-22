#!/usr/bin/env bash
set -euo pipefail

# Optional breaker drill. This script does NOT alter remote env; it only drives requests.
# To meaningfully trip the breaker, deploy with intentionally failing provider settings
# or point BASE to an instance with MODEL_PROVIDER set but unavailable.

if [[ -z "${BASE:-}" ]]; then
  echo "ERROR: BASE env var is required (e.g., https://your-staging.railway.app)" >&2
  exit 1
fi

ATTEMPTS="${ATTEMPTS:-8}"
COOKIE_JAR="/tmp/cost_breaker_cookies.txt"
RESP_FILE="/tmp/cost_breaker_resp.json"
rm -f "$COOKIE_JAR" "$RESP_FILE"

echo "Breaker drill (BASE=$BASE, ATTEMPTS=$ATTEMPTS)"
echo "NOTE: This expects the backend to be misconfigured/unavailable to force downstream failures."
echo

curl -s -o /dev/null -c "$COOKIE_JAR" "$BASE/auth/whoami" || true

breaker_seen=0
for i in $(seq 1 "$ATTEMPTS"); do
  status=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -b "$COOKIE_JAR" -H "Content-Type: application/json" -d '{"user_text":"hi"}' "$BASE/api/chat")
  echo "attempt #$i status=$status"
  if grep -q '"failure_type"\s*:\s*"PROVIDER_UNAVAILABLE"' "$RESP_FILE"; then
    breaker_seen=1
  fi
done

echo "Breaker open observed: $breaker_seen"
if [[ "$breaker_seen" == "1" ]]; then
  exit 0
fi
echo "Breaker did not open. Ensure backend provider is intentionally failing for this drill." >&2
exit 2
