#!/bin/bash
# One LIVE ReproPatch run: real Meta muse-wonder-1.0 calls, metered and capped.
CASE=$1; METHOD=${2:-W1}
source /workspace/rp-cases-2026-11-02/env.sh
cd /workspace/rp-cases-2026-11-02/app
echo -e "\x1b[1mReproPatch LIVE run  $(TZ=America/Chicago date '+%Y-%m-%d %H:%M %Z')\x1b[0m"
echo "case=$CASE  method=$METHOD  model=muse-wonder-1.0  caps: \$${REPROPATCH_RUN_CAP_USD}/run, \$${REPROPATCH_BATCH_CAP_USD}/batch"
echo "bug video sha256: $(sha256sum ../videos/$CASE.mp4 | cut -c1-16)...  (independently recorded reproduction)"
$PY -m repropatch.opscli cases | sed 's/^/accepted case: /'
SINCE=$(python3 -c "from datetime import datetime,timezone;print(datetime.now(timezone.utc).isoformat())")
$PY -m repropatch.opscli run --case $CASE --method $METHOD --video ../videos/$CASE.mp4 --approve-paid-run > ../runs/$CASE-$METHOD.out 2>&1 &
P=$!
python3 ../watch.py "$SINCE"
wait $P; echo "opscli exit=$?"; cat ../runs/$CASE-$METHOD.out | tail -3
