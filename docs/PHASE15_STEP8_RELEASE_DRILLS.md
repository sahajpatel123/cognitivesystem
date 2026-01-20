# Phase 15 — Step 8: Release Drills (Staging → Prod)

## 1) Purpose & Non-Negotiables (LOCK DOC)
- Phase 15 anchors: production hardening, public release readiness, deterministic failure handling, passive observability, no sensitive logging, no cognition changes.
- Phases 1–14 stay locked: **no cognition logic changes**, no personalization, no prompt/plan alterations, no silent degradation.
- /api/chat contract remains stable: always returns `{action, rendered_text, failure_type, failure_reason}`.
- Debug detail only when `DEBUG_ERRORS=1` (staging only). Never log user_text or prompts.

## 2) Staging Topology (Option A)
- **Frontend (staging):** Vercel preview or separate Vercel project (recommended: preview first).
- **Backend (staging):** Separate Railway service (suggested name: `cognitivesystem-staging`).
- **DB/Auth (staging):** Separate Supabase project (suggested name: `cognitivesystem-staging`).
- **Routing:** Vercel (staging) → Railway (staging) → Supabase (staging).
- Production stays unchanged on existing Railway + Supabase.

## 3) Environment Variable Matrix (names only; no secrets)

| Variable | Production source | Staging source |
| --- | --- | --- |
| NEXT_PUBLIC_BACKEND_URL | Prod Railway URL | Staging Railway URL |
| CORS_ORIGINS | Prod frontend origin(s) | Staging frontend origin(s) |
| DATABASE_URL | Prod Supabase Postgres | Staging Supabase Postgres |
| SUPABASE_URL | Prod Supabase URL | Staging Supabase URL |
| SUPABASE_ANON_KEY | Prod anon key (public) | Staging anon key (public) |
| SUPABASE_JWKS_URL / SUPABASE_PROJECT_REF | Prod Supabase project | Staging Supabase project |
| IDENTITY_HASH_SALT | Prod salt | Staging salt (distinct) |
| PLAN_DEFAULT / PRO_SUBJECTS / MAX_SUBJECTS | Prod values | Staging values (can be stricter) |
| WAF_* (burst/sustain/lockout) | Prod values | Staging values (same or stricter) |
| DEBUG_ERRORS | 0 | 1 allowed temporarily during drills, then reset to 0 |
| MODEL_PROVIDER / MODEL_NAME | Prod choice | Staging choice (can be same) |
| MODEL_API_KEY / MODEL_PROVIDER_BASE_URL / MODEL_TIMEOUT_* | Prod secrets | Staging secrets (separate key) |
| REQUEST_ID_HEADER | x-request-id (default) | same |
| BACKEND_PUBLIC_BASE_URL | Prod base URL | Staging base URL |

## 4) Staging Setup Procedure (dashboards)
1) **Railway (backend staging)**  
   - Create new service from repo main branch.  
   - Builder: Nixpacks; Start: `bash start.sh`.  
   - Set env vars per matrix (staging values).  
   - Include `CORS_ORIGINS` with staging Vercel origin(s).
2) **Supabase (staging)**  
   - Create new project.  
   - Run migration `backend/app/db/migrations/001_init.sql` in SQL editor.  
   - Confirm tables (sessions, requests, rate_limits, etc.) exist.  
   - Capture staging `SUPABASE_URL`, `SUPABASE_ANON_KEY`, project ref/JWKS URL.
3) **Auth/JWKS**  
   - Ensure JWT issuer/audience point to staging Supabase.  
   - Set corresponding envs (`SUPABASE_JWT_ISSUER`, `SUPABASE_JWT_AUD`, JWKS).
4) **Vercel (frontend staging)**  
   - Configure preview env vars: `NEXT_PUBLIC_BACKEND_URL` → staging Railway URL.  
   - Add staging frontend origin to staging `CORS_ORIGINS`.
5) **Prod untouched** during staging setup.

## 5) Drill Suite (copy-paste; Mac zsh/bash)
Set bases:
```bash
STAGING_BASE=https://<staging-service>.up.railway.app
PROD_BASE=https://cognitivesystem-production.up.railway.app
FRONTEND_ORIGIN=https://<staging-vercel>.vercel.app
```

