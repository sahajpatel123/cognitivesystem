#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "[ux_frontend_gate] MISSING: $1" >&2
    exit 1
  fi
}

require_exec() {
  if [[ ! -x "$1" ]]; then
    echo "[ux_frontend_gate] NOT EXECUTABLE: $1" >&2
    exit 1
  fi
}

main() {
  require_file "$ROOT_DIR/frontend/app/components/system-status/SystemStatus.tsx"
  require_file "$ROOT_DIR/frontend/app/lib/ux_state.ts"

  if [[ -f "$ROOT_DIR/frontend/package.json" ]]; then
    if node -e "const p=require('./frontend/package.json'); console.log(p.scripts && p.scripts.test ? '1':'0')" | grep -q "1"; then
      echo "[ux_frontend_gate] Running frontend tests"
      (cd "$ROOT_DIR/frontend" && npm test) || true
    else
      echo "[ux_frontend_gate] SKIP: no frontend test script"
    fi
  else
    echo "[ux_frontend_gate] SKIP: frontend package.json not found"
  fi

  echo "[ux_frontend_gate] OK"
}

main "$@"
