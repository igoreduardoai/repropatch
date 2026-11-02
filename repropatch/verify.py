"""Harness-side verdicts computed in FRESH containers, never in the agent's.

The agent container is untrusted (model-written tests can print anything), so
reproduction confirmation, test sensitivity and final evaluation each run in a
new container from the immutable image with bytes the harness itself holds.
"""
import re
from .cases import Case,tree_files
from .security import BoundaryError

INFRA=re.compile(r"SyntaxError|Cannot find module|ERR_MODULE_NOT_FOUND|MODULE_NOT_FOUND|Test timeout of|"
    r"browserType\.launch|Executable doesn't exist|net::ERR_|ECONNREFUSED|ReferenceError|"
    r"page\.goto: |locator\.\w+: Timeout|Target page, context or browser has been closed|"
    r"No tests found|error TS\d+|Unexpected token|ENOENT|EACCES|ProtocolViolation")
SECRET=re.compile(r"(?i)((?:api[_-]?key|secret|token|passw(?:or)?d)[\"']?\s*[:=]\s*[\"']?)[^\s'\",}]+|sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]{16,}")
REPO='/workspace/repo'

def redact(text:str)->str:
    text=re.sub(r'LLM_[0-9]{8,}_[A-Za-z0-9_-]{20,}', '[redacted]', text)
    return SECRET.sub(lambda m:(m.group(1) or '')+'[redacted]',text)

def classify(case:Case,r:dict)->dict:
    """PASS | ASSERTION_FAILED | INFRA_ERROR | TIMEOUT. Only the second may freeze."""
    if r.get('timed_out'):return {'outcome':'TIMEOUT','reason':'command_timeout'}
    text=(r.get('stdout') or '')+'\n'+(r.get('stderr') or '')
    if r.get('exit_code')==0:return {'outcome':'PASS','reason':'exit_0'}
    m=INFRA.search(text)
    if m:return {'outcome':'INFRA_ERROR','reason':'infra_marker','marker':m.group(0)[:60]}
    if re.search(case.failure_pattern,text):return {'outcome':'ASSERTION_FAILED','reason':'expected_assertion'}
    return {'outcome':'INFRA_ERROR','reason':'unrecognized_failure'}

def fresh_run(runtime,case:Case,run_id:str,role:str,files:dict[str,bytes],argv,timeout=None):
    c=runtime.new_container(case.image_id,run_id,role).start()
    try:
        c.put('/workspace',{'repo/'+n:b for n,b in files.items()},user='0:0')
        # Trusted setup runs before any target/test code. Untrusted tests remain UID 65534.
        # Root-owned read-only files prevent tests from modifying source, themselves or checks.
        lock=c.exec(['chmod','-R','a-w',REPO],user='0:0')
        if lock['exit_code']!=0:raise BoundaryError('Unable to protect evaluator snapshot')
        return c.exec(list(argv),cwd=REPO,timeout=timeout or case.command_timeout_s)
    finally:c.remove()

def confirm_reproduction(runtime,case:Case,run_id:str,test:bytes)->dict:
    """Baseline must fail with the expected assertion AND the reference must pass."""
    base=dict(tree_files(case.snapshot_dir));base[case.repro_path]=test
    before=fresh_run(runtime,case,run_id,'baseline',base,case.repro_argv)
    verdict=classify(case,before)
    out={'baseline':verdict,'baseline_excerpt':redact(((before.get('stdout') or '')+(before.get('stderr') or ''))[-1500:]),
         'reference':None,'confirmed':False}
    if verdict['outcome']!='ASSERTION_FAILED':return out
    ref=dict(tree_files(case.reference_dir));ref[case.repro_path]=test
    after=fresh_run(runtime,case,run_id,'reference',ref,case.repro_argv)
    out['reference']=classify(case,after)
    out['confirmed']=out['reference']['outcome']=='PASS'
    return out

def apply_candidate(case:Case,changes:dict[str,bytes],deleted:list[str])->dict[str,bytes]:
    files=dict(tree_files(case.snapshot_dir))
    for p in [*changes,*deleted]:
        if not any(p.startswith(e) for e in case.editable_paths) or p==case.repro_path:
            raise BoundaryError('Candidate touches a path outside the editable scope')
    for p in deleted:files.pop(p,None)
    files.update(changes)
    return files

def evaluate_candidate(runtime,case:Case,run_id:str,changes:dict[str,bytes],deleted:list[str],
                       frozen_test:bytes|None)->dict:
    """Runs once after finalization. Nothing here is returned to the model."""
    cand=apply_candidate(case,changes,deleted)
    result={}
    if frozen_test is not None:
        r=fresh_run(runtime,case,run_id,'eval-repro',{**cand,case.repro_path:frozen_test},case.repro_argv)
        result['frozen_reproduction']={**classify(case,r),'exit_code':r['exit_code']}
    if case.public_argv:
        r=fresh_run(runtime,case,run_id,'eval-public',cand,case.public_argv)
        result['public_regressions']={'passed':r['exit_code']==0 and not r.get('timed_out'),'exit_code':r['exit_code'],
                                      'timed_out':bool(r.get('timed_out'))}
    ev={f"{case.evaluator_dest}/{n}":b for n,b in tree_files(case.evaluator_dir).items()}
    r=fresh_run(runtime,case,run_id,'eval-independent',{**cand,**ev},case.evaluator_argv)
    result['independent']={'passed':r['exit_code']==0 and not r.get('timed_out'),'exit_code':r['exit_code'],
                           'timed_out':bool(r.get('timed_out'))}
    result['log']=redact(((r.get('stdout') or '')+'\n'+(r.get('stderr') or ''))[-8000:])
    ok=result['independent']['passed'] and result.get('public_regressions',{'passed':True})['passed']
    if frozen_test is not None:ok=ok and result['frozen_reproduction']['outcome']=='PASS'
    result['all_passed']=ok
    return result
