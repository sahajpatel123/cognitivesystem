# Phase 16 Step 2 — Environment Separation & Safety Guards (LOCK)

## Purpose
Staging-first safety gates to prevent cross-wiring and risky configs from reaching production. Ensures local/staging/prod separation, fail-fast startup checks, and promotion discipline without touching cognition logic or Phase 15 protections.

## Definitions
- APP_ENV: local | staging | production (default local).
- Environment separation: distinct configs and databases per env; staging mirrors prod controls.
- Cross-wire: connecting a service to the wrong database or origins for its environment.
- Promotion gate: staging validation before production deploy using Phase 15 certify subset.

## Required Environment Variables (by env)
- All envs: APP_ENV, CORS_ORIGINS, DATABASE_URL, LOG_LEVEL, REQUEST_ID_HEADER, IDENTITY_HASH_SALT, AUTH_COOKIE_SECURE, PLAN_DEFAULT, MODEL_* (per Step 7), WAF_*.
- Staging/Prod only: DB_HOST_ALLOWLIST_STAGING (staging), DB_HOST_ALLOWLIST_PROD (production), SUPABASE_URL/ANON_KEY/JWT_AUD/JWT_ISSUER, BACKEND_PUBLIC_BASE_URL, MODEL_PROVIDER/KEY (if calls enabled).
- Local: may omit allowlists; may use local DB; DEBUG_ERRORS may be 1 for debugging only.

## Fail-Fast Rules (startup)
- APP_ENV must be local/staging/production; prod/dev synonyms normalize to production/local.
- Staging/production: DATABASE_URL required; CORS_ORIGINS must be set and parse to non-empty; DEBUG_ERRORS must be 0.
- Any violation raises and refuses to boot.

## Cross-Wire Detection
- DATABASE_URL host must match environment allowlist:
  - APP_ENV=staging → DB_HOST_ALLOWLIST_STAGING (CSV) required; host must match entry/substr.
  - APP_ENV=production → DB_HOST_ALLOWLIST_PROD (CSV) required; host must match entry/substr.
- If allowlist missing in staging/prod → fail fast. Local may omit.
- Never log full DATABASE_URL; only masked host.

## CORS Strictness
- Production: no "*" and no localhost origins. Must be explicit prod/staging domains.
- Staging: no "*"; localhost allowed if explicit. Origins normalized (strip trailing slash).
- Local: defaults allowed.

## Debug Safety
- DEBUG_ERRORS must be 0 in staging/production.
- Only local may enable DEBUG_ERRORS=1 for controlled debugging.

## Secrets Rules
- Service role key never exposed to frontend; only backend env.
- Do not check in secrets; env vars set per environment (Vercel/Railway/Supabase).

## Promotion Gate (Staging → Production)
- Run Phase 15 certify subset on staging before promotion:
  - /health, /db/health, /auth/whoami
  - /api/chat happy path (safe payload “hi”)
  - /api/chat wrong content-type 415
  - Burst check: some 429, no 500
- Use scripts: scripts/certify_phase15.sh (staging) and scripts/release_drills.sh as needed.

## Invalidation Triggers
- APP_ENV unset or outside allowed set; missing allowlists in staging/prod.
- Wildcard CORS in staging/prod; localhost origins in production.
- DEBUG_ERRORS > 0 in staging/prod.
- Cross-wired DATABASE_URL (host not in allowlist).
- Logging sensitive data (DATABASE_URL, prompts) or adding new storage beyond bounds.

## Acceptance Checklist
- APP_ENV definition and allowed set documented.
- Fail-fast rules for staging/prod documented.
- Cross-wire detection and allowlists defined.
- CORS and debug safety documented.
- Promotion gate checklist documented.
- Invalidation triggers listed.

## Status
- Phase 16 Step 2 Status: COMPLETE ✅
