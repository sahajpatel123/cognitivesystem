# Phase 15 — Step 1: Deployment Architecture & Environments (LOCK)

## 1) Deployment Topology
```
           +---------------------+
           |   Vercel (Frontend) |
           |   Next.js app       |
           +----------+----------+
                      |
          HTTPS (public API URL)
                      |
           +----------v----------+
           | Railway (Backend)   |
           | FastAPI + Uvicorn   |
           | start.sh / python3  |
           +----------+----------+
                      |
           +----------v----------+
           |  (Planned) Supabase |
           |  Auth/DB Step 2     |
           +---------------------+
```

- Frontend: deployed on Vercel.
- Backend: deployed on Railway (Nixpacks), served by `python3 -m uvicorn mci_backend.main:app`.
- Supabase: planned for Phase 15 Step 2 (not implemented yet).

## 2) Environments
- **Local/Dev**
  - Frontend: localhost:3000 (Next dev)
  - Backend: localhost:8000 (uvicorn) or Railway preview URL
  - Key env: `CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000`
  - Frontend API base: `NEXT_PUBLIC_BACKEND_URL=http://localhost:8000`

- **Staging (planned)**
  - Frontend: Vercel preview domain
  - Backend: Railway staging service/domain
  - Env: `CORS_ORIGINS` includes Vercel preview domain + localhost
  - Frontend API base: `NEXT_PUBLIC_BACKEND_URL=<railway-staging-url>`

- **Production**
  - Frontend: Vercel production domain (e.g., https://yourapp.vercel.app)
  - Backend: Railway production service (optional custom domain)
  - Env: `CORS_ORIGINS` includes Vercel prod domain (+ localhost for emergency testing if desired)
  - Frontend API base: `NEXT_PUBLIC_BACKEND_URL=https://<railway-backend>.up.railway.app`

## 3) Routing + HTTPS
- Frontend calls backend over public HTTPS using the Railway-provided URL (or custom domain if configured).
- Backend binds `0.0.0.0` on `$PORT` per Railway contract.
- All public traffic is HTTPS-terminated by platform (Vercel/Railway).

## 4) CORS Policy
- Configured via `CORS_ORIGINS` env (comma-separated or JSON list).
  - Local default: `http://localhost:3000,http://127.0.0.1:3000`
  - Production: include the Vercel domain(s), e.g., `https://yourapp.vercel.app`
- Middleware settings:
  - `allow_origins` = parsed `CORS_ORIGINS`
  - `allow_credentials = True`
  - `allow_methods = ["*"]`
  - `allow_headers = ["*"]`
- CORS is deploy-time configuration only; no cognition/business logic changes.

## 5) Railway Service Configuration
- Start command (source of truth):
  - `bash start.sh` (Railway startCommand or Nixpacks `[start] cmd`)
- `start.sh` uses `/usr/bin/env bash`, requires `python3`, and runs:
  - `PYTHONPATH=/app python3 -m uvicorn mci_backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"`
- Nixpacks config: `.nixpacks/nixpacks.toml` installs `python312`, pip, setuptools, wheel, then installs requirements.
- Runtime Python typically at `/opt/venv/bin/python3` (platform-managed).
- Backend exposed publicly on Railway domain; health endpoint `/health` returns OK.

## 6) Vercel Configuration
- Frontend env var: `NEXT_PUBLIC_BACKEND_URL` pointing to Railway backend (no trailing slash preferred).
- Build output: standard Next.js build (`next build`).
- Frontend uses public HTTPS to call backend API.

## 7) Operational Guardrails
- Phases 1–14 cognition logic remain locked/unchanged.
- Secrets only via environment variables; no committed keys.
- Avoid logging user content in production; minimal telemetry only.

## 8) Acceptance Checklist
- `/health` returns OK on Railway backend.
- Frontend can call backend without CORS errors (Vercel → Railway).
- Railway service status: Active/Running.
- Vercel deployment successful (build + runtime).

---
### Phase 15 Step 1 Status: COMPLETE ✅
