# backend/app/db – Phase 15 Step 2

## Overview
This package contains the bounded persistence layer for Supabase Postgres, including:
- Connection helpers (`database.py`) with fail-closed health checks.
- TTL cleanup helper (`cleanup_expired_records`).
- SQL migrations (`migrations/001_init.sql`) defining minimal, bounded tables.

## Migrations
The schema is defined in `migrations/001_init.sql`. Apply using psql (or Supabase SQL editor):
```bash
psql "$DATABASE_URL" -f backend/app/db/migrations/001_init.sql
```

If using Supabase CLI:
```bash
supabase db push  # with migration file added
```

## Tables (summary)
- `sessions`: minimal session identity with `expires_at` TTL.
- `quotas`: per-subject daily counters (unique by subject_type+id+date).
- `rate_limits`: windowed hit tracking with optional `blocked_until`.
- `invocation_logs`: minimal request telemetry (no prompts/responses).

## Cleanup / retention
- Use `cleanup_expired_records()` for best-effort TTL deletions.
- Planned retention: sessions TTL; invocation_logs ~14d; quotas ~90d; rate_limits when windows expire.

## Health checks
`check_db_connection()` returns `(ok, reason)` without leaking credentials; safe to call in readiness probes. If `DATABASE_URL` or psycopg is missing, it returns a degraded status instead of crashing.

## Postgres enum creation note
Postgres (including Supabase) does not support `CREATE TYPE IF NOT EXISTS`. Enums in `001_init.sql` are created via guarded `DO $$ ... IF NOT EXISTS ... END $$;` blocks to keep migrations idempotent in Supabase SQL Editor.
