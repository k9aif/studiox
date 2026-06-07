#!/usr/bin/env bash
# k9x_studio launcher

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Shared venv (k9-aif-framework) ───────────────────────────
VENV_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)/k9-aif-framework/.venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "[k9x_studio] ERROR: shared venv not found at $VENV_DIR"
  echo "  Run: cd ../../k9-aif-framework && python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

source "$VENV_DIR/bin/activate"

echo "[k9x_studio] Using shared venv: $VENV_DIR"
echo "[k9x_studio] Installing k9x_studio backend dependencies..."
pip install -q -r requirements.txt

# ── Frontend deps ─────────────────────────────────────────────
if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
  echo "[k9x_studio] Installing frontend dependencies..."
  cd "$SCRIPT_DIR/frontend" && npm install
  cd "$SCRIPT_DIR"
fi

# ── Start backend ─────────────────────────────────────────────
echo "[k9x_studio] Starting backend on http://localhost:8090"
cd "$SCRIPT_DIR"
uvicorn backend.main:app --host 0.0.0.0 --port 8090 --reload &
BACKEND_PID=$!

# ── Start frontend ────────────────────────────────────────────
echo "[k9x_studio] Starting frontend on http://localhost:5173"
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "  k9x_studio running:"
echo "  Frontend → http://localhost:5173"
echo "  Backend  → http://localhost:8090"
echo ""
echo "  Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait
