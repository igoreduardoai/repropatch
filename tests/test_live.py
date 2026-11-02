import hashlib
import pytest
from fastapi.testclient import TestClient
from repropatch.api import create_app
from repropatch.budget import Budget,BudgetExceeded
from repropatch.cases import Registry
from repropatch.config import Settings
from repropatch.live import run_live
from repropatch.store import Store,now
from repropatch.worker import process_next
from repropatch.verify import evaluate_candidate
from livekit import *

VIDEO=b'synthetic-video-bytes'

@pytest.fixture
def env(tmp_path):
    cases=tmp_path/'cases';cases.mkdir();make_case(cases)
    s=Settings(data_dir=tmp_path/'data',auth_token='tok',enable_live=True,cases_dir=cases,acceptance_key=KEY)
    s.data_dir.mkdir()
    reg=Registry(cases,KEY);case=reg.load('synthetic-case');accept(reg,case)
    store=Store(s.db_path);budget=Budget(s.db_path,s.live_budget_usd,s.run_budget_usd)
    vdir=s.data_dir/'uploads';vdir.mkdir();vp=vdir/'v.mp4';vp.write_bytes(VIDEO)
    with store.connection() as c:
        c.execute('INSERT INTO uploads VALUES(?,?,?,?,?,?)',('a'*32,str(vp),'v.mp4',len(VIDEO),hashlib.sha256(VIDEO).hexdigest(),now()))
    return s,store,budget,reg,case

def submit(env,method,script,**kw):
    s,store,budget,reg,case=env
    payload={'case_id':'synthetic-case','method':method,'mode':'live','title':'Active filter disappears on page 2',
             'expected_behavior':'x','video_id':'a'*32}
    run=store.create(payload,None);store.transition(run['id'],'PREFLIGHT','claimed');run=store.get(run['id'])
    rt=kw.pop('runtime',FakeRuntime());client=kw.pop('client',None) or ScriptedClient(budget,script)
    run_live(store,s,run,runtime=rt,client=client,registry=reg)
    return store.get(run['id']),rt,client

W1_GOOD=[('write_reproduction_test',{'content':REPRO_OK}),('freeze_reproduction',{}),
         ('write_source',{'path':'src/pagination.mjs','content':CORRECT}),
         ('run_public_regressions',{}),('submit_candidate',{'claim':'fixed'})]

def test_w1_end_to_end_verified_with_persisted_evidence(env):
    s,store,budget,reg,case=env
    row,rt,client=submit(env,'W1',W1_GOOD)
    assert row['status']=='VERIFIED',row['result']
    r=row['result']
    assert r['source']=='live' and r['model']=='muse-wonder-1.0' and r['verified'] is True
    assert r['frozen_test_sha256']==hashlib.sha256(REPRO_OK.encode()).hexdigest()
    assert len(r['candidate_sha256'])==64 and len(r['patch_sha256'])==64
    assert r['model_calls']==5 and r['unknown_calls']==0 and r['committed_usd']>0
    assert r['evaluation']['all_passed'] and 'log' not in r['evaluation']
    stages=[e['stage'] for e in store.events(row['id'])]
    assert stages.index('FROZEN')<stages.index('PATCHING')<stages.index('VERIFYING')
    names={a['name'] for a in store.artifacts(row['id'])}
    assert {'repair.patch','report.json','reproduction.frozen.mjs','evaluator.log'}<=names
    assert client.uploaded and rt.live==set()                      # containers all removed
    # evaluator ran in fresh containers after submit and never in the agent one
    roles=[r for r,_ in rt.execs]
    assert 'eval-independent' in roles and roles.index('eval-independent')>roles.index('reference')

def test_false_fix_is_rejected_by_independent_evaluator(env):
    script=[('write_reproduction_test',{'content':REPRO_OK}),('freeze_reproduction',{}),
            ('write_source',{'path':'src/pagination.mjs','content':FALSE_FIX}),('submit_candidate',{'claim':'fixed'})]
    row,rt,_=submit(env,'W1',script)
    assert row['status']=='REJECTED' and row['result']['false_success'] is True
    assert row['result']['evaluation']['independent']['passed'] is False

