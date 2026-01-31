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
  python3 -c "import backend.app.main as m; print('step6_header_ok=', hasattr(m, '_with_request_id'))"
  python3 -c "import backend.app.main as m; print('step6_chat_summary_ok=', callable(getattr(m, '_emit_chat_summary', None)))"
  python3 -c "from backend.app.security.entitlements import decide_entitlements, EntitlementsContext; print('step7_entitlements_ok=', callable(decide_entitlements) and (EntitlementsContext is not None))"
  python3 -c "from backend.app.security.headers import security_headers; print('step7_headers_ok=', isinstance(security_headers(is_https=False,is_non_local=False), dict))"
  python3 -c "from backend.app.security.abuse import decide_abuse; print('step7_abuse_ok=', callable(decide_abuse))"
  python3 -c "import backend.app.cost.policy; print('OK backend.app.cost import')" 
  python3 -c "import mci_backend.main; print('OK mci_backend.main import')" 
  python3 -c "from backend.app.observability.request_id import get_request_id; import inspect; print('get_request_id_callable=', callable(get_request_id))"
  python3 -c "import backend.app.main as m; print('datetime_in_main=', hasattr(m, 'datetime'))"
  python3 -c "from backend.app.ux.state import decide_ux_state; print('step8_ux_ok=', callable(decide_ux_state))"
  if [[ -f "$SCRIPT_DIR/../docs/PHASE16_STEP6_OBSERVABILITY_UPGRADE.md" ]]; then echo "step6_doc_upgrade_present=1"; else echo "step6_doc_upgrade_present=0"; fi
  if [[ -f "$SCRIPT_DIR/../docs/DASHBOARD_SPEC.md" ]]; then echo "dashboard_spec_present=1"; else echo "dashboard_spec_present=0"; fi
  if [[ -f "$SCRIPT_DIR/eval_gate.sh" ]]; then echo "eval_gate_present=1"; else echo "eval_gate_present=0"; fi
  if [[ -x "$SCRIPT_DIR/eval_gate.sh" ]]; then echo "eval_gate_executable=1"; else echo "eval_gate_executable=0"; fi
  if [[ -f "$SCRIPT_DIR/../backend/tests/test_step6_observability_contract.py" ]]; then echo "step6_contract_test_present=1"; else echo "step6_contract_test_present=0"; fi
  if [[ -f "$SCRIPT_DIR/../backend/tests/test_step6_eval_gate_scenarios.py" ]]; then echo "step6_scenarios_test_present=1"; else echo "step6_scenarios_test_present=0"; fi
  if [[ -f "$SCRIPT_DIR/../backend/tests/test_step7_headers.py" ]]; then echo "step7_headers_test_present=1"; else echo "step7_headers_test_present=0"; fi
  if [[ -f "$SCRIPT_DIR/../backend/tests/test_step7_abuse_scoring.py" ]]; then echo "step7_abuse_test_present=1"; else echo "step7_abuse_test_present=0"; fi
  if [[ -f "$SCRIPT_DIR/security_gate.sh" ]]; then echo "security_gate_present=1"; else echo "security_gate_present=0"; fi
  if [[ -x "$SCRIPT_DIR/security_gate.sh" ]]; then echo "security_gate_executable=1"; else echo "security_gate_executable=0"; fi
  if [[ -f "$SCRIPT_DIR/../docs/PHASE16_STEP7_SECURITY_UPGRADE.md" ]]; then echo "step7_security_doc_present=1"; else echo "step7_security_doc_present=0"; fi
  if [[ -f "$SCRIPT_DIR/../docs/PHASE16_STEP7_PENTEST_CHECKLIST.md" ]]; then echo "step7_pentest_doc_present=1"; else echo "step7_pentest_doc_present=0"; fi
  if [[ -f "$SCRIPT_DIR/../docs/PHASE16_STEP8_UX_RELIABILITY.md" ]]; then echo "step8_ux_doc_present=1"; else echo "step8_ux_doc_present=0"; fi
  if [[ -f "$SCRIPT_DIR/../backend/tests/test_step8_ux_state_mapping.py" ]]; then echo "step8_state_test_present=1"; else echo "step8_state_test_present=0"; fi
  if [[ -f "$SCRIPT_DIR/../backend/tests/test_step8_ux_headers.py" ]]; then echo "step8_headers_test_present=1"; else echo "step8_headers_test_present=0"; fi
  if [[ -f "$SCRIPT_DIR/ux_gate.sh" ]]; then echo "ux_gate_present=1"; else echo "ux_gate_present=0"; fi
  if [[ -x "$SCRIPT_DIR/ux_gate.sh" ]]; then echo "ux_gate_executable=1"; else echo "ux_gate_executable=0"; fi
  if [[ -f "$SCRIPT_DIR/../frontend/app/components/system-status/SystemStatus.tsx" ]]; then echo "step8b_system_status_present=1"; else echo "step8b_system_status_present=0"; fi
  if [[ -f "$SCRIPT_DIR/../frontend/app/lib/ux_state.ts" ]]; then echo "step8b_ux_state_helper_present=1"; else echo "step8b_ux_state_helper_present=0"; fi
  if [[ -f "$SCRIPT_DIR/ux_frontend_gate.sh" ]]; then echo "ux_frontend_gate_present=1"; else echo "ux_frontend_gate_present=0"; fi
  if [[ -x "$SCRIPT_DIR/ux_frontend_gate.sh" ]]; then echo "ux_frontend_gate_executable=1"; else echo "ux_frontend_gate_executable=0"; fi
  python3 -c "from backend.app.release import load_release_flags, decide_canary; print('step9_release_ok=', callable(load_release_flags) and callable(decide_canary))"
  if [[ -f "$SCRIPT_DIR/../backend/tests/test_step9_canary_determinism.py" ]]; then echo "step9_canary_test_present=1"; else echo "step9_canary_test_present=0"; fi
  if [[ -f "$SCRIPT_DIR/../backend/tests/test_step9_flags_parsing.py" ]]; then echo "step9_flags_test_present=1"; else echo "step9_flags_test_present=0"; fi
  if [[ -f "$SCRIPT_DIR/canary_check.sh" ]]; then echo "canary_check_present=1"; else echo "canary_check_present=0"; fi
  if [[ -x "$SCRIPT_DIR/canary_check.sh" ]]; then echo "canary_check_executable=1"; else echo "canary_check_executable=0"; fi
  if [[ -f "$SCRIPT_DIR/../docs/PHASE16_STEP9_RELEASE_ENGINEERING.md" ]]; then echo "step9_doc_present=1"; else echo "step9_doc_present=0"; fi
  if [[ -f "$SCRIPT_DIR/../docs/PHASE16_CERTIFICATION.md" ]]; then echo "phase16_cert_present=1"; else echo "phase16_cert_present=0"; echo "ERROR: missing docs/PHASE16_CERTIFICATION.md" >&2; exit 1; fi
  if [[ -f "$SCRIPT_DIR/../docs/PHASE17_DEEP_THINKING_CONTRACT.md" ]]; then echo "phase17_contract_present=1"; else echo "phase17_contract_present=0"; echo "ERROR: missing docs/PHASE17_DEEP_THINKING_CONTRACT.md" >&2; exit 1; fi
  if [[ -f "$SCRIPT_DIR/../docs/PHASE17_CERTIFICATION.md" ]]; then echo "phase17_cert_present=1"; else echo "phase17_cert_present=0"; echo "ERROR: missing docs/PHASE17_CERTIFICATION.md" >&2; exit 1; fi
  if [[ -f "$SCRIPT_DIR/../backend/tests/test_phase17_eval_gates.py" ]]; then echo "phase17_eval_gates_present=1"; else echo "phase17_eval_gates_present=0"; echo "ERROR: missing backend/tests/test_phase17_eval_gates.py" >&2; exit 1; fi
  if [[ -f "$SCRIPT_DIR/../docs/PHASE18_RESEARCH_CONTRACT.md" ]]; then
    echo "phase18_contract_present=1"
    if ! grep -q 'ContractVersion.*"18.0.0"' "$SCRIPT_DIR/../docs/PHASE18_RESEARCH_CONTRACT.md"; then
      echo "ERROR: PHASE18_RESEARCH_CONTRACT.md missing ContractVersion 18.0.0" >&2
      exit 1
    fi
    if ! grep -q 'Status.*FROZEN' "$SCRIPT_DIR/../docs/PHASE18_RESEARCH_CONTRACT.md"; then
      echo "ERROR: PHASE18_RESEARCH_CONTRACT.md missing Status: FROZEN" >&2
      exit 1
    fi
    if ! grep -q 'RESEARCH STOP REASONS' "$SCRIPT_DIR/../docs/PHASE18_RESEARCH_CONTRACT.md"; then
      echo "ERROR: PHASE18_RESEARCH_CONTRACT.md missing ResearchStopReasons section" >&2
      exit 1
    fi
  else
    echo "phase18_contract_present=0"
    echo "ERROR: missing docs/PHASE18_RESEARCH_CONTRACT.md" >&2
    exit 1
  fi
  if [[ -f "$SCRIPT_DIR/../backend/tests/test_phase18_eval_gates.py" ]]; then
    echo "phase18_eval_gates_present=1"
  else
    echo "phase18_eval_gates_present=0"
    echo "ERROR: missing backend/tests/test_phase18_eval_gates.py" >&2
    exit 1
  fi
  # Phase 19 Memory Eval Gates (fail-closed)
  if [[ -f "$SCRIPT_DIR/../backend/tests/test_phase19_eval_gates.py" ]]; then
    echo "phase19_eval_gates_present=1"
    if ! grep -q 'PHASE 19 MEMORY EVAL GATES' "$SCRIPT_DIR/../backend/tests/test_phase19_eval_gates.py"; then
      echo "ERROR: backend/tests/test_phase19_eval_gates.py missing required header" >&2
      exit 1
    fi
  else
    echo "phase19_eval_gates_present=0"
    echo "ERROR: missing backend/tests/test_phase19_eval_gates.py" >&2
    exit 1
  fi
  # Phase 19 Memory Contract checks (fail-closed)
  if [[ -f "$SCRIPT_DIR/../docs/PHASE19_MEMORY_CONTRACT.md" ]]; then
    echo "phase19_contract_present=1"
    if ! grep -q 'ContractVersion.*"19.0.0"' "$SCRIPT_DIR/../docs/PHASE19_MEMORY_CONTRACT.md"; then
      echo "ERROR: PHASE19_MEMORY_CONTRACT.md missing ContractVersion 19.0.0" >&2
      exit 1
    fi
    if ! grep -q 'Status.*FROZEN' "$SCRIPT_DIR/../docs/PHASE19_MEMORY_CONTRACT.md"; then
      echo "ERROR: PHASE19_MEMORY_CONTRACT.md missing Status: FROZEN" >&2
      exit 1
    fi
    if ! grep -q 'MEMORY STOP REASONS' "$SCRIPT_DIR/../docs/PHASE19_MEMORY_CONTRACT.md"; then
      echo "ERROR: PHASE19_MEMORY_CONTRACT.md missing MEMORY STOP REASONS section" >&2
      exit 1
    fi
    if ! grep -q 'ALLOWED MEMORY CATEGORIES' "$SCRIPT_DIR/../docs/PHASE19_MEMORY_CONTRACT.md"; then
      echo "ERROR: PHASE19_MEMORY_CONTRACT.md missing ALLOWED MEMORY CATEGORIES section" >&2
      exit 1
    fi
    if ! grep -q 'FORBIDDEN CATEGORIES' "$SCRIPT_DIR/../docs/PHASE19_MEMORY_CONTRACT.md"; then
      echo "ERROR: PHASE19_MEMORY_CONTRACT.md missing FORBIDDEN CATEGORIES section" >&2
      exit 1
    fi
    if ! grep -q "NO SOURCE.*DON'T STORE" "$SCRIPT_DIR/../docs/PHASE19_MEMORY_CONTRACT.md"; then
      echo "ERROR: PHASE19_MEMORY_CONTRACT.md missing NO SOURCE → DON'T STORE rule" >&2
      exit 1
    fi
    echo "phase19_contract_valid=1"
  else
    echo "phase19_contract_present=0"
    echo "ERROR: missing docs/PHASE19_MEMORY_CONTRACT.md" >&2
    exit 1
  fi
  # Phase 20 Governance Contract checks (fail-closed)
  if [[ -f "$SCRIPT_DIR/../docs/PHASE20_GOVERNANCE_CONTRACT.md" ]]; then
    echo "phase20_contract_present=1"
    # Extract current contract version
    PHASE20_VERSION=$(grep -o 'ContractVersion.*"[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*"' "$SCRIPT_DIR/../docs/PHASE20_GOVERNANCE_CONTRACT.md" | grep -o '[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*' || echo "")
    if [[ -z "$PHASE20_VERSION" ]]; then
      echo "ERROR: PHASE20_GOVERNANCE_CONTRACT.md missing valid ContractVersion" >&2
      exit 1
    fi
    echo "phase20_contract_version=$PHASE20_VERSION"
    # Check version starts with 20.
    if [[ ! "$PHASE20_VERSION" =~ ^20\. ]]; then
      echo "ERROR: PHASE20_GOVERNANCE_CONTRACT.md ContractVersion must be 20.x.y" >&2
      exit 1
    fi
    if ! grep -q 'Status.*FROZEN' "$SCRIPT_DIR/../docs/PHASE20_GOVERNANCE_CONTRACT.md"; then
      echo "ERROR: PHASE20_GOVERNANCE_CONTRACT.md missing Status: FROZEN" >&2
      exit 1
    fi
    if ! grep -q 'STOP REASONS (EXHAUSTIVE)' "$SCRIPT_DIR/../docs/PHASE20_GOVERNANCE_CONTRACT.md"; then
      echo "ERROR: PHASE20_GOVERNANCE_CONTRACT.md missing STOP REASONS (EXHAUSTIVE) section" >&2
      exit 1
    fi
    if ! grep -q 'FAIL-CLOSED LADDER (PRIORITY ORDER)' "$SCRIPT_DIR/../docs/PHASE20_GOVERNANCE_CONTRACT.md"; then
      echo "ERROR: PHASE20_GOVERNANCE_CONTRACT.md missing FAIL-CLOSED LADDER (PRIORITY ORDER) section" >&2
      exit 1
    fi
    if ! grep -q 'VERSIONING & CHANGE CONTROL' "$SCRIPT_DIR/../docs/PHASE20_GOVERNANCE_CONTRACT.md"; then
      echo "ERROR: PHASE20_GOVERNANCE_CONTRACT.md missing VERSIONING & CHANGE CONTROL section" >&2
      exit 1
    fi
    # Hash-based change detection
    if [[ -f "$SCRIPT_DIR/../docs/PHASE20_GOVERNANCE_CONTRACT.hash" ]]; then
      STORED_HASH=$(cat "$SCRIPT_DIR/../docs/PHASE20_GOVERNANCE_CONTRACT.hash" 2>/dev/null || echo "")
      if command -v sha256sum >/dev/null 2>&1; then
        CURRENT_HASH=$(sha256sum "$SCRIPT_DIR/../docs/PHASE20_GOVERNANCE_CONTRACT.md" | cut -d' ' -f1)
      else
        CURRENT_HASH=$(python3 -c "import hashlib, pathlib; p=pathlib.Path('$SCRIPT_DIR/../docs/PHASE20_GOVERNANCE_CONTRACT.md'); print(hashlib.sha256(p.read_bytes()).hexdigest())" 2>/dev/null || echo "")
      fi
      if [[ "$STORED_HASH" == "$CURRENT_HASH" ]]; then
        echo "phase20_contract_hash_match=1"
      else
        echo "phase20_contract_hash_match=0"
        # Check if release evidence exists for this version
        if grep -q "Phase20ContractVersion.*$PHASE20_VERSION" "$SCRIPT_DIR/../docs/RELEASE_LOG.md"; then
          echo "phase20_release_evidence_present=1"
        else
          echo "phase20_release_evidence_present=0"
          echo "ERROR: Phase 20 contract changed without version bump + release evidence" >&2
          exit 1
        fi
      fi
    else
      echo "ERROR: missing docs/PHASE20_GOVERNANCE_CONTRACT.hash" >&2
      exit 1
    fi
    echo "phase20_contract_valid=1"
  else
    echo "phase20_contract_present=0"
    echo "ERROR: missing docs/PHASE20_GOVERNANCE_CONTRACT.md" >&2
    exit 1
  fi
  bash -n "$SCRIPT_DIR/chaos_gate.sh"
  python3 -c "import backend.app.reliability.engine as e; print('step5_engine_ok=', hasattr(e,'run_step5'))"
  python3 -c "import backend.app.quality.gate as q; print('step5_quality_ok=', hasattr(q,'evaluate_quality'))"
  python3 -c "import backend.app.safety.envelope as s; print('step5_safety_ok=', hasattr(s,'apply_safety'))"
  echo

  run_optional "Phase 15 drills (staging subset)" bash "$DRILLS"
  run_optional "Phase 15 certify subset" bash "$CERTIFY"
  if [[ -x "$SCRIPT_DIR/cost_gate_chat.sh" && -n "${BASE:-}" ]]; then
    echo "---- Cost gate (staging optional)"
    MODE=staging BASE="$BASE" bash "$SCRIPT_DIR/cost_gate_chat.sh" || true
    echo
  fi
fi

if [[ "$MODE_LOWER" == "prod" ]]; then
  echo "Production gate is evidence-only; deployment must occur via release branch promotion (no direct deploys here)."
fi

echo "Promotion gate completed (mode=$MODE_LOWER). Review outputs above for PASS/FAIL."
