"""Export verified, sanitized pilot evidence; never calls a model or reruns tests."""
import json,hashlib,shutil
from decimal import Decimal,ROUND_CEILING
from pathlib import Path
from repropatch.config import Settings,ROOT
from repropatch.store import Store
from repropatch.cases import Registry,tree_files,tree_hash
from repropatch.gateway import split_patch,apply_unified_diff
from repropatch.budget import Budget

def main():
    settings=Settings.load();store=Store(settings.db_path);reg=Registry(settings.cases_root,settings.acceptance_key)
    execution=json.loads((settings.data_dir/'pilot-execution.json').read_text());plan=execution['protocol'];attempts=execution['runs']
    if len(attempts)!=len(plan['order']):raise SystemExit('Pilot incomplete: preserve attempts, do not infer missing results')
    out=settings.data_dir/'release';out.mkdir(exist_ok=True);rows=[];total=0
    for item,expected in zip(attempts,plan['order']):
        row=store.get(item['run_id']);res=row['result'];case=reg.load(row['case_id'])
        assert (row['case_id'],row['method'])==(expected['case_id'],expected['method'])
        assert case.manifest_sha256==expected['manifest_sha256']
        assert reg.acceptance_status(case)['accepted']
        usage=[e['data'] for e in store.events(row['id']) if 'response_id' in e['data']]
        micro=0
        for u in usage:
            micro+=int((Decimal(u['input_tokens']-u['cached_tokens'])*4+Decimal(u['cached_tokens'])*Decimal('.20')+Decimal(u['output_tokens'])*20).to_integral_value(rounding=ROUND_CEILING))
        spend=Budget(settings.db_path).run_spend(row['id']);assert spend['unknown_calls']==0
        assert micro==round(spend['settled_usd']*1_000_000),'Usage/ledger mismatch'
        assert spend['settled_usd']<=3;total+=micro
        rows.append({'run_id':row['id'],'case_id':case.case_id,'method':row['method'],'status':row['status'],
          'model_calls':spend['model_calls'],'metered_cost_usd':spend['settled_usd'],'duration_ms':res['duration_ms'],
          'frozen_test_sha256':res.get('frozen_test_sha256'),'candidate_sha256':res.get('candidate_sha256'),
          'patch_sha256':res.get('patch_sha256'),'false_success':res.get('false_success',False),
          'regressions':res.get('regressions',0),'operator_interventions':res.get('operator_interventions',0),
          'reason':res.get('reason'),'evaluation':res.get('evaluation'),'response_usage':usage})
    assert total<=24_000_000
    report={'protocol':plan,'runs':rows,'metered_cost_usd':total/1_000_000,'account_invoice_verified':False,
      'usage_reconciled_to_ledger':True,'fixtures_excluded':True,'limitations':['Four selected bugs from one library, not a general repair benchmark','Operator-authored independent checks, not maintainer tests','No observed tie proves equivalence or superiority','Browser tools return text to the model; screenshots are stored as evidence']}
    (out/'pilot-results.json').write_text(json.dumps(report,indent=2))
    first=next((r for r in rows if r['status']=='VERIFIED' and r['frozen_test_sha256']),None)
    if not first:raise SystemExit('No complete verified repair to export')
    original=store.get(first['run_id']);case=reg.load(first['case_id']);dest=out/'first-live';dest.mkdir(exist_ok=True)
    for artifact in store.artifacts(first['run_id']):
        if artifact['name'] not in {'repair.patch','reproduction.frozen.cjs','browser-01.png','evaluator.log'}:continue
        src=Path(artifact['path']);body=src.read_bytes();assert hashlib.sha256(body).hexdigest()==artifact['sha256'];(dest/artifact['name']).write_bytes(body)
    patch=(dest/'repair.patch').read_text();candidate=tree_files(case.snapshot_dir)
    for path,diff,new in split_patch(patch):candidate[path]=apply_unified_diff(None if new else candidate[path].decode(),diff,path).encode()
    assert tree_hash(candidate)==first['candidate_sha256'],'Candidate reconstructed from patch differs'
    private=settings.data_dir/'candidate-replay';private.mkdir(exist_ok=True)
    for name,body in candidate.items():
        p=private/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
    video=settings.data_dir/'preparation'/case.case_id/'recording/reproduction.mp4'
    assert hashlib.sha256(video.read_bytes()).hexdigest()==case.video_sha256
    shutil.copyfile(video,dest/'reported-bug.mp4');shutil.copyfile(case.snapshot_dir/'LICENSE',dest/'VanJS-LICENSE')
    (dest/'report.json').write_text(json.dumps({**first,'repository':case.repository_url,'base_commit':case.base_commit,'video_origin':case.video_origin,'video_sha256':case.video_sha256,'candidate_reconstructed_and_hash_verified':True},indent=2))
    shutil.copyfile(settings.data_dir/'case-provenance-public.json',out/'case-provenance.json')
    print(json.dumps({'attempts':len(rows),'metered_cost_usd':report['metered_cost_usd'],'first_repair':first['run_id'],'output':str(out)}))
if __name__=='__main__':main()
