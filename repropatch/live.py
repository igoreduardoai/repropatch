"""Live run orchestration: registry gate -> sandbox -> Muse AgentLoop -> fresh evaluator.

Fails closed. Every unsuccessful path ends in an explicit terminal status; an
exception is never turned into VERIFIED. Containers are always removed.
"""
import json
import logging
import time
from pathlib import Path
from .agent import AgentLoop
from .artifacts import save_artifact
from .auditor import run_after_verdict
from .budget import Budget,BudgetExceeded,UsageMismatch
from .cases import CaseError,Registry
from .docker_runtime import DockerRuntime
from .fixture import Cancelled
from .gateway import SandboxGateway
from .meta import MetaClient,MetaError
from .models import TERMINAL
from .security import sha256
from .store import now
from .verify import evaluate_candidate,redact

log=logging.getLogger('repropatch.live')
MODEL='muse-wonder-1.0'

class Blocked(Exception):pass

def preflight(settings,registry:Registry,runtime,payload:dict,store):
    """Everything that must hold BEFORE any paid call. Raises Blocked(reason)."""
    try:case=registry.load(payload.get('case_id'))
    except CaseError as exc:raise Blocked(f'case_not_registered: {exc}')
    acc=registry.acceptance_status(case)
    if not acc['accepted']:raise Blocked('acceptance_missing: '+acc['reason'])
    if settings.meta_model!=MODEL:raise Blocked('model_not_allowed')
    try:local=runtime.image_id(case.image_id)
    except Exception as exc:raise Blocked(f'sandbox_image_unavailable: {type(exc).__name__}')
    acc=registry.acceptance_status(case,live_image_id=local)
    if not acc['accepted']:raise Blocked('acceptance_missing: '+acc['reason'])
    vid=payload.get('video_id')
    if not vid:raise Blocked('video_required')
    with store.connection() as c:row=c.execute('SELECT path,sha256 FROM uploads WHERE id=?',(vid,)).fetchone()
    if not row or not Path(row['path']).is_file():raise Blocked('video_not_found')
    if row['sha256']!=case.video_sha256:raise Blocked('video_not_the_reviewed_case_video')
    return case,acc,Path(row['path'])

