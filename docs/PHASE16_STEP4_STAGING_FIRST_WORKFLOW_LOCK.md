# Phase 16 Step 4 — Staging-First Workflow (Option B: Release Branch Promotion) LOCK

## Purpose
Enforce staging-first promotion so production only advances by fast-forwarding the release branch from staging-tested commits. Prevents direct-to-prod changes, preserves Phase 15 baseline, and keeps cognition unchanged.

## Option B Model (Main → Release)
- `main` branch = staging only; all changes land here and deploy to staging.
- `release` branch = production only; no feature work directly on `release`.
- Promotions are fast-forward from `main` → `release` using the exact staging-tested commit SHA.
- Rollbacks adjust `release` to a prior known-good SHA and redeploy.
- All promotions/rollbacks are recorded in docs/RELEASE_LOG.md (append-only).

## Non-Negotiable Rules
- No cognition logic changes, personalization, or silent degradation.
- Observability remains passive; no raw prompt logging or new storage.
- APP_ENV must be staging on staging, production on prod; DEBUG_ERRORS=0 in both.
- CORS and DB host allowlists follow Step 2 guards; any cross-wire invalidates the promotion.
- No “one last fix” between staging pass and production promotion.

## Required Gates Before Promotion
- Run staging gates (MODE=staging) via scripts/promotion_gate.sh (includes smoke; optional drills/certify).
- Required curls on staging: /health, /db/health, /auth/whoami, /api/chat happy (“hi”), /api/chat 415, burst 10–20 (expect 200/429, no 500s).
- Use only safe payload “hi”; temp cookies only.

## Production Smoke After Promotion
- Run MODE=prod via scripts/promotion_gate.sh: health, db health, whoami, chat happy, chat 415.
- If any fail, initiate rollback to last known good `release` SHA.

## Release Branch Promotion Mechanics
- Promote by fast-forwarding `release` to the staging-tested commit from `main`.
- No merge commits onto `release`; no force-pushing unless rolling back to a prior known-good SHA with operator approval.
- Production deploys from `release` only.

## Rollback Discipline
- Triggers: 5xx spike, auth failure, DB failure, unexpected 429/415 patterns, staging gate regression observed in prod.
- Action: reset `release` to prior known-good SHA, push, redeploy, rerun production smoke subset.
- Log rollback in docs/RELEASE_LOG.md.

## Evidence & Logging
- For each promotion: record commit SHA, date/time, staging BASE, gates run/results, rollout notes, prod smoke results, operator, rollback plan pointer in docs/RELEASE_LOG.md.
- For rollbacks: record trigger, from/to SHA, symptoms, post-rollback verification.

## How We Work Daily
- Dev work → PR/merge to `main` → staging deploy → run gates (MODE=staging) → log evidence → fast-forward `release` to RC commit → prod deploy → prod smoke → log promotion in release log.

## Invalidation Triggers
- Direct prod deploy not via `release`.
- `release` SHA differs from staging-tested commit.
- Missing staging evidence before promotion.
- DEBUG_ERRORS enabled in staging/prod; CORS wildcard or DB allowlist mismatch in prod.
- Any cognition/personalization/storage expansion or raw prompt logging.

## Status
- Phase 16 Step 4 Status: COMPLETE ✅
- Locked on: 2026-01-22
