"""Synthetic, scripted integration fixture. NO MODEL CALLS.

Runs only package-owned, known JS sources. This host subprocess path must
never be reused for uploaded repositories, model-written code, or live tests.
"""
import difflib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from .artifacts import save_artifact
from .config import ROOT
from .security import freeze_test, check_frozen, sha256

FIXTURES=ROOT/"fixtures"/"pagination"

class Cancelled(Exception):pass

def trusted_js(source:Path,test:Path):
    allowed={p.resolve() for p in FIXTURES.glob('*.mjs')}
    allowed.add((ROOT/'evaluation'/'fixture-independent.mjs').resolve())
    if source.resolve() not in allowed or test.resolve() not in allowed:
        raise ValueError('Host execution is restricted to package-owned fixtures')
    node=shutil.which('node')
    if not node:raise RuntimeError('Node.js is required for the trusted fixture')
    with tempfile.TemporaryDirectory(prefix='repropatch-fixture-') as folder:
        work=Path(folder)
        shutil.copyfile(source,work/'app.mjs')
        shutil.copyfile(test,work/'test.mjs')
        begin=time.monotonic()
        r=subprocess.run([node,'test.mjs'],cwd=work,capture_output=True,text=True,
            timeout=15,env={"PATH":os.getenv('PATH',''),"HOME":folder})
        try:data=json.loads(r.stdout.strip())
        except json.JSONDecodeError:
            raise RuntimeError('Fixture execution failed without structured evidence')
        return {**data,'exit_code':r.returncode,'duration_ms':round((time.monotonic()-begin)*1000,2)}

def run_fixture(store,settings,run):
    rid=run['id'];method=run['method'];start=time.monotonic()
    def step(stage,message):
        if store.cancelled(rid):
            store.transition(rid,'CANCELLED','Stopped between operations.');raise Cancelled()
        store.transition(rid,stage,message)
    store.event(rid,'Synthetic harness fixture. Patches are scripted; Muse is NOT being called.',
                'warning',{'source':'fixture','model_calls':0})
    step('REPRODUCING','Executing the fixed reproduction test against the original fixture.')
    before=trusted_js(FIXTURES/'buggy.mjs',FIXTURES/'reproduction.mjs')
    store.event(rid,'Original code fails the intended assertion.','warning',before)
    if before.get('status')!='ASSERTION_FAILED':
        step('NOT_REPRODUCED','Expected assertion did not fail; repair not attempted.');return
    frozen_dir=settings.data_dir/'frozen'/rid
    frozen=freeze_test(FIXTURES/'reproduction.mjs',frozen_dir)
    if method=='W1':step('FROZEN','Reproduction test frozen before any patch; SHA-256 recorded.')
    store.event(rid,'Reproduction evidence saved.','info',{'sha256':frozen['sha256'],
        'protocol_enforced':method=='W1'})
    step('PATCHING','Applying the deliberately incomplete fixture patch.')
    first=trusted_js(FIXTURES/'false-fix.mjs',FIXTURES/'reproduction.mjs')
    visible=trusted_js(FIXTURES/'false-fix.mjs',FIXTURES/'regression.mjs')
    store.event(rid,'Candidate passes reproduction but fails public regression checks.','warning',
                {'reproduction':first,'public_regressions':visible})
    selected=FIXTURES/'false-fix.mjs'
    if method=='W1':
        store.event(rid,'Scripted recovery: choose the complete fixture patch. Not an AI repair.','info')
        selected=FIXTURES/'correct.mjs'
    check_frozen(Path(frozen['path']),frozen['sha256'])
    final_repro=trusted_js(selected,FIXTURES/'reproduction.mjs')
    step('VERIFYING','Final candidate frozen. Running independent fixture checks once.')
    evaluation=trusted_js(selected,ROOT/'evaluation'/'fixture-independent.mjs')
    verified=final_repro['status']=='PASS' and evaluation['passed']==evaluation['total']
    original=(FIXTURES/'buggy.mjs').read_text();candidate=selected.read_text()
    patch=''.join(difflib.unified_diff(original.splitlines(True),candidate.splitlines(True),
                                    fromfile='a/src/pagination.mjs',tofile='b/src/pagination.mjs'))
    result={'source':'synthetic_fixture','benchmark_eligible':False,'model_calls':0,
            'model':None,'method':method,'verified':verified,'reproduced':True,
            'agent_claim':'fixed (scripted fixture)','false_success':not verified,
            'regressions':evaluation['total']-evaluation['passed'],
            'reproduction_before':before,'reproduction_after':final_repro,
            'independent':evaluation,'frozen_test_sha256':frozen['sha256'],
            'candidate_sha256':sha256(candidate.encode()),'patch':patch,
            'cost_usd':0.0,'duration_ms':round((time.monotonic()-start)*1000,2),
            'limitation':'Scripted synthetic fixture, not evidence of model repair performance.'}
    save_artifact(store,settings.data_dir,rid,'repair.patch',patch.encode(),'text/x-diff')
    save_artifact(store,settings.data_dir,rid,'report.json',json.dumps(result,indent=2).encode(),'application/json')
    save_artifact(store,settings.data_dir,rid,'reproduction.frozen.mjs',Path(frozen['path']).read_bytes())
    store.transition(rid,'VERIFIED' if verified else 'REJECTED',
       'Fixture passes the executed checks; not a model benchmark.' if verified else
       'Fixture rejected by independent checks; original assertion alone was insufficient.',result)
