# Phase 15 — Step 1: Production Deployment Readiness
Status: DRAFT
Date: 2026-01-15

## Purpose
Make the repo deployable to Railway (backend) + Vercel (frontend) + Supabase (Postgres) without changing governed semantics. Ensure fail-closed posture, explicit envs, safe CORS, health/readiness, and minimal operational persistence.

## Stack Targets
- Backend: FastAPI on Railway
- Frontend: Next.js on Vercel (renderer-only)
- Database: Supabase Postgres (operational metadata only; not memory/personalization)

## Environment Variables
Backend (Railway):
- ENV=development|production
- BACKEND_PUBLIC_BASE_URL
- CORS_ORIGINS (comma list; no wildcard in prod)
- SUPABASE_URL
- SUPABASE_ANON_KEY
- SUPABASE_SERVICE_ROLE_KEY (server only)
- DATABASE_URL (direct Postgres URL; optional but required if DB used)
- MODEL_PROVIDER_API_KEY
- MODEL_PROVIDER_BASE_URL (optional)
- LOG_LEVEL
- LLM_REASONING_MODEL (optional override)
- LLM_EXPRESSION_MODEL (optional override)

Frontend (Vercel):
- NEXT_PUBLIC_API_BASE_URL
- NEXT_PUBLIC_ENV

See `env.example` for defaults.

## Supabase Setup
1) Create Supabase project; obtain `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`.
2) Create a Postgres connection string and set `DATABASE_URL` (or use the generated one).
3) Apply migration `backend/migrations/0001_init.sql` (via psql or Supabase SQL editor).
4) Enforce RLS as needed; ensure least-privilege service role for server use.

## Railway Backend Deploy
1) Create Railway service from `backend`.
2) Set env vars above (ENV=production, BACKEND_PUBLIC_BASE_URL=https://<your-backend>, CORS_ORIGINS=https://<your-frontend>). No wildcards in prod.
3) Install dependencies (includes `psycopg[binary]`).
4) Expose port 8000 (or Railway default) and run `PYTHONPATH=/app uvicorn app.main:app --host 0.0.0.0 --port $PORT` (root directory set to `backend`). PYTHONPATH=/app is required so `mci_backend` (at repo root) is importable when service runs inside `/app/backend`.
5) Validate `/health` and `/ready` (expect 200 when configured; 503 if missing critical env/DB).

## Vercel Frontend Deploy
1) Set `NEXT_PUBLIC_API_BASE_URL=https://<your-backend>` and `NEXT_PUBLIC_ENV=production`.
2) Deploy as standard Next.js app.
3) Verify chat page uses configured API base and shows no dev banner in production.

## CORS & Networking
- Production: only configured origins allowed; wildcard disallowed.
- Development: localhost origins permitted when CORS_ORIGINS unset.
- No history or metadata is sent from UI beyond governed contract.

## Database Constraints (Operational Only)
- Tables: `sessions`, `requests` per `backend/migrations/0001_init.sql`.
- No storage of raw user text, model output, governed internals, or personalization artifacts.
- DB must not influence cognition; used only for quotas/TTL/operational metadata.
- Retention TTLs must be applied; no indefinite logs by default.

## Monitoring & Telemetry
- Allowed: categorical outcomes (accepted/refused/aborted), action counts, error category counts.
- Forbidden: raw prompts/responses, reasoning logs, adaptive feedback into cognition.

## Smoke Test Checklist
- GET /health → 200 {status:"ok"}
- GET /ready → 200 when envs set; 503 with missing envs in prod
- POST /api/chat → returns governed response; internal exceptions are sanitized
- Frontend chat → end-to-end succeeds using configured API base

## Security Checks Before Release
- No `.env` files committed; secrets only in runtime env
- Determinism snapshots unchanged
- Phase 14 backend fast + UI phase14 + Phase 13 UI abuse + Phase 12 abuse suites passing
- CORS restricted to production origin(s)
- No raw logging of user_text or model output

## Rollback Plan (Minimum)
- Keep previous deployment image
- Retain previous DB schema; avoid destructive migrations without backups
- If readiness fails, rollback to last known good tag
