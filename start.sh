#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

python3 -V
python3 -m pip -V

if ! python3 -c "import uvicorn" >/dev/null 2>&1; then
  echo "uvicorn missing; installing backend requirements"
  python3 -m pip install --upgrade pip
  python3 -m pip install -r backend/requirements.txt
  python3 -c "import uvicorn; print('uvicorn_ok')"
else
  echo "uvicorn_ok (cached)"
fi

echo "python3 location:"
command -v python3 || (echo "python3 not found in PATH" && exit 1)

export PYTHONPATH=/app
exec python3 -m uvicorn mci_backend.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips "100.64.0.0/10"