def run_live(store,settings,run,runtime=None,client=None,registry=None):
    rid=run['id'];payload=run['payload'];method=run['method']
    runtime=runtime or DockerRuntime()
    registry=registry or Registry(settings.cases_root,settings.acceptance_key)
    budget=Budget(settings.db_path,settings.live_budget_usd,settings.run_budget_usd)
    gateway=None
    started=now();clock_started=time.monotonic()

    def advance(target,message):
        cur=store.get(rid)['status']
        if cur==target or cur in TERMINAL:return
        try:store.transition(rid,target,message)
        except ValueError:log.warning('Skipped stage %s from %s',target,cur)

    def finish(status,message,result):
        cur=store.get(rid)['status']
        if cur in TERMINAL:return
        spend=budget.run_spend(rid)
        store.transition(rid,status,message,{'cost_usd':spend['settled_usd'],'duration_ms':round((time.monotonic()-clock_started)*1000),'source':'live','mode':'live','model':MODEL,'method':method,
            'case_id':payload.get('case_id'),'verified':status=='VERIFIED','operator_interventions':0,
            'started_at':started,'finished_at':now(),**spend,**result})
        summary=store.get(rid)['result']
        save_artifact(store,settings.data_dir,rid,'attempt-summary.json',json.dumps(summary,indent=2).encode(),'application/json')

    def emit(kind,data):
        if store.cancelled(rid):raise Cancelled()
        if 'error_reason' in data:data={**data,'error_reason':redact(data['error_reason'])}
        if kind=='model_usage':store.event(rid,'Model response received (usage recorded).','info',data)
        else:store.event(rid,f'Tool finished: {data.get("tool")}','warning' if data.get('error') else 'info',data)

    try:
        try:
            case,acc,video=preflight(settings,registry,runtime,payload,store)
            if budget.summary()['halted']:raise Blocked('ledger_halted: '+budget.summary()['halted'])
            if store.cancelled(rid):raise Cancelled()
            client=client or MetaClient(settings.meta_base_url,settings.meta_model)
        except Blocked as exc:
            finish('BLOCKED','Live run blocked before any model call.',{'reason':str(exc)[:300],'model_calls':0});return
        except MetaError as exc:
            finish('BLOCKED','Live run blocked before any model call.',{'reason':'meta_client: '+str(exc)[:200],'model_calls':0});return
        store.event(rid,'LIVE run. Muse Wonder inference via Meta API; target code runs only in the sandbox.','warning',
                    {'source':'live','case_id':case.case_id,'base_commit':case.base_commit,
                     'manifest_sha256':case.manifest_sha256,'acceptance':acc['signature'][:16]})
        advance('REPRODUCING','Sandbox starting from the immutable case snapshot.')

        def on_artifact(name,body,ctype):
            save_artifact(store,settings.data_dir,rid,name,body,ctype)
        def on_event(kind,data):store.event(rid,'Harness: '+kind.replace('_',' '),'info',data)
        gateway=SandboxGateway(case,method,runtime,rid,settings.data_dir,
            on_stage=lambda s,m:advance(s,m),on_event=on_event,on_artifact=on_artifact,
            should_cancel=lambda:store.cancelled(rid)).setup()
        on_artifact('bug-reproduction.mp4',video.read_bytes(),'video/mp4')
        file_id=client.upload_video(video)
        store.event(rid,'Reviewed case video uploaded to Meta Files for this run.','info',
                    {'video_sha256':case.video_sha256})
        outcome=AgentLoop(client,gateway,budget,emit).run(rid,method,payload['title'],case.expected_behavior,file_id)
        frozen=gateway.frozen
        if outcome['status']!='CANDIDATE_SUBMITTED':
            if method=='W1' and not frozen:
                finish('NOT_REPRODUCED','No confirmed reproduction was frozen; no source edit was allowed.',
                       {'reproduced':False,'agent_status':outcome['status'],'reason':outcome.get('reason'),'false_success':False})
            else:
                finish('REJECTED','The agent ended without submitting a candidate.',
                       {'reproduced':bool(frozen),'agent_status':outcome['status'],'reason':outcome.get('reason'),
                        'frozen_test_sha256':frozen['test_sha256'] if frozen else None,'false_success':False})
            return
        cand=gateway.candidate
        advance('PATCHING','Candidate submitted.')
        advance('VERIFYING','Candidate is final. Running the independent evaluator once in fresh containers.')
        save_artifact(store,settings.data_dir,rid,'repair.patch',cand['patch'].encode(),'text/x-diff')
        if frozen:
            save_artifact(store,settings.data_dir,rid,'reproduction.frozen'+Path(case.repro_path).suffix,
                          gateway.frozen_bytes,'text/plain')
        base={'reproduced':bool(frozen),'agent_claim':cand['claim'],'candidate_sha256':cand['candidate_sha256'],
              'patch_sha256':cand['patch_sha256'],'frozen_test_sha256':cand['frozen_test_sha256'],
              'workspace_test_modified':cand['workspace_test_modified'],'patch':cand['patch'],
              'files_changed':sorted([*cand['changes'],*cand['deleted']])}
        if not cand['changes'] and not cand['deleted']:
            finish('REJECTED','The candidate contains no source change.',{**base,'reason':'empty_patch','false_success':False});return
        ev=evaluate_candidate(runtime,case,rid,cand['changes'],cand['deleted'],gateway.frozen_bytes if frozen else None)
        log_text=ev.pop('log')
        save_artifact(store,settings.data_dir,rid,'evaluator.log',log_text.encode(),'text/plain')
        verified=ev['all_passed']
        res={**base,'evaluation':ev,'regressions':0 if ev.get('public_regressions',{}).get('passed',True) else 1,
             'limitation':'VERIFIED means the executed frozen/public/independent checks passed; not a proof of correctness.',
             'false_success':(not verified) and 'fixed' in cand['claim'].lower()}
        save_artifact(store,settings.data_dir,rid,'report.json',json.dumps(res,indent=2).encode(),'application/json')
        finish('VERIFIED' if verified else 'REJECTED',
               'Candidate passed the executed checks.' if verified else 'Candidate failed an independent check.',res)
        # Advisory audit strictly AFTER the verdict is persisted; it cannot alter it.
        try:
            audit=run_after_verdict(store,settings,rid,{'title':payload.get('title'),'expected_behavior':case.expected_behavior},
                                    res,gateway.frozen_bytes.decode('utf-8','replace') if frozen else None)
            if audit:save_artifact(store,settings.data_dir,rid,'advisory-audit.json',json.dumps(audit,indent=2).encode(),'application/json')
        except Exception as exc:
            log.error('Advisory audit hook failed for %s: %s',rid,type(exc).__name__)
    except Cancelled:
        finish('CANCELLED','Stopped between operations.',{'reason':'cancelled'})
    except (BudgetExceeded,UsageMismatch) as exc:
        finish('BUDGET_EXCEEDED','Stopped by the spend ledger; reconcile before retrying.',
               {'reason':type(exc).__name__,'ledger_halted':True})
    except Exception as exc:
        log.error('Live run %s failed: %s',rid,type(exc).__name__)
        halted=budget.summary()['halted']
        finish('ERROR','Execution failed; inspect operator logs. No automatic retry.',
               {'reason':type(exc).__name__,'error_detail':redact(str(exc))[:1000],'ledger_halted':halted})
    finally:
        try:
            if gateway:gateway.close()
        finally:
            try:runtime.sweep(rid)
            except Exception:log.error('Container sweep failed for %s',rid)