def test_w1_without_confirmed_reproduction_is_not_reproduced(env):
    script=[('write_reproduction_test',{'content':REPRO_SYNTAX}),('freeze_reproduction',{}),
            ('write_source',{'path':'src/pagination.mjs','content':CORRECT})]+[('list_files',{})]*30
    row,rt,_=submit(env,'W1',script)
    assert row['status']=='NOT_REPRODUCED' and row['result']['reproduced'] is False
    assert not any(e['stage']=='PATCHING' for e in store_events(env,row))

def store_events(env,row):return env[1].events(row['id'])

def test_w0_can_patch_without_freezing_and_empty_patch_is_rejected(env):
    row,_,_=submit(env,'W0',[('write_source',{'path':'src/pagination.mjs','content':CORRECT}),('submit_candidate',{'claim':'fixed'})])
    assert row['status']=='VERIFIED' and row['result']['frozen_test_sha256'] is None
    row,_,_=submit(env,'W0',[('submit_candidate',{'claim':'fixed'})])
    assert row['status']=='REJECTED' and row['result']['reason']=='empty_patch'

def test_blocked_without_acceptance_and_no_model_call(env):
    s,store,budget,reg,case=env
    case.acceptance_path.unlink()
    client=ScriptedClient(budget,[])
    row,rt,_=submit(env,'W1',[],client=client)
    assert row['status']=='BLOCKED' and row['result']['model_calls']==0 and client.calls==0 and not rt.created

def test_blocked_for_wrong_video_unregistered_case_or_missing_key(env,monkeypatch):
    s,store,budget,reg,case=env
    with store.connection() as c:c.execute("UPDATE uploads SET sha256=?",('0'*64,))
    row,_,client=submit(env,'W1',[])
    assert row['status']=='BLOCKED' and 'video_not_the_reviewed_case_video' in row['result']['reason'] and client.calls==0
    monkeypatch.delenv('META_MODEL_API_KEY',raising=False);monkeypatch.delenv('MODEL_API_KEY',raising=False)
    with store.connection() as c:c.execute("UPDATE uploads SET sha256=?",(hashlib.sha256(VIDEO).hexdigest(),))
    run=store.create({'case_id':'synthetic-case','method':'W1','mode':'live','title':'t t t','expected_behavior':'x'*10,'video_id':'a'*32},None)
    store.transition(run['id'],'PREFLIGHT','c')
    run_live(store,s,store.get(run['id']),runtime=FakeRuntime(),registry=reg)   # no client injected -> real MetaClient needs a key
    got=store.get(run['id']);assert got['status']=='BLOCKED' and 'meta_client' in got['result']['reason']

def test_image_drift_blocks(env):
    row,rt,client=submit(env,'W1',[],runtime=FakeRuntime(image='sha256:'+'c'*64))
    assert row['status']=='BLOCKED' and client.calls==0

def test_halted_ledger_blocks_before_any_call(env):
    s,store,budget,reg,case=env;budget.halt('request_billing_unknown')
    row,_,client=submit(env,'W1',W1_GOOD)
    assert row['status']=='BLOCKED' and client.calls==0

def test_unknown_billing_error_stops_as_error_and_does_not_retry(env):
    class Boom(ScriptedClient):
        def respond(self,run_id,inputs,tools,budget,max_output=1800):
            self.calls+=1;rid='x'*32;budget.reserve(rid,run_id,10,10);budget.unknown(rid);raise RuntimeError('timeout')
    s,store,budget,*_=env
    row,rt,client=submit(env,'W1',[],client=Boom(budget,[]))
    assert row['status']=='ERROR' and client.calls==1 and row['result']['unknown_calls']==1
    assert row['result']['ledger_halted']=='request_billing_unknown' and rt.live==set()

def test_budget_exceeded_maps_to_status(env):
    class Over(ScriptedClient):
        def respond(self,*a,**k):raise BudgetExceeded('Call reservation exceeds run or batch budget')
    row,rt,_=submit(env,'W1',[],client=Over(env[2],[]))
    assert row['status']=='BUDGET_EXCEEDED' and rt.live==set()

def test_cancel_between_tools_cleans_up(env):
    s,store,budget,*_=env
    class Cancelling(ScriptedClient):
        def respond(self,run_id,*a,**k):
            if self.calls==1:store.cancel(run_id)
            return super().respond(run_id,*a,**k)
    row,rt,_=submit(env,'W1',W1_GOOD,client=Cancelling(budget,W1_GOOD))
    assert row['status']=='CANCELLED' and rt.live==set()

