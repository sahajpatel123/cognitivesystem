#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${BASE:-}" ]]; then
  echo "ERROR: BASE env var is required (e.g., https://your-staging.railway.app)" >&2
  exit 1
fi

if [[ -z "${MODE:-}" ]]; then
  echo "ERROR: MODE env var is required (staging|prod)" >&2
  exit 1
fi

MODE_LOWER="$(echo "$MODE" | tr '[:upper:]' '[:lower:]')"
if [[ "$MODE_LOWER" != "staging" && "$MODE_LOWER" != "prod" ]]; then
  echo "ERROR: MODE must be staging or prod" >&2
  exit 1
fi

echo "Promotion gate starting (mode=$MODE_LOWER, base=$BASE)"
echo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SMOKE="$SCRIPT_DIR/smoke_api_chat.sh"
DRILLS="$SCRIPT_DIR/release_drills.sh"
CERTIFY="$SCRIPT_DIR/certify_phase15.sh"

run_optional() {
  local label="$1"
  shift
  if [[ -x "$1" ]]; then
    echo "---- $label"
    "$@" || true
    echo
  else
    echo "---- $label (skipped: not present or not executable)"
    echo
  fi
}

echo "---- Smoke checks"
BASE="$BASE" bash "$SMOKE"
echo

if [[ "$MODE_LOWER" == "staging" ]]; then
  echo "---- Import gates"
  python3 -c "import backend.app.main; print('OK backend.app.main import')" 
  python3 -c "import mci_backend.main; print('OK mci_backend.main import')" 
  echo

  run_optional "Phase 15 drills (staging subset)" bash "$DRILLS"
  run_optional "Phase 15 certify subset" bash "$CERTIFY"
fi

if [[ "$MODE_LOWER" == "prod" ]]; then
  echo "Production gate is evidence-only; deployment must occur via release branch promotion (no direct deploys here)."
fi

echo "Promotion gate completed (mode=$MODE_LOWER). Review outputs above for PASS/FAIL."
