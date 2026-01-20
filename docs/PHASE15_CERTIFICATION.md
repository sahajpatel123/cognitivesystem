# Phase 15 Certification (Step 10 Final Lock)

## 1. Phase 15 Certification Summary
- Scope: Production hardening, public readiness, release drills, governance visibility. No cognition logic changes.
- Deliverables: Deployment architecture, DB boundaries, auth/identity, plans/quotas, WAF, observability, secrets/config, release drills, public legal/UX, certification lock.
- Backend/Frontend/DB: FastAPI on Railway, Next.js on Vercel, Supabase Postgres (separate staging/prod).

## 2. Certified Scope
- /api/chat governed pipeline with WAF → plan guard → governed response runtime; contract stable (action, rendered_text, failure_type, failure_reason).
- Identity: anon cookie + optional Supabase JWT verification.
- Storage: sessions, quotas, rate_limits, invocation_logs (metadata only).
- Observability: passive structured logs; no prompts/user_text stored or logged.

## 3. Explicit Non-Goals / Forbidden Changes (Phases 1–14 lock)
- No cognition/runtime logic changes, no prompt memory, no personalization.
- No logging of user_text/prompts; no silent degradation; no new endpoints affecting governance.

## 4. Deployment Evidence
- Frontend (Vercel): https://cognitivesystem.vercel.app/ — env: NEXT_PUBLIC_API_BASE_URL/NEXT_PUBLIC_BACKEND_URL → prod Railway.
- Backend (Railway): https://cognitivesystem-production.up.railway.app — start: `bash start.sh` (uvicorn with proxy headers).
- DB (Supabase): Supabase Postgres; auth JWKS optional; transaction pooler.
- Health checks: /health, /db/health OK.

## 5. Environment Variables (Production)
**Backend Core (REQUIRED)**: APP_ENV, LOG_LEVEL, REQUEST_ID_HEADER, BACKEND_PUBLIC_BASE_URL  
**CORS**: CORS_ORIGINS (JSON list or CSV; defaults to localhost if empty)  
**DB**: DATABASE_URL (Supabase Postgres)  
**Auth**: SUPABASE_URL, SUPABASE_ANON_KEY (public), SUPABASE_JWT_AUD, SUPABASE_JWT_ISSUER, IDENTITY_HASH_SALT, AUTH_COOKIE_SECURE  
**Plans**: PLAN_DEFAULT, PRO_SUBJECTS, MAX_SUBJECTS  
**WAF**: WAF_MAX_BODY_BYTES, WAF_MAX_USER_TEXT_CHARS, WAF_IP_* burst/sustain, WAF_SUBJECT_* burst/sustain, WAF_LOCKOUT_*  
**Observability**: REQUEST_ID_HEADER, LOG_LEVEL (no user_text logged)  
**Debug**: DEBUG_ERRORS (prod must be 0)  
**Model/Step7**: MODEL_PROVIDER, MODEL_NAME, MODEL_API_KEY, MODEL_BASE_URL/MODEL_PROVIDER_BASE_URL, MODEL_TIMEOUT_SECONDS, MODEL_CONNECT_TIMEOUT_SECONDS, MODEL_MAX_*TOKENS, MODEL_CALLS_ENABLED  
All secrets remain in env; none in repo.

## 6. Storage Boundaries & Retention
- Tables: sessions (anon_id, expires_at), rate_limits, quotas, invocation_logs (metadata only). No transcripts.  
- Retention: sessions bounded by TTL; rate/plan windows bounded; invocation_logs short-lived (~14d); quotas ~90d (operational).  
- Forbidden: storing raw prompts/user_text, personalization, long-lived memory.

## 7. Abuse Defense & Cost Boundaries
- WAF: content-type enforcement, payload caps, IP/subject burst & sustain limits, lockouts.  
- Plans: requests/day and token budget caps; output caps.  
- Circuit breakers and timeouts for model calls; kill switch MODEL_CALLS_ENABLED.

## 8. Observability (Passive Only)
- Logs: request_id, route, status_code, latency_ms, hashed_subject, waf_decision/plan_decision, token estimates, error_code.  
- Not logged: user_text/prompts/headers/bodies.  
- Invocation log best-effort; failures do not affect responses.

## 9. Release Drills Evidence
- Reference: docs/PHASE15_STEP8_RELEASE_DRILLS.md; optional script: scripts/release_drills.sh.  
- Drill coverage: health, db health, identity cookie, /api/chat happy, content-type rejection, invalid JSON, missing user_text, plan/token caps, WAF burst, observability log inspection, failure drills, rollback.

## 10. Verification Checklist (Production)
- /health (200), /db/health (db ok), /auth/whoami (sets anon cookie), /api/chat happy path (200 governed response), wrong content-type → 415, burst → 429 after threshold (no 500).

## 11. Known Limitations
- No long-term transcripts; users must copy responses locally.  
- Rate limits/quota may block high-volume usage.  
- Debug detail only when DEBUG_ERRORS=1 (staging only).  
- Model provider availability can impact responses (fallbacks possible).

## 12. Invalidation Triggers (Re-certify)
- Any change to cognition pipeline, prompt handling, storage schema for prompts, or observability contents.  
- Changes to WAF/plan policies, token caps, or contract.  
- Enabling logging of user_text/prompts.  
- Changing hosting topology or env variable semantics.

## 13. Rollback Plan
- Railway: rollback to previous deployment or redeploy prior commit.  
- Vercel: redeploy previous build.  
- Supabase: revert env vars; avoid destructive schema changes (schema unchanged in Step 10).  
- Re-run health + /api/chat smoke after rollback.

## 14. Phase 15 Lock Declaration
- Phase 15 certified and locked. Future changes require Phase 16+ scope with explicit re-certification.

## Commit Evidence
- Step 1: e6ce26c  
- Step 3: 6e62f03  
- Step 4: 48eaa64  
- Step 5: a46b4f7 (+ fixes 82501a7, 5148f1a)  
- Step 6: 71ee352 (+ debug surfacing 1408c53)  
- Step 7: 102c07b (settings/secrets hardening)  
- Step 8: 04bf6bf  
- Step 9: 85c7a99  
- Step 10 (this lock): <to be populated on commit>
