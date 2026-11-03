"""Export the 2 Nov 2026 extension runs (batches 1-4) (real Meta calls) as sanitized evidence. No model calls."""
import json,hashlib,shutil,csv,sys
from decimal import Decimal,ROUND_CEILING
from pathlib import Path
sys.path.insert(0,'/workspace/rp-cases-2026-11-02/app')
from repropatch.config import Settings
from repropatch.store import Store
from repropatch.cases import Registry,tree_files,tree_hash
from repropatch.gateway import split_patch,apply_unified_diff
from repropatch.budget import Budget
INVALID={'van-setter-161':'Excluded: our public regression test was wrong (it also failed on the upstream fix: style serializes as "color: red;"). Fixed and re-run as van-setter-161-v2.'}
UPSTREAM={'vanx-truncate-915':'915f0e2c47cb6ca72f90e567fdc2dfc731d72df0','van-setter-161':'52a3696e386956439130fc4041cf97ce96756316',
          'van-setter-161-v2':'52a3696e386956439130fc4041cf97ce96756316','vanx-compact-063':'c9f2dd48cbb5f8b4a0b053d68cdbeec01127a7c3','vanx-replace-c93':'c93a1531ab6b7bcb17492881966799b963c8fe22','vanx-funcfield-5d9':'5d97cffc31b912700ef1ce7dfe98fa42c68b9e9b','vanx-raw-356':'17d5ce5eae691f9839b68454154d03a293a51368',
          'vanx-poplen-fc3':'fc3ee4c4bdab9f0a065ff6d897c53f2fa8f85eeb','vanx-replacelen-acb':'acb8ba839a28b53ef0e4cf9be0cf086df0a56ca6','vanx-proxyarg-1c5':'1c580f0a6598ddcff62b005e742a7d5e9fe4eaf7','van-propgc-84f':'84f30ae917107c9d4b4c38b9969a0d56aaac5ac8'}
s=Settings.load();store=Store(s.db_path);reg=Registry(s.cases_root,s.acceptance_key)
out=Path('/workspace/rp-cases-2026-11-02/export/extension-2026-11-02');out.mkdir(parents=True,exist_ok=True)
import sqlite3
con=sqlite3.connect(s.db_path);ids=[r[0] for r in con.execute("select id from runs order by created_at")]
rows=[];total=0;calls_csv=[]
for rid in ids:
    row=store.get(rid);res=row['result'];case=reg.load(row['case_id']);assert reg.acceptance_status(case)['accepted']
    usage=[e['data'] for e in store.events(rid) if 'response_id' in e['data']]
    micro=0
    for u in usage:
        m=int((Decimal(u['input_tokens']-u['cached_tokens'])*4+Decimal(u['cached_tokens'])*Decimal('.20')+Decimal(u['output_tokens'])*20).to_integral_value(rounding=ROUND_CEILING))
        micro+=m;calls_csv.append([rid,row['case_id'],row['method'],u['turn'],u['response_id'],u['input_tokens'],u['cached_tokens'],u['output_tokens'],f"{m/1e6:.6f}"])
    spend=Budget(s.db_path).run_spend(rid);assert spend['unknown_calls']==0
    assert micro==round(spend['settled_usd']*1_000_000),('Usage/ledger mismatch',rid)
    total+=micro
    d=out/'runs'/rid;d.mkdir(parents=True,exist_ok=True);art={}
    for a in store.artifacts(rid):
        if a['name'] not in {'repair.patch','reproduction.frozen.cjs','evaluator.log','report.json','attempt-summary.json'}:continue
        body=Path(a['path']).read_bytes();assert hashlib.sha256(body).hexdigest()==a['sha256'];(d/a['name']).write_bytes(body);art[a['name']]=a['sha256']
    rebuilt=None
    if res.get('candidate_sha256') and (d/'repair.patch').exists():
        cand=tree_files(case.snapshot_dir)
        for path,diff,new in split_patch((d/'repair.patch').read_text()):cand[path]=apply_unified_diff(None if new else cand[path].decode(),diff,path).encode()
        rebuilt=tree_hash(cand)==res['candidate_sha256'];assert rebuilt
    ev=res.get('evaluation') or {}
    rows.append({'run_id':rid,'case_id':case.case_id,'method':row['method'],'status':row['status'],
      'counted':case.case_id not in INVALID,'exclusion_reason':INVALID.get(case.case_id),
      'model_calls':spend['model_calls'],'metered_cost_usd':spend['settled_usd'],'duration_ms':res.get('duration_ms'),
      'reason':res.get('reason'),'frozen_test_sha256':res.get('frozen_test_sha256'),'candidate_sha256':res.get('candidate_sha256'),
      'patch_sha256':res.get('patch_sha256'),'candidate_rebuilt_from_patch':rebuilt,'false_success':res.get('false_success',False),
      'evaluation':{k:v for k,v in ev.items() if k!='log'},'artifact_sha256':art,'response_usage':usage})
prov=[]
for cid in reg.ids():
    c=reg.load(cid);h=reg.hashes(c)
    vid=Path('/workspace/rp-cases-2026-11-02/videos')/(cid+'.mp4');assert hashlib.sha256(vid.read_bytes()).hexdigest()==c.video_sha256
    shutil.copyfile(vid,out/f'bug-video-{cid}.mp4')
    prov.append({**c.public(),'upstream_fix_commit':UPSTREAM[cid],'editable_paths':list(c.editable_paths),'video_sha256':c.video_sha256,
      'sandbox_image_id':c.image_id,**h,'accepted':True,'counted':cid not in INVALID,
      'independent_check_author':'Adapted by the ReproPatch operator from the upstream VanJS tests added in the fix commit (MIT); not run by maintainers'})
with open(out/'spend-log-per-call.csv','w',newline='') as f:
    w=csv.writer(f);w.writerow(['run_id','case_id','method','turn','response_id','input_tokens','cached_tokens','output_tokens','metered_usd']);w.writerows(calls_csv)
counted=[r for r in rows if r['counted']]
cases={}
for r in counted:cases.setdefault(r['case_id'],[]).append(r['status'])
summary={'date':'2026-11-02','model':'muse-wonder-1.0','runs_total':len(rows),'runs_counted':len(counted),
  'cases_counted':len(cases),'cases_verified':sorted(k for k,v in cases.items() if 'VERIFIED' in v),
  'false_success':sum(1 for r in rows if r['false_success']),
  'candidates_rejected_by_independent_check':sum(1 for r in counted if r['status']=='REJECTED' and r['candidate_sha256']),
  'runs_without_candidate':sum(1 for r in counted if not r['candidate_sha256']),
  'metered_cost_usd_all_runs':total/1e6,'metered_cost_usd_counted_runs':sum(r['metered_cost_usd'] for r in counted),
  'model_calls_all_runs':len(calls_csv),'usage_reconciled_to_ledger':True,'account_invoice_verified':False,
  'pricing':'muse-wonder-1.0 standard: $4/M input, $0.20/M cached, $20/M output (dev.meta.ai/docs/pricing-rate-limits, read 2 Nov 2026)'}
(out/'extension-results.json').write_text(json.dumps({'summary':summary,'runs':rows},indent=2))
(out/'case-provenance-extension.json').write_text(json.dumps(prov,indent=2))
print(json.dumps(summary,indent=1))