def test_abstention_after_freeze_is_rejected_not_verified(env):
    class Quit(ScriptedClient):
        def respond(self,run_id,*a,**k):
            r=super().respond(run_id,*a,**k)
            if self.calls==3:r['output']=[]
            return r
    s,store,budget,*_=env
    row,*_=submit(env,'W1',W1_GOOD,client=Quit(budget,W1_GOOD))
    assert row['status']=='REJECTED' and row['result']['frozen_test_sha256']

def test_evaluator_rejects_out_of_scope_candidate(env):
    case=env[4]
    with pytest.raises(Exception):evaluate_candidate(FakeRuntime(),case,'r',{'tests/public.mjs':b'//'},[],None)
    with pytest.raises(Exception):evaluate_candidate(FakeRuntime(),case,'r',{'tests/repro.mjs':b'//'},[],None)

def test_agent_container_never_receives_private_material(env):
    s,store,budget,reg,case=env
    row,rt,_=submit(env,'W1',W1_GOOD)
    agent_files={n:b for role,files in rt.puts if role=='agent' for n,b in files.items()}
    assert 'repo/src/pagination.mjs' in agent_files and agent_files['repo/src/pagination.mjs']==(case.snapshot_dir/'src'/'pagination.mjs').read_bytes()
    assert not any(n.startswith('repo/maintainer') for n in agent_files)          # hidden evaluator tests
    assert not any(b'correct' in n.encode() or b==CORRECT.encode() for n,b in agent_files.items() if n.endswith('pagination.mjs'))
    evaluator_puts=[f for role,f in rt.puts if role=='eval-independent']
    assert evaluator_puts and any(n.startswith('repo/maintainer/') for n in evaluator_puts[0])
    assert not any(n.startswith('repo/maintainer') for role,f in rt.puts if role in {'baseline','reference','eval-repro','eval-public'} for n in f)

# ---- API gating -----------------------------------------------------------------
def client_for(env,**over):
    s=env[0]
    from dataclasses import replace
    app=create_app(replace(s,**over));c=TestClient(app);c.headers['Authorization']='Bearer tok';return c,app

def test_api_live_requires_flag_acceptance_video_and_registered_case(env):
    s,store,budget,reg,case=env
    body={'mode':'live','case_id':'synthetic-case','method':'W1','video_id':'a'*32}
    c,_=client_for(env,enable_live=False)
    assert c.post('/api/runs',json=body).status_code==409
    c,_=client_for(env)
    assert c.post('/api/runs',json={**body,'case_id':'unknown-case'}).status_code==400
    assert c.post('/api/runs',json={**body,'video_id':None}).status_code==400
    r=c.post('/api/runs',json=body);assert r.status_code==201 and r.json()['mode']=='live'
    case.acceptance_path.unlink()
    assert c.post('/api/runs',json=body).status_code==409
    assert c.post('/api/runs',json={'case_id':'synthetic-case'}).status_code==400   # fixture mode only runs its fixture

def test_config_live_enabled_only_with_accepted_case(env):
    s,store,budget,reg,case=env
    c,_=client_for(env);cfg=c.get('/api/config').json()
    assert cfg['live_enabled'] is True and cfg['live_cases'][0]['case_id']=='synthetic-case'
    assert str(s.data_dir) not in str(cfg) and 'private' not in str(cfg)
    case.acceptance_path.unlink();assert c.get('/api/config').json()['live_enabled'] is False
    c,_=client_for(env,enable_live=False);assert c.get('/api/config').json()['live_enabled'] is False

def test_worker_routes_live_and_blocks_instead_of_fixture(env):
    s,store,budget,reg,case=env
    case.acceptance_path.unlink()
    c,app=client_for(env)
    # bypass API gate: queue a live run directly
    run=store.create({'case_id':'synthetic-case','method':'W1','mode':'live','title':'abc','expected_behavior':'x'*10,'video_id':'a'*32},None)
    assert process_next(store,s)
    got=store.get(run['id']);assert got['status']=='BLOCKED' and got['result'].get('source')=='live'
