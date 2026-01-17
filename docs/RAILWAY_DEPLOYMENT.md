# Railway Deployment (Backend)

## Correct root directory
Use the repository root as the working directory (`/app` on Railway). The `backend/` package must be present directly under this root; placing the app under a nested `/backend` root or using a different working directory will prevent Python from importing `backend`.

## Start command
```
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

## Why `/backend` root breaks imports
If the build or runtime working directory is set to `/backend` (or the project is uploaded with `/backend` as the root), the `backend` package itself will not be importable because Python expects `backend/` to be under the working directory. This leads to `ModuleNotFoundError: No module named 'backend'`.

## mci_backend wrapper
`mci_backend/main.py` is a thin wrapper that imports and exposes the FastAPI `app` from `backend.app.main`. Ensure the working directory remains the repository root so that both `backend` and `mci_backend` are importable.