**DRILL A: Boot & health**
```bash
curl -s $STAGING_BASE/health
curl -s $STAGING_BASE/db/health
```

**DRILL B: Identity (anon cookie)**
```bash
curl -i -c cookies.txt $STAGING_BASE/auth/whoami | head -n 5
# Expect Set-Cookie anon_session present.
```

**DRILL C: /api/chat happy path**
```bash
curl -i -b cookies.txt -X POST "$STAGING_BASE/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"user_text":"hi"}'
# Expect 200 and action/rendered_text/failure_type/failure_reason fields.
```

**DRILL D: /api/chat content-type rejection**
```bash
curl -i -X POST "$STAGING_BASE/api/chat" \
  -H "Content-Type: text/plain" \
  -d 'hi'
# Expect 415 content_type_invalid
```

**DRILL E: invalid JSON**
```bash
curl -i -X POST "$STAGING_BASE/api/chat" \
  -H "Content-Type: application/json" \
  -d '{bad json'
# Expect 400 json_invalid (or current stable error_code)
```

**DRILL F: missing user_text**
```bash
curl -i -X POST "$STAGING_BASE/api/chat" \
  -H "Content-Type: application/json" \
  -d '{}'
# Expect structured 400 user_text_missing (or current stable error_code)
```

**DRILL G: Plan limits (Step 4)**
_Requests/day cap (do in staging only):_
```bash
for i in {1..12}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST "$STAGING_BASE/api/chat" \
    -H "Content-Type: application/json" \
    -d '{"user_text":"hi"}';
done
# Expect later responses to return 429 requests_limit_exceeded (or equivalent).
```
_Token budget cap (send bounded long text):_
```bash
LONG=$(python3 - <<'PY'\nprint("x"*9000)\nPY)
curl -i -X POST "$STAGING_BASE/api/chat" \
  -H "Content-Type: application/json" \
  -d "{\"user_text\":\"$LONG\"}"
# Expect 429 token_budget_exceeded (or equivalent).
```

**DRILL H: WAF burst (Step 5)**  
Burst safely, watch for 429 (stop with CTRL+C; if backgrounded use `jobs -l` then `kill %<jobid>` or `kill <pid>`):
```bash
for i in {1..40}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST "$STAGING_BASE/api/chat" \
    -H "Content-Type: application/json" \
    -d '{"user_text":"hi"}';
done
```

**DRILL I: Observability verification (Step 6)**  
- In Railway logs, confirm structured line: `type=api_chat`, `request_id`, `status_code`, `latency_ms`, `hashed_subject`, `waf_decision`, `plan_decision`.  
- Verify no user_text appears.  
- Capture sample log line and paste in evidence.

## 6) Failure Drills (STAGING ONLY)
1) **Remove DATABASE_URL**  
   - Action: unset DATABASE_URL in staging Railway; redeploy.  
   - Expect: `/db/health` returns error; `/api/chat` may fail closed with safe error; app should still start.  
   - Rollback: restore DATABASE_URL and redeploy.
2) **Invalid CORS_ORIGINS format**  
   - Action: set `CORS_ORIGINS=` to invalid JSON (e.g., `{bad}`) in staging.  
   - Expect: app fails fast on startup; Railway deploy shows config parse error.  
   - Rollback: set valid JSON/CSV and redeploy.
3) **Invalid model provider key**  
   - Action: set wrong MODEL_API_KEY in staging.  
   - Expect: /api/chat returns governed fallback with model failure (no traceback), stable contract.  
   - Rollback: restore valid key, redeploy.

## 7) Rollback Drill
- In Railway staging, use “Rollback” to previous deployment (or redeploy older commit).  
- Verify `/health` and `/api/chat` return healthy responses.  
- Record request_id and log evidence.

## 8) Certification Checklist (Step 8 completion)
- All staging drills A–I pass; failure drills validated and rolled back.  
- Prod smoke (A–D only) passes.  
- Evidence captured: request_ids, sample logs (no user_text).  
- No cognition/contract changes introduced.  
- Debug flags reset (`DEBUG_ERRORS=0` in prod; staging reset after drill).

## 9) Optional: Script Runner
- See `scripts/release_drills.sh` for a minimal A–F runner (uses `BASE` env var).  
- Run in staging only; inspect outputs manually; does not modify backend behavior.
