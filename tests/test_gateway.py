import hashlib
import pytest
from repropatch.fixture import Cancelled
from repropatch.gateway import SandboxGateway,GatewayError,apply_unified_diff,split_patch
from repropatch.cases import Registry
from repropatch.security import BoundaryError
from livekit import *

@pytest.fixture
def env(tmp_path):
    root=tmp_path/'cases';root.mkdir();make_case(root)
    reg=Registry(root,KEY);case=reg.load('synthetic-case')
    return case,FakeRuntime(),tmp_path

def gw(env,method='W1',**kw):
    case,rt,tmp=env
    stages=[];g=SandboxGateway(case,method,rt,'r1',tmp/'data',on_stage=lambda s,m:stages.append(s),**kw).setup()
    g.stages=stages;return g

def freeze(g,body=REPRO_OK):
    g.execute('write_reproduction_test',{'content':body});return g.execute('freeze_reproduction',{})

def test_tool_surface_matches_contract_and_has_no_shell(env):
    names={d['name'] for d in gw(env).definitions()}
    assert names=={'list_files','read_file','browser_observe','browser_action','write_reproduction_test','run_reproduction',
        'freeze_reproduction','write_source','apply_patch','run_public_regressions','submit_candidate'}
    assert all(d['type']=='function' for d in gw(env).definitions())
    with pytest.raises(GatewayError):gw(env).execute('bash',{'cmd':'id'})

def test_w1_blocks_source_edit_before_freeze(env):
    g=gw(env)
    with pytest.raises(BoundaryError):g.execute('write_source',{'path':'src/pagination.mjs','content':CORRECT})
    assert 'PATCHING' not in g.stages

def test_syntax_error_or_always_failing_test_never_freezes(env):
    g=gw(env)
    r=freeze(g,REPRO_SYNTAX)
    assert r['error']=='not_a_valid_reproduction' and not g.frozen
    r=freeze(g,REPRO_ALWAYS_FAIL)  # fails on baseline AND reference: infra-free but not sensitive
    assert r['error']=='test_not_sensitive_to_expected_behavior' and not g.frozen
    with pytest.raises(BoundaryError):g.execute('write_source',{'path':'src/pagination.mjs','content':CORRECT})

def test_passing_test_on_baseline_is_not_a_reproduction(env):
    g=gw(env);r=freeze(g,"console.log('ok')\n")
    assert r['error']=='not_a_valid_reproduction' and g.frozen is None

def test_confirmed_freeze_persists_hash_outside_workspace_and_unlocks_edits(env):
    g=gw(env);r=freeze(g)
    assert r['frozen'] and r['test_sha256']==hashlib.sha256(REPRO_OK.encode()).hexdigest()
    ext=g.frozen['path']
    assert str(g.evidence) in ext and open(ext).read()==REPRO_OK
    assert not str(g.c.dir) in ext
    with pytest.raises(BoundaryError):g.execute('write_reproduction_test',{'content':'// edited'})
    with pytest.raises(GatewayError):g.execute('freeze_reproduction',{})
    g.execute('write_source',{'path':'src/pagination.mjs','content':CORRECT})
    assert g.stages==['FROZEN','PATCHING']
    with pytest.raises(BoundaryError):g.execute('write_source',{'path':'tests/repro.mjs','content':'// suppress'})

def test_confirmation_runs_in_fresh_containers_not_the_agent_container(env):
    case,rt,_=env;g=gw(env);freeze(g)
    roles={r for r,_ in rt.execs}
    assert {'baseline','reference'}<=roles and 'agent' not in roles

def test_edit_scope_and_types(env):
    g=gw(env,'W0')
    for path in ['package.json','tests/public.mjs','.env','../x','src/../tests/x.mjs','private/a.js']:
        with pytest.raises(BoundaryError):g.execute('write_source',{'path':path,'content':'x'})
    with pytest.raises(BoundaryError):g.execute('write_source',{'path':'src/a.sh','content':'x'})
    with pytest.raises(BoundaryError):g.execute('write_source',{'path':'src/a.mjs','content':'x'*100_001})

def test_read_redacts_and_blocks_forbidden(env):
    g=gw(env)
    g.c.put('/workspace',{'repo/src/cfg.json':b'{"token": "supersecretvalue1234"}'})
    out=g.execute('read_file',{'path':'src/cfg.json'})['content']
    assert 'supersecretvalue1234' not in out
    for p in ['.git/config','.env','maintainer/check.mjs','src/x.exe']:
        with pytest.raises((BoundaryError,GatewayError)):g.execute('read_file',{'path':p})

