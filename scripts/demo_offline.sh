#!/usr/bin/env bash
# ReproPatch offline demo. No network, no model calls, no API keys.
#  1) re-checks the recorded Meta pilot and the first real repair (hashes + tallies)
#  2) serves the static "replay of a recorded run" page on http://127.0.0.1:8799/
# For a real (free) execution of the workbench itself, run the labeled FIXTURE:
#  see README "Run locally" (scripts/setup.py + scripts/start_local.sh, then "Run W1 fixture").
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== Recorded pilot (8 Meta runs, 27 Oct 2026) + extension (3 more real bugs, 2 Nov 2026), re-checked offline =="
python3 scripts/verify_evidence.py
echo; echo "== Replay of recorded run 909bd13d (VanJS 389) =="
python3 scripts/verify_evidence.py --run 909bd13d
if [[ "${1:-}" == "--serve" ]]; then
  echo; echo "Replay page: http://127.0.0.1:8799/  (Ctrl+C to stop)"
  cd docs/replay && exec python3 -m http.server 8799 --bind 127.0.0.1
fi
