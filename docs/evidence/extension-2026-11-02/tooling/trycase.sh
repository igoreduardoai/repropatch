#!/bin/bash
# trycase.sh CASE FIXSHA FILES... : runs public/check against pre-fix and fix trees in the sandbox image (no network)
C=$1; FIX=$2; shift 2; R=/workspace/rp-cases-2026-11-02; T=/tmp/try-$C; rm -rf $T.bak 2>/dev/null; [ -d $T ] && mv $T $T.bak-$(date +%s)
for rev in $FIX^ $FIX; do tag=$([ "$rev" = "$FIX" ] && echo fix || echo base); d=$T/$tag; mkdir -p $d/tests
 for f in "$@"; do mkdir -p $d/$(dirname $f); git -C $R/van-src show $rev:$f > $d/$f; done
 cp $R/spec/$C/demo.mjs $d/; cp $R/spec/$C/public.cjs $d/tests/; cp $R/spec/$C/check.cjs $d/tests/check.cjs
 for t in public check; do echo -n "$tag $t: "; sudo docker run --rm --network=none -v $d:/workspace/repo:ro -w /workspace/repo repropatch-browser:pilot-v4 node /opt/repropatch/run-test.cjs /workspace/repo/tests/$t.cjs 2>&1 | tail -2 | tr '\n' ' '; echo " exit=${PIPESTATUS[0]}"; done; done
