#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

log() {
  echo "[eval_gate] $1"
}

log "compileall backend mci_backend"
python3 -m compileall backend mci_backend

log "import backend.app.main"
python3 -c "import backend.app.main; print('OK backend.app.main import')"

log "pytest step6 offline suite"
pytest -q backend/tests/test_step6_observability_contract.py backend/tests/test_step6_eval_gate_scenarios.py

log "PASS"
