# Phase 16 Step 9 — Release Engineering (Flags + Canary + Rollback + Versioning)

## Purpose
- Safely ship non-cognition changes with deterministic canary exposure and explicit rollback levers.
- Emit passive metadata headers (X-Canary, X-Build-Version) and structured chat.summary hints without altering routing, safety, or model selection.

## Non-goals
- No changes to cognition, routing, safety envelopes, quality gates, or entitlements semantics.
- No new external services or dashboards; no user-content logging.
- No request/response schema changes beyond additive headers and safe metadata fields.

## Flags (env)
| Env var | Default | Description |
| --- | --- | --- |
| `RELEASE_CANARY_ENABLED` | `0` | Master switch for canary exposure. |
| `RELEASE_CANARY_PERCENT` | `0` | Percent bucket (0–100) for deterministic canary. |
| `RELEASE_CANARY_ALLOWLIST` | empty | Comma list of subject_ids force-canary (only if canary enabled). |
| `RELEASE_HEADER_BUILD_VERSION` | `1` | Emit `X-Build-Version` header. |
| `RELEASE_HEADER_CANARY` | `1` | Emit `X-Canary` header (`0/1`). |
| `RELEASE_CHAT_SUMMARY_CANARY` | `1` | Include `canary` boolean in `chat.summary`. |
| `RELEASE_CHAT_SUMMARY_FLAGS` | `0` | Include minimal digest `{canary_enabled, canary_percent}` in `chat.summary`. |

## Canary algorithm (deterministic)
- `bucket = int(sha256(request_id).hexdigest()[0:8], 16) % 100`
- `is_canary = bucket < percent` when canary enabled.
- Allowlist: if `subject_id` in allowlist and canary enabled, force `is_canary=True`.
- Pure, no routing/model side effects.

## Rollback playbook
1) Set `RELEASE_CANARY_ENABLED=0` to halt canary.
2) Optionally disable headers: set `RELEASE_HEADER_CANARY=0`, `RELEASE_HEADER_BUILD_VERSION=0` if needed.
3) Optionally disable chat.summary fields: set `RELEASE_CHAT_SUMMARY_CANARY=0`, `RELEASE_CHAT_SUMMARY_FLAGS=0`.
4) Capture evidence: `request_id`, `X-Canary`, `X-Build-Version`, timestamp, status code; do not log `user_text`/`rendered_text`.
5) Re-run gates (promotion + canary_check) after toggles.

## Verification checklist
- Local: `python3 -m compileall backend mci_backend`
- Local: `python3 -c "import backend.app.main; print('OK backend.app.main import')"`
- Local: `pytest -q backend/tests/test_step9_canary_determinism.py backend/tests/test_step9_flags_parsing.py`
- Local: `bash -n scripts/promotion_gate.sh scripts/canary_check.sh`
- Staging: `MODE=staging BASE=$STAGING_BASE ./scripts/promotion_gate.sh`
- Staging: `BASE=$STAGING_BASE ./scripts/canary_check.sh`

## Privacy note
- Never log `user_text` or `rendered_text` in flags/canary metadata.
- Allowlist values are not emitted in logs or summaries.
