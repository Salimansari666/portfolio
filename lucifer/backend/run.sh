#!/usr/bin/env bash
set -euo pipefail

# Run the backend with uvicorn
UVicorn_CMD="uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "Starting backend: $UVicorn_CMD"
exec $UVicorn_CMD
