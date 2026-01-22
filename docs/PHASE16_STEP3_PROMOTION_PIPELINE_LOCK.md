# Phase 16 Step 3 — Promotion Pipeline, Release Gates, Rollback Discipline (LOCK)

## Purpose
Production is promotion-only; staging is verification. This lock prevents risky changes from going straight to prod and enforces evidence-based promotion without altering cognition or Phase 15 protections.

## Definitions
- Deploy: build/deploy to an environment (staging or prod).
- Promote: take the exact staging-tested commit/artefact and deploy it to production.
- Evidence: recorded gate results (health/auth/chat/error-path/burst) from staging and post-promotion checks.
- Release Candidate (RC): the specific commit SHA that completed staging gates and is eligible for promotion.

## Environments & URLs (placeholders)
- STAGING_BASE (Railway API): <fill>
- PROD_BASE (Railway API): <fill>
- STAGING_FRONTEND (Vercel): <fill>
- PROD_FRONTEND (Vercel): <fill>
- APP_ENV must be “staging” or “production” accordingly; DEBUG_ERRORS=0; CORS restrictions per Step 2; DB hosts must match env allowlists.

## Promotion Rules (Hard Gates)
- Only promote a commit that ran on staging and passed required gates.
- No “one last fix” between staging pass and prod promotion; promotion uses the SAME commit SHA.
- Forbidden: cognition logic changes, personalization/memory, adaptive behavior changes.

## Required Gates (Staging BEFORE Promotion)
- /health → 200
- /db/health → 200
- /auth/whoami → 200 (sets anon cookie)
- /api/chat POST {"user_text":"hi"} → 200 governed response
- /api/chat wrong content-type → 415 with structured error
- Burst: 10–20 chat requests; expect 200 then 429 per limits; no 500s
- Optional evidence: run scripts/release_drills.sh (A–F) and scripts/certify_phase15.sh subset on staging.

## Production Smoke Subset (After Promotion)
- /health, /db/health, /auth/whoami, /api/chat happy (“hi”), /api/chat wrong content-type 415.
- If any fail: initiate rollback.

## Rollback Protocol (Deterministic)
- Triggers: increased 5xx/internal_error, DB failure, auth failure, unexpected 429/415 patterns, or any staging gate regression observed in prod.
- Action: redeploy last known good commit SHA; rerun production smoke subset.
- Record rollback entry in docs/RELEASE_LOG.md.

## Evidence Requirements
- Capture per promotion: commit SHA, date/time, environment, gates run with pass/fail, outputs/links (optional), operator.
- Use docs/RELEASE_LOG.md templates for promotion/rollback entries (append-only).

## Invalidation Triggers
- Bypassing staging gates.
- Promoting a commit different from the staging-tested RC.
- Enabling DEBUG_ERRORS in staging/prod.
- CORS wildcard or localhost in prod.
- DB host not matching allowlist for env.
- Any cognition/personalization change or new storage beyond bounds.

## Status
- Phase 16 Step 3 Status: COMPLETE ✅
- Locked on: 2026-01-22
