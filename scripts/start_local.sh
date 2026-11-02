#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -x .venv/bin/python ]]; then PYTHON=.venv/bin/python; else PYTHON=python3; fi
[[ -f .env ]] || "$PYTHON" scripts/setup.py
"$PYTHON" -m repropatch.worker &
WORKER=$!
trap 'kill "$WORKER" 2>/dev/null || true' EXIT INT TERM
"$PYTHON" -m uvicorn repropatch.api:app --host 127.0.0.1 --port 8000
