# Phase 15 — Step 3: Auth & Identity (Supabase JWT + Anonymous Sessions) — LOCK

## Purpose
Production-safe identity plumbing for public release. Provides:
- Anonymous session identity (cookie-based) with bounded metadata.
- Optional authenticated identity via Supabase JWT (Bearer token).
- Unified IdentityContext for enforcement (subject_type/subject_id).
- No cognition changes; no personalization/memory storage.

## Identity Model
- `subject_type`: `user` (Supabase auth) | `anon` (cookie) | `ip` (fallback)
- `subject_id`: user_id | anon_id | ip_hash
- Additional hashes: `ip_hash`, `user_agent_hash` (SHA256 with `IDENTITY_HASH_SALT`)
- `IdentityContext` fields: is_authenticated, user_id, anon_id, subject_type, subject_id, ip_hash, user_agent_hash

## Token & Cookie Strategy
- Auth: Authorization: Bearer <Supabase JWT>; verified via Supabase JWKS.
- Guest: httpOnly cookie `anon_id` (uuid4), SameSite=Lax, Secure configurable, TTL via `ANON_SESSION_TTL_DAYS` (default 30d).
- IP/User-Agent hashed only (no raw storage), salted by `IDENTITY_HASH_SALT`.

## Storage Boundaries (NO personalization)
- Sessions table (Step 2) stores: anon_id, created_at, last_seen_at, expires_at, metadata {ip_hash, ua_hash}. No prompts or content.
- No embeddings, no long-term profiling, no adaptive memory.
- Telemetry remains minimal (invocation_logs) per Step 2.

## Endpoints
- `GET /auth/whoami` → identity summary (no secrets, no content).
- `POST /auth/logout` → clears anon cookie.
- `GET /db/health` → DB connectivity check (SELECT 1, sanitized detail).

## Env Vars
- `SUPABASE_URL`
- `SUPABASE_JWT_AUD` (default: authenticated)
- `SUPABASE_JWT_ISSUER` (optional; derives from SUPABASE_URL if absent)
- `AUTH_COOKIE_SECURE` (true/false)
- `ANON_SESSION_TTL_DAYS` (default 30)
- `IDENTITY_HASH_SALT` (required in prod; defaults to dev-salt locally)
- (Already present) `CORS_ORIGINS` with allow_credentials=True enabled in app

## CORS / Credentials
- CORS middleware already set with `allow_credentials=True`.
- `CORS_ORIGINS` must include frontend domains (Vercel prod + localhost) to allow cookies.

## Checklist
- Anonymous cookie set on first request; hashed IP/UA only.
- Supabase JWT verified via JWKS; invalid token → treated as guest.
- DB optional: if DATABASE_URL missing or psycopg absent, identity still functions (no crash).
- No storage of raw user content; no prompts/responses recorded.

---
### Phase 15 Step 3 Status: COMPLETE ✅
