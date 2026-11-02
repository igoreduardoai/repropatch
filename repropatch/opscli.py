"""Operator CLI for gated P0 execution. Not exposed through the API.

  python -m repropatch.opscli cases
  python -m repropatch.opscli accept --case ID            # sandbox evidence, no model call
  python -m repropatch.opscli run --case ID --method W1 --video /path.mp4 --approve-paid-run
  python -m repropatch.opscli sweep

`run` is the only command that can spend; it needs acceptance evidence, the Meta
key in the operator environment (never in the repo) and an explicit flag.
"""
import argparse
import fcntl
import hashlib
import json
import sys
import uuid
from pathlib import Path
from .cases import CaseError,Registry,sign_acceptance
from .config import Settings
from .docker_runtime import DockerRuntime
from .live import run_live
from .security import sha256
from .store import Store,now
from .verify import classify,fresh_run
from .cases import tree_files

def accept_case(runtime,registry:Registry,case,smoke=True)->dict:
    """Produce signed acceptance evidence by actually exercising the sandbox."""
    if not registry.key:raise CaseError('REPROPATCH_ACCEPTANCE_KEY is required to sign evidence')
    run_id='accept-'+uuid.uuid4().hex[:8]
    local=runtime.image_id(case.image_id)
    if local!=case.image_id:raise CaseError('local image ID differs from manifest')
    base=tree_files(case.snapshot_dir);ref=tree_files(case.reference_dir)
    ev={f'{case.evaluator_dest}/{n}':b for n,b in tree_files(case.evaluator_dir).items()}
    before=fresh_run(runtime,case,run_id,'accept-base',{**base,**ev},case.evaluator_argv)
    after=fresh_run(runtime,case,run_id,'accept-ref',{**ref,**ev},case.evaluator_argv)
    fails_before=classify(case,before)['outcome']=='ASSERTION_FAILED'
    passes_ref=classify(case,after)['outcome']=='PASS'
    browser=False
    if smoke and case.serve_argv:
        c=runtime.new_container(case.image_id,run_id,'accept-browser').start()
        try:
            c.put('/workspace',{'repo/'+n:b for n,b in base.items()});c.open_dispatcher()
            c.call({'op':'serve_start','id':1,'argv':list(case.serve_argv),'url':case.serve_url,
                    'ready_timeout_s':case.serve_ready_s},timeout=case.serve_ready_s+15)
            r=c.call({'op':'observe','id':2},timeout=60)
            browser=bool(r.get('ok') and str(r['result'].get('screenshot_b64','')).startswith('iVBOR'))
        finally:c.remove()
    runtime.sweep(run_id)
    evidence={'schema_version':1,'case_id':case.case_id,'sandbox_image_id':case.image_id,
        **registry.hashes(case),'independent_fails_before':fails_before,'independent_exit_before':before['exit_code'],
        'independent_passes_reference':passes_ref,'independent_exit_reference':after['exit_code'],
        'browser_smoke':browser,'executed_at':now()}
    signed=sign_acceptance(evidence,registry.key)
    case.acceptance_path.write_text(json.dumps(signed,indent=2,sort_keys=True))
    return signed

def operator_run(settings,registry,case_id,method,video:Path,runtime=None):
    store=Store(settings.db_path)
    lock=(settings.data_dir/'worker.lock').open('w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise SystemExit('A worker is active; stop it first (one execution at a time).')
    from .budget import Budget
    Budget(settings.db_path,settings.live_budget_usd,settings.run_budget_usd).recover_inflight()
    case=registry.load(case_id)
    body=video.read_bytes();digest=hashlib.sha256(body).hexdigest()
    uid=uuid.uuid4().hex;dest=settings.data_dir/'uploads';dest.mkdir(parents=True,exist_ok=True)
    (dest/(uid+'.mp4')).write_bytes(body)
    with store.connection() as c:
        c.execute('INSERT INTO uploads VALUES(?,?,?,?,?,?)',(uid,str(dest/(uid+'.mp4')),video.name,len(body),digest,now()))
    payload={'case_id':case_id,'method':method,'mode':'live','title':case.title,
             'expected_behavior':case.expected_behavior,'video_id':uid}
    run=store.create(payload,'op-'+uuid.uuid4().hex[:16])
    store.transition(run['id'],'PREFLIGHT','Operator CLI claimed the run.')
    run=store.get(run['id'])
    run_live(store,settings,run,runtime=runtime,registry=registry)
    return store.get(run['id'])

def main(argv=None):
    p=argparse.ArgumentParser(prog='repropatch.opscli')
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('cases');sub.add_parser('sweep')
    a=sub.add_parser('accept');a.add_argument('--case',required=True)
    r=sub.add_parser('run');r.add_argument('--case',required=True);r.add_argument('--method',choices=['W0','W1'],required=True)
    r.add_argument('--video',type=Path,required=True);r.add_argument('--approve-paid-run',action='store_true')
    args=p.parse_args(argv)
    settings=Settings.load();registry=Registry(settings.cases_root,settings.acceptance_key)
    runtime=DockerRuntime()
    if args.cmd=='cases':
        for cid in registry.ids():
            try:c=registry.load(cid);print(cid,registry.acceptance_status(c)['accepted'],registry.acceptance_status(c)['reason'])
            except CaseError as exc:print(cid,False,'invalid manifest:',exc)
    elif args.cmd=='sweep':print('removed',runtime.sweep())
    elif args.cmd=='accept':
        ev=accept_case(runtime,registry,registry.load(args.case))
        print(json.dumps({k:v for k,v in ev.items() if k!='signature'},indent=2))
        ok=ev['independent_fails_before'] and ev['independent_passes_reference'] and ev['browser_smoke']
        print('ACCEPTED' if ok else 'NOT ACCEPTED (evidence written but live remains blocked)');sys.exit(0 if ok else 1)
    elif args.cmd=='run':
        if not args.approve_paid_run:raise SystemExit('Refusing: pass --approve-paid-run to allow Meta spend (cap $%s/run).'%settings.run_budget_usd)
        row=operator_run(settings,registry,args.case,args.method,args.video,runtime)
        print(json.dumps({'id':row['id'],'status':row['status']}))

if __name__=='__main__':main()
