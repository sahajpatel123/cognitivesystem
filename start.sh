#!/bin/bash
set -e

echo "PWD: $(pwd)"
echo "Listing /app:"
ls -la /app || true

echo "Listing current directory:"
ls -la

echo "Find backend folder:"
find /app -maxdepth 4 -type d -name "backend" || true

echo "Python sys.path:"
python -c "import sys; print('\n'.join(sys.path))"

echo "Starting uvicorn..."
PYTHONPATH=/app uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}
