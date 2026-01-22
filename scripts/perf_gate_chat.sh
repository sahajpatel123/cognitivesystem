#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${BASE:-}" ]]; then
  echo "ERROR: BASE env var is required (e.g., https://your-staging.railway.app)" >&2
  exit 1
fi

COOKIE_JAR="/tmp/cookies_perf_gate.txt"
rm -f "$COOKIE_JAR"

run() {
  desc="$1"; shift
  echo "---- $desc"
  "$@" || true
  echo
}

run "Health" curl -i -s "$BASE/health"
run "DB health" curl -i -s "$BASE/db/health"
run "Identity (anon cookie)" curl -i -s -c "$COOKIE_JAR" "$BASE/auth/whoami"
run "Chat happy (hi)" curl -i -s -b "$COOKIE_JAR" -H "Content-Type: application/json" -d '{"user_text":"hi"}' "$BASE/api/chat"

echo "---- Burst (15x hi) expect 200/429, no 500"
for i in {1..15}; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -b "$COOKIE_JAR" -H "Content-Type: application/json" -d '{"user_text":"hi"}' "$BASE/api/chat")
  echo "$i: $code"
done

echo "Done. Inspect status codes above. Payload limited to 'hi'; temp cookies at $COOKIE_JAR"
