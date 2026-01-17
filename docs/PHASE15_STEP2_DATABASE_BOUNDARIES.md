# Phase 15 — Step 2: Database Design (Supabase Postgres) + Storage Boundaries (LOCK)

## Purpose
Introduce a bounded persistence layer for production-hardening without altering cognition logic (Phases 9–14 remain immutable). Storage is limited to session state, quotas, rate limits, and minimal telemetry. No personalization, embeddings, or long-term profiling.

## Strictly Forbidden
- No storage of raw prompts/responses by default.
- No embeddings/vector memory, personalization, adaptive learning, or long-term profiling tables.
- No user content logging beyond minimal telemetry fields defined here.
- No schema changes to cognition components (Phases 9–14).

## Schema (see `backend/app/db/migrations/001_init.sql`)
- **sessions**
  - `id UUID PK`
  - `user_id UUID NULL`
  - `anon_id TEXT NULL`
  - `created_at TIMESTAMPTZ DEFAULT now()`
  - `last_seen_at TIMESTAMPTZ DEFAULT now()`
  - `expires_at TIMESTAMPTZ NOT NULL` (TTL boundary)
  - `metadata JSONB DEFAULT '{}'` (small, non-sensitive)
  - Indexes: `anon_id`, `user_id`, `expires_at`
- **quotas**
  - `id UUID PK`
  - `subject_type ENUM('anon','user','ip')`
  - `subject_id TEXT`
  - `date DATE`
  - `requests_count INT DEFAULT 0`
  - `tokens_count INT DEFAULT 0`
  - `reset_at TIMESTAMPTZ NOT NULL`
  - Unique: `(subject_type, subject_id, date)`
- **rate_limits**
  - `id UUID PK`
  - `subject_type ENUM('anon','user','ip')`
  - `subject_id TEXT`
  - `window_start TIMESTAMPTZ`
  - `window_seconds INT`
  - `hits INT DEFAULT 0`
  - `blocked_until TIMESTAMPTZ NULL`
  - Unique: `(subject_type, subject_id, window_start, window_seconds)`
- **invocation_logs** (minimal telemetry, no prompts/responses)
  - `id UUID PK`
  - `ts TIMESTAMPTZ DEFAULT now()`
  - `session_id UUID NULL`
  - `route TEXT`
  - `status_code INT`
  - `latency_ms INT`
  - `model_used TEXT NULL`
  - `error_code TEXT NULL`
  - `hashed_subject TEXT NULL` (optional)
  - Indexes: `ts`, `session_id`

## Retention & Boundaries
- sessions: expire via `expires_at` (e.g., 7 days).
- invocation_logs: retain max 14 days.
- quotas: retain up to ~90 days (or shorter).
- rate_limits: drop after windows/blocked_until elapse (~30 days).
- Implement cleanup via `cleanup_expired_records()` (best-effort); scheduling to be added later if needed.

## Allowed vs. Forbidden Storage
- Allowed: session identifiers, counters, minimal telemetry (route/status/latency/model/error), hashed subjects.
- Forbidden: raw user text, model prompts/responses, embeddings, PII enrichment, long-term behavioral profiles.

## Supabase / Postgres Connection
- Use `DATABASE_URL` for backend connectivity (Supabase provided).
- Backend defensively degrades if DB missing or psycopg absent; readiness reports degraded instead of crashing.

## Migrations
- Source of truth: `backend/app/db/migrations/001_init.sql`.
- Apply via:
  - `psql "$DATABASE_URL" -f backend/app/db/migrations/001_init.sql`
  - or Supabase SQL editor / Supabase CLI (`supabase db push` with the file added).

## Cleanup Path
- `cleanup_expired_records()` deletes TTL-bounded rows (best-effort).
- Until scheduling exists, ops can call this function manually (e.g., via a management task).

## Future Steps
- Step 3 (Auth): may use `user_id` in sessions/quotas/rate_limits; schema already supports it.
- Step 4 (Quotas): will increment `quotas` and `rate_limits`; no schema change expected.
- Supabase integration for auth/storage will be added later without expanding forbidden areas.

## Locks
- Phase 9–14 cognition logic remains unchanged.
- No additional storage outside the tables and rules defined above.
- Any future persistence must respect TTLs, minimal fields, and forbidden list.

---
### Phase 15 Step 2 Status: COMPLETE ✅
