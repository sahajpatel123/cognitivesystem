# Local Development Guide

## Frontend (Next.js) — directory: `frontend/`
1) Install deps:
   ```bash
   cd frontend
   npm install
   ```
2) Run dev server:
   ```bash
   npm run dev
   ```
3) Connect to local backend:
   - Create `frontend/.env.local` with:
     ```
     NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
     ```
4) Notes:
   - Production/staging env vars are configured in Vercel/Railway; do not hardcode secrets locally.
   - This is for local DX only; does not change cognition or runtime behavior.

## Backend (FastAPI) — directory: `backend/`
1) Setup venv and install:
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2) Run locally (port 8000):
   ```bash
   uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
   ```
3) Notes:
   - Keep Phase 15/16 locks: no cognition changes, no prompt logging.
   - Use local env vars for testing; production/staging settings remain in their platforms.
