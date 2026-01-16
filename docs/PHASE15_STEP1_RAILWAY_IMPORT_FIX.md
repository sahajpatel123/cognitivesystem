# Phase 15 — Step 1: Railway Import Fix for `mci_backend`
Status: LOCKED
Date: 2026-01-16

## Root Cause
Railway deploy ran from `/app/backend` without installing the repo root, so `mci_backend` (at repo root) was not on the Python path. Importing governed modules failed with `ModuleNotFoundError: mci_backend`.

## Fix Summary
- Added repo-level packaging via `pyproject.toml` using setuptools to expose `mci_backend` and `backend` as installable packages.
- Added editable install pointer `-e ..` in `backend/requirements.txt` so Railway installs the repo root when installing backend deps.
- Ensured `mci_backend/__init__.py` exists so the package is discoverable.
- Updated `railway.toml` start command to run from repo root without `cd backend`.

## Required Railway Settings
- **Root directory:** repository root (not `backend`).
- **Start command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT` (as set in `railway.toml`).
- **Builder:** Nixpacks (from `railway.toml`).
- **Env vars:** same as Phase 15 Step 1 (ENV, BACKEND_PUBLIC_BASE_URL, CORS_ORIGINS, MODEL_PROVIDER_API_KEY, DATABASE_URL if used, etc.).

## Redeploy Checklist
1) Ensure service root is repo root.
2) Confirm `railway.toml` present and start command matches above.
3) Install deps via `pip install -r backend/requirements.txt` (which installs repo root via `-e ..`).
4) Redeploy.

## Verification
- Local import checks:
  - `python -c "from mci_backend.decision_assembly import assemble_decision_state; print('ok')"`
  - `python -c "from backend.app.main import app; print('ok')"`
- Runtime endpoints after deploy:
  - `GET /health` → 200
  - `GET /ready` → 200 when envs/DB configured; 503 with missing_env otherwise

## Notes
- No governance semantics changed; this is packaging-only to make imports deterministic in Railway.
