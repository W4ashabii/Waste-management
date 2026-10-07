#!/usr/bin/env bash
# Run the model service, backend and Next.js frontend locally (no Docker).
# Requires: uv (https://docs.astral.sh/uv/) and Node.js.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
WEB="${WEB_DIR:-$ROOT/../waste-management-website}"

for port in 8001 8000 3000; do
  if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Port $port is already in use." >&2
    exit 1
  fi
done

setup_venv() {
  (cd "$1" && [ -d .venv ] || uv venv -q -p 3.12 .venv)
  uv pip install -q -p "$1/.venv/bin/python" "${@:2}"
}

echo "Installing model service (first run downloads torch)..."
setup_venv "$ROOT/model-service" -r "$ROOT/model-service/requirements.txt" torch torchvision
echo "Installing backend..."
setup_venv "$ROOT/backend" -r "$ROOT/backend/requirements.txt"
echo "Installing frontend..."
(cd "$WEB" && [ -d node_modules ] || npm install --silent)

pids=()
cleanup() { kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

(cd "$ROOT/model-service" && YOLO_AUTOINSTALL=false .venv/bin/python -m uvicorn app.main:app --port 8001) &
pids+=($!)
(cd "$ROOT/backend" && MODEL_SERVICE_URL=http://localhost:8001 .venv/bin/python -m uvicorn app.main:app --port 8000) &
pids+=($!)
(cd "$WEB" && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev) &
pids+=($!)

cat <<MSG

  Frontend:       http://localhost:3000   (KMC: /kmc, Ward: /ward)
  Backend API:    http://localhost:8000/docs
  Model service:  http://localhost:8001/health

  Demo logins (password demo1234):
    KMC portal   anita.shrestha@kathmandu.gov.np
    Ward portal  ward17@kathmandu.gov.np

  Ctrl+C stops everything.
MSG
wait