def test_apply_patch_strict_and_only_editable(env):
    g=gw(env,'W0')
    ok=("--- a/src/pagination.mjs\n+++ b/src/pagination.mjs\n@@ -2,2 +2,2 @@\n"
        "   // Fixture bug: the filter is incorrectly dropped after the first page.\n"
        "-  const filtered = page === 1 ? rows.filter(r => r.status === status) : rows;\n"
        "+  const filtered = rows.filter(r => r.status === status);\n")
    # context line count mismatch in hunk header is tolerated; content mismatch is not
    g.execute('apply_patch',{'patch':ok})
    assert 'rows.filter(r => r.status === status);' in g.execute('read_file',{'path':'src/pagination.mjs'})['content']
    bad=ok.replace('-  const filtered = page','-  const nothere = page')
    with pytest.raises(GatewayError):g.execute('apply_patch',{'patch':bad})
    outside=ok.replace('src/pagination.mjs','tests/public.mjs')
    with pytest.raises(BoundaryError):g.execute('apply_patch',{'patch':outside})
    with pytest.raises(GatewayError):split_patch("--- a/src/x.mjs\n+++ /dev/null\n@@ -1 +0,0 @@\n-x\n")
    with pytest.raises(GatewayError):split_patch("--- a/src/x.mjs\n+++ b/src/y.mjs\n@@ -1 +1 @@\n-x\n+y\n")

def test_apply_unified_diff_new_file():
    assert apply_unified_diff(None,"@@ -0,0 +1,2 @@\n+a\n+b\n",'x')=='a\nb\n'

def test_submit_extracts_candidate_host_side_and_ends_tools(env):
    g=gw(env);freeze(g)
    g.execute('write_source',{'path':'src/pagination.mjs','content':CORRECT})
    g.c.put('/workspace',{'repo/src/new.mjs':b'export const x=1\n','repo/tests/extra.mjs':b'// outside scope'})
    r=g.execute('submit_candidate',{'claim':'fixed'})
    c=g.candidate
    assert set(c['changes'])=={'src/pagination.mjs','src/new.mjs'} and c['deleted']==[]
    assert 'tests/extra.mjs' not in c['changes']            # out-of-scope junk never reaches the candidate
    assert r['candidate_sha256']==c['candidate_sha256'] and r['frozen_test_sha256']==g.frozen['test_sha256']
    assert '+++ b/src/pagination.mjs' in c['patch'] and c['workspace_test_modified'] is False
    with pytest.raises(GatewayError):g.execute('list_files',{})
    assert g.c is None

def test_w1_cannot_submit_without_freeze_w0_can(env):
    with pytest.raises(GatewayError):gw(env).execute('submit_candidate',{'claim':'x'})
    g=gw(env,'W0');assert g.execute('submit_candidate',{'claim':'nothing'})['files_changed']==[]

def test_cancel_stops_next_tool(env):
    flag={'c':False};g=gw(env,should_cancel=lambda:flag['c'])
    g.execute('list_files',{});flag['c']=True
    with pytest.raises(Cancelled):g.execute('list_files',{})

def test_browser_tools_store_screenshot_hash_and_redact(env):
    shots=[];g=gw(env,on_artifact=lambda n,b,t:shots.append((n,t)))
    r=g.execute('browser_observe',{})
    assert shots and shots[0][1]=='image/png' and r['screenshot_sha256']
    assert 'sk-abcdefghijklmnopqrstuv' not in r['text']
    with pytest.raises(GatewayError):g.execute('browser_action',{'kind':'eval'})
    for _ in range(40):
        try:g.execute('browser_action',{'kind':'wait','value':'1'})
        except GatewayError as e:assert 'limit' in str(e);break
    else:pytest.fail('browser call limit not enforced')

def test_no_browser_tools_without_profile_serve(tmp_path):
    root=tmp_path/'c';root.mkdir();make_case(root,serve=False)
    case=Registry(root,KEY).load('synthetic-case')
    names={d['name'] for d in SandboxGateway(case,'W1',FakeRuntime(),'r',tmp_path).definitions()}
    assert 'browser_observe' not in names

def test_dispatcher_script_is_valid_javascript():
    import shutil,subprocess
    from pathlib import Path
    if not shutil.which('node'):pytest.skip('node not installed')
    p=Path(__file__).resolve().parents[1]/'repropatch'/'sandbox_runtime'/'dispatch.mjs'
    assert subprocess.run(['node','--check',str(p)],capture_output=True).returncode==0
