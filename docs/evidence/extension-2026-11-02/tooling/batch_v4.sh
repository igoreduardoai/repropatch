#!/bin/bash
# Round 2 (2 Nov 2026, t306u): 4 new real VanJS bugs x W1/W0, recorded as terminal casts.
# Ledger-enforced cap for the round: total ledger <= $6.47 (= $2.473885 before + $4.00). $3/run cap still applies.
cd /workspace/rp-cases-2026-11-02
for RUN in "vanx-poplen-fc3 W1" "vanx-poplen-fc3 W0" "vanx-replacelen-acb W1" "vanx-replacelen-acb W0" "vanx-proxyarg-1c5 W1" "vanx-proxyarg-1c5 W0" "van-propgc-84f W1" "van-propgc-84f W0"; do
 set -- $RUN
 T=$(python3 -c "import sqlite3;print(sqlite3.connect('data/repropatch.sqlite3').execute('select coalesce(sum(charged),0) from spend').fetchone()[0]/1e6)")
 if python3 -c "import sys;sys.exit(0 if $T>=6.2 else 1)"; then echo "STOP: ledger total \$$T near round cap"; break; fi
 /tmp/cast-venv/bin/asciinema rec -q --overwrite --cols 130 --rows 36 -c "./live_run_v3.sh $1 $2" live-capture/live-run-$1-$2.cast
 echo "DONE $1 $2 ledger_before=\$$T"
done
sudo chown -R box:box data runs live-capture
echo BATCH_DONE
