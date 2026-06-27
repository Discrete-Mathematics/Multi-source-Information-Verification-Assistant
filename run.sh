#!/usr/bin/env bash
# One-click local launch: build the front-end (if needed) and start the API
# that also serves the built SPA.  Requires: python3, and node/npm for the
# first front-end build (a pre-built dist/ is committed, so node is optional).
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "⚠️  ANTHROPIC_API_KEY 未设置 —— 核验功能需要它。"
  echo "   export ANTHROPIC_API_KEY=... ; 可选 ANTHROPIC_BASE_URL / ANTHROPIC_MODEL"
fi

# --- front-end ---
if [[ ! -d frontend/dist ]]; then
  if command -v npm >/dev/null 2>&1; then
    echo "▶ building front-end…"
    (cd frontend && npm install && npm run build)
  else
    echo "⚠️  无 npm 且无 frontend/dist,前端将不可用(API 仍可用)。"
  fi
fi

# --- back-end ---
cd backend
if [[ ! -d .venv ]]; then
  echo "▶ creating venv & installing deps…"
  python3 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
fi

echo "▶ starting on http://${HOST}:${PORT}"
exec ./.venv/bin/uvicorn app.main:app --host "$HOST" --port "$PORT"
