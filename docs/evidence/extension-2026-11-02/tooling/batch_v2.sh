#!/bin/bash
# Batch v2 (2 Nov 2026 evening): 2 new real VanJS bugs x W0/W1, recorded as terminal casts. Caps from env.sh ($3/run, $8/batch ledger).
cd /workspace/rp-cases-2026-11-02
for RUN in "vanx-replace-c93 W0" "vanx-replace-c93 W1" "vanx-funcfield-5d9 W1" "vanx-funcfield-5d9 W0"; do
 set -- $RUN
 /tmp/cast-venv/bin/asciinema rec -q --overwrite --cols 130 --rows 36 -c "./live_run_v2.sh $1 $2" live-capture/live-run-$1-$2.cast
 echo "DONE $1 $2"
done
sudo chown -R box:box data runs live-capture
echo BATCH_DONE
