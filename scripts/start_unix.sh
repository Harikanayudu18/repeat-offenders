#!/usr/bin/env bash
# Start the API (127.0.0.1:8000) and the Vite dev server (http://localhost:5173).
set -euo pipefail
cd "$(dirname "$0")/.."

export RO_DB="${RO_DB:-./repeat_offenders.db}"
uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT

cd frontend
npm install
npm run dev
