#!/usr/bin/env bash
set -euo pipefail

echo "python3 location:"
command -v python3 || (echo "python3 not found in PATH" && exit 1)

export PYTHONPATH=/app
exec python3 -m uvicorn mci_backend.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips "100.64.0.0/10"
