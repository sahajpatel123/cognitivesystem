# Phase 15 — Step 1: Railway Railpack/Nixpacks Fix
Status: LOCKED
Date: 2026-01-15

## Purpose
Resolve Railway buildpack detection issues in a monorepo and force the backend (FastAPI) to build/run with Nixpacks only. Avoids accidental frontend/monorepo auto-detection and ensures predictable start/health behavior.

## Required Railway Service Settings
- **Root Directory:** repository root (not `backend`)
- **Builder:** Nixpacks (forced via `railway.toml`)
- **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- **Healthcheck Path:** `/health`
- **Restart Policy:** ON_FAILURE

## Environment Variables (minimum for readiness)
- `ENV=production`
- `BACKEND_PUBLIC_BASE_URL=https://<your-backend-domain>`
- `CORS_ORIGINS=https://<your-frontend-domain>` (comma-separated; no wildcard)
- `MODEL_PROVIDER_API_KEY=<provider-key>`
- `DATABASE_URL=<postgres-connection-string>` (if using Supabase Postgres)
- Optional: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `MODEL_PROVIDER_BASE_URL`, `LOG_LEVEL`

## Common Failure Modes + Fixes
- **Build picks wrong workspace / fails to find app:** Ensure Root Directory is `backend` and `railway.toml` is present at repo root.
- **Port binding errors:** Use provided start command; it binds `0.0.0.0` and `$PORT`.
- **CORS blocked:** Set `CORS_ORIGINS` explicitly (no `*` in production).
- **Ready endpoint returns 503:** Missing required envs or DB unreachable; set envs and ensure DB URL reachable.
- **Python version mismatch:** `backend/runtime.txt` pins `python-3.11.8` for Nixpacks.

## Verification Checklist
1) Deploy Railway backend with settings above.
2) From a terminal (replace host):
   - `curl -f https://<host>/health` → 200 and status "ok"
   - `curl -f https://<host>/ready` → 200 when envs set; 503 lists missing_env otherwise
3) From frontend (Vercel) ensure `NEXT_PUBLIC_API_BASE_URL` points to backend; UI should operate normally.

## Notes
- No governed cognition logic changed; this is deployment-only hardening.
- Keep `.env` out of git; use `env.example` for reference.
