#!/usr/bin/env bash
set -euo pipefail

MODE="${MODE:-local}"
BASE="${BASE:-http://localhost:8000}"
ATTEMPTS="${ATTEMPTS:-12}"
RETRY_MAX_TIME="${RETRY_MAX_TIME:-180}" # unused but kept for compatibility

info() { echo "[canary_check] $*"; }
fail() { echo "[canary_check][FAIL] $*" >&2; exit 1; }

workdir="$(mktemp -d)"
last_hdr_file=""
last_body_file=""
cleanup() {
  if [[ -n "${last_hdr_file}" && -f "${last_hdr_file}" ]]; then
    :
  fi
  if [[ -n "${last_body_file}" && -f "${last_body_file}" ]]; then
    :
  fi
  rm -rf "${workdir}" 2>/dev/null || true
}
trap cleanup EXIT

# Health check (IPv4 + HTTP/1.1)
health_code=$(curl -4 --http1.1 -sS --connect-timeout 8 --max-time 15 -o /dev/null -w "%{http_code}" "${BASE}/health" || true)
if [[ "${health_code}" != "200" ]]; then
  fail "health not ok http_code=${health_code}"
fi
info "health ok"

payload='{"user_text":"hi"}'
allowed_actions="ANSWER ASK_CLARIFY FALLBACK"
last_hdr=""
last_body=""
last_reason="unknown"

for attempt in $(seq 1 ${ATTEMPTS}); do
  hdr="$(mktemp "${workdir}/hdr.XXXX")"
  body="$(mktemp "${workdir}/body.XXXX")"
  last_hdr_file="${hdr}"
  last_body_file="${body}"
  chat_rc=0
  curl -4 --http1.1 -sS \
    --connect-timeout 8 --max-time 15 \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -H "Accept-Encoding: identity" \
    -H "Connection: close" \
    -H "Expect:" \
    --ignore-content-length \
    -D "${hdr}" -o "${body}" \
    -d "${payload}" \
    "${BASE}/api/chat" || chat_rc=$?

  hdr_norm=$(tr -d '\r' < "${hdr}")
  status_line=$(printf "%s" "${hdr_norm}" | head -n1)
  last_hdr="${hdr_norm}"
  last_body=$(cat "${body}" 2>/dev/null || true)

  if [[ ${chat_rc} -ne 0 ]]; then
    last_reason="curl_fail"
    info "attempt=${attempt} reason=curl_fail"
    sleep 1
    continue
  fi

  if [[ "${status_line}" != *"200"* ]]; then
    last_reason="bad_status"
    info "attempt=${attempt} reason=bad_status"
    sleep 1
    continue
  fi

  if ! printf "%s" "${hdr_norm}" | grep -qi '^x-request-id:'; then
    last_reason="missing_reqid"
    info "attempt=${attempt} reason=missing_reqid"
    sleep 1
    continue
  fi

  # body handling
  has_ux=$(printf "%s" "${hdr_norm}" | grep -qi '^x-ux-state:' && echo yes || echo no)

  if [[ ! -s "${body}" ]]; then
    if [[ "${has_ux}" == "yes" ]]; then
      info "attempt=${attempt} reason=body_truncated_ok"
      echo "[canary_check][PASS] status=200 reqid=$(printf "%s" "${hdr_norm}" | grep -i '^x-request-id:' | head -n1 | cut -d':' -f2- | xargs) mode=${MODE} base=${BASE} action=TRUNCATED ux_state=$(printf "%s" "${hdr_norm}" | grep -i '^x-ux-state:' | head -n1 | cut -d':' -f2- | xargs)"
      exit 0
    else
      last_reason="parse_fail"
      info "attempt=${attempt} reason=empty_body"
      sleep 1
      continue
    fi
  fi

  action=$(python3 - <<'PY' "${body}" || true
import json, sys
p = sys.argv[1]
try:
    with open(p, 'r', encoding='utf-8') as f:
        obj = json.load(f)
    print(obj.get('action', ''))
except Exception:
    print('')
PY
  )

  case " ${allowed_actions} " in
    *" ${action} "*)
      info "attempt=${attempt} reason=ok"
      echo "[canary_check][PASS] status=200 reqid=$(printf "%s" "${hdr_norm}" | grep -i '^x-request-id:' | head -n1 | cut -d':' -f2- | xargs) mode=${MODE} base=${BASE} action=${action} ux_state=$(printf "%s" "${hdr_norm}" | grep -i '^x-ux-state:' | head -n1 | cut -d':' -f2- | xargs)"
      exit 0
      ;;
    *)
      last_reason="parse_fail"
      info "attempt=${attempt} reason=parse_fail"
      sleep 1
      continue
      ;;
  esac
done

echo "[canary_check][FAIL] could not obtain valid action after ${ATTEMPTS} attempts (last_reason=${last_reason})"
echo "[canary_check] headers (last 30 lines):"
printf "%s\n" "${last_hdr}" | tail -n 30 || true

echo "[canary_check] body (first 200 chars):"
printf "%s" "${last_body}" | head -c 200 2>/dev/null || true
echo
exit 1
