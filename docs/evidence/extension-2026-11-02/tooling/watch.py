"""Live follower for a ReproPatch operator run: prints harness events and metered spend as they happen."""
import sqlite3, json, sys, time
DB='/workspace/rp-cases-2026-11-02/data/repropatch.sqlite3'
since=sys.argv[1]  # ISO time; follow the first run created after it
TERM={'VERIFIED','REJECTED','NOT_REPRODUCED','BLOCKED','BUDGET_EXCEEDED','ERROR','CANCELLED'}
def q(sql,*a):
    c=sqlite3.connect(DB,timeout=10);c.row_factory=sqlite3.Row
    try:return c.execute(sql,a).fetchall()
    finally:c.close()
rid=None;last=0;t0=time.time()
while rid is None:
    try:
        r=q("SELECT id FROM runs WHERE created_at>=? ORDER BY created_at LIMIT 1",since)
        if r:rid=r[0]['id']
    except sqlite3.OperationalError:pass
    time.sleep(0.5)
print(f"\x1b[1mrun {rid}\x1b[0m",flush=True)
while True:
    for e in q("SELECT * FROM events WHERE run_id=? AND id>? ORDER BY id",rid,last):
        last=e['id'];d=json.loads(e['data'] or '{}')
        spend=q("SELECT COALESCE(SUM(charged),0) s FROM spend WHERE run_id=?",rid)[0]['s']/1e6
        extra=''
        if 'input_tokens' in d:extra=f" in={d.get('input_tokens')} out={d.get('output_tokens')} cached={d.get('cached_tokens')}"
        if d.get('tool'):extra=f" turn {d.get('turn')}: {d['tool']}"+(' (error: '+str(d.get('error_reason'))[:80]+')' if d.get('error') else '')
        if 'confirmed' in d:extra=f" baseline={d['baseline']['outcome']} reference={(d.get('reference') or {}).get('outcome')} confirmed={d['confirmed']}"
        print(f"[{time.time()-t0:6.1f}s] {e['stage']:<12} {e['message'][:70]}{extra}  | metered ${spend:.4f}",flush=True)
    st=q("SELECT status FROM runs WHERE id=?",rid)[0]['status']
    if st in TERM:
        print(f"\x1b[1mFINAL STATUS: {st}\x1b[0m",flush=True);break
    time.sleep(0.4)
