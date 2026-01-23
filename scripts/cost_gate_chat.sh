#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${BASE:-}" ]]; then
  echo "ERROR: BASE env var is required (e.g., https://your-staging.railway.app)" >&2
  exit 1
fi

MODE="${MODE:-staging}"
EXPECT_BUDGET_BLOCK="${EXPECT_BUDGET_BLOCK:-0}" # set to 1 if budgets are intentionally tightened for this drill
BURST_COUNT="${BURST_COUNT:-8}"
COOKIE_JAR="/tmp/cost_gate_cookies.txt"
RESP_FILE="/tmp/cost_gate_resp.json"
rm -f "$COOKIE_JAR" "$RESP_FILE"

run() {
  local label="$1"; shift
  echo "---- $label"
  "$@" || true
  echo
}

parse_response() {
  local file="$1"
  python3 - "$file" <<'PY'
import json, sys
path = sys.argv[1]
try:
    with open(path, "r") as f:
        data = json.load(f)
    ft = data.get("failure_type")
    fr = data.get("failure_reason")
    action = data.get("action")
    print(f"failure_type={ft} failure_reason={fr} action={action}")
except Exception as exc:  # noqa: BLE001
    print(f"response_parse_error={exc}")
PY
}

echo "Cost gate (mode=$MODE, base=$BASE)"
echo

run "Health" curl -i -s "$BASE/health"
run "DB health" curl -i -s "$BASE/db/health"
run "Whoami (anon cookie)" curl -i -s -c "$COOKIE_JAR" "$BASE/auth/whoami"

echo "---- Chat burst ($BURST_COUNT x \"hi\")"
budget_block_seen=0
breaker_seen=0
for i in $(seq 1 "$BURST_COUNT"); do
  status=$(curl -s -o "$RESP_FILE" -w "%{http_code}" -b "$COOKIE_JAR" -H "Content-Type: application/json" -d '{"user_text":"hi"}' "$BASE/api/chat")
  echo "chat #$i status=$status"
  parse_response "$RESP_FILE"
  if grep -q '"failure_type"\s*:\s*"BUDGET_EXCEEDED"' "$RESP_FILE"; then
    budget_block_seen=1
  fi
  if grep -q '"failure_type"\s*:\s*"PROVIDER_UNAVAILABLE"' "$RESP_FILE"; then
    breaker_seen=1
  fi
done
echo

if [[ "$EXPECT_BUDGET_BLOCK" == "1" && "$budget_block_seen" != "1" ]]; then
  echo "ERROR: EXPECT_BUDGET_BLOCK=1 but no BUDGET_EXCEEDED responses observed" >&2
  exit 2
fi

echo "Budget block seen: $budget_block_seen"
echo "Breaker open seen: $breaker_seen"
echo
echo "Cost gate completed. Inspect statuses above. Set COST_* env vars in deployment to force budget hits if needed."
