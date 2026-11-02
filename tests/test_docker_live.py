"""Real Docker isolation tests. Skipped unless Docker and a local node image exist.
They use a stock node image (no Chromium): they prove container isolation, file IO,
freeze/evaluator flow and cleanup, NOT the Playwright browser path."""
import hashlib
import json
import shutil
import subprocess
import pytest
from repropatch.budget import Budget
from repropatch.cases import Registry
from repropatch.config import Settings
from repropatch.docker_runtime import DockerRuntime,DockerError,OWNER_LABEL
from repropatch.gateway import SandboxGateway,GatewayError
from repropatch.live import run_live
from repropatch.opscli import accept_case
from repropatch.store import Store,now
from livekit import make_case,accept,ScriptedClient,KEY,REPRO_OK,CORRECT,FIX

IMAGE_REF='node:22-bookworm-slim'

def _image_id():
    if not shutil.which('docker'):return None
    r=subprocess.run(['docker','image','inspect','--format','{{.Id}}',IMAGE_REF],capture_output=True,text=True)
    return r.stdout.strip() if r.returncode==0 else None

IMG=_image_id()
pytestmark=pytest.mark.skipif(not IMG,reason='Docker + local node image required')

def owned():
    return subprocess.run(['docker','ps','-aq','--filter','label='+OWNER_LABEL],capture_output=True,text=True).stdout.split()

@pytest.fixture
def rt():
    r=DockerRuntime();assert not owned(),'refusing to run with foreign leftovers of ours';yield r
    r.sweep()
    assert owned()==[]

def test_container_hardening_is_what_we_claim(rt):
    c=rt.new_container(IMG,'t1','agent').start()
    info=json.loads(subprocess.run(['docker','inspect',c.name],capture_output=True,text=True).stdout)[0]
    hc=info['HostConfig']
    assert hc['NetworkMode']=='none' and hc['ReadonlyRootfs'] is True and hc['CapDrop']==['ALL']
    assert 'no-new-privileges' in ' '.join(hc['SecurityOpt']) and not hc['Binds'] and not hc['Privileged']
    assert {m['Type'] for m in info['Mounts']}<= {'tmpfs'} and info['Config']['User']=='65534:65534'
    assert not any('docker.sock' in json.dumps(m) for m in info['Mounts'])
    assert not any(('META' in e or 'KEY' in e or 'TOKEN' in e) for e in info['Config']['Env'])
    assert c.exec(['node','-e','require("net").connect(443,"1.1.1.1").on("error",e=>{console.log("NONET");process.exit(0)}).on("connect",()=>{console.log("NET")})'],timeout=30)['stdout'].strip()=='NONET'
    assert c.exec(['sh','-c','touch /etc/x 2>&1; echo $?'])['stdout'].strip().endswith('1')
    assert c.exec(['sh','-c','ls /var/run/docker.sock /Users /root 2>&1 | head -1'])['stdout']
    assert 'docker.sock' not in c.exec(['sh','-c','ls /var/run'])['stdout']
    c.put('/workspace',{'repo/a.txt':b'hi'});assert c.get_file('/workspace/repo/a.txt')==b'hi'
    assert c.get_dir('/workspace/repo')=={'a.txt':b'hi'}
    c.remove();assert owned()==[]

def test_dispatcher_path_policy_inside_container(rt):
    c=rt.new_container(IMG,'t2','agent').start()
    try:
        c.put('/workspace',{'repo/src/a.mjs':b'x','repo/.env':b'SECRET=1','repo/.git/config':b'g'});c.open_dispatcher()
        ok=lambda op,**kw:c.call({'op':op,'id':1,**kw})
        assert ok('read',path='src/a.mjs')['result']['content']=='x'
        for bad in ['.env','.git/config','../etc/passwd','/etc/passwd','src/../../x','a\\b']:
            assert ok('read',path=bad)['ok'] is False,bad
        names=[e['name'] for e in ok('list',path='.')['result']['entries']]
        assert '.env' not in names and '.git' not in names
        c.exec(['ln','-s','/etc/passwd','/workspace/repo/src/link'])
        assert ok('read',path='src/link')['ok'] is False
        assert ok('write',path='src/b.mjs',content='y')['ok'] and c.get_file('/workspace/repo/src/b.mjs')==b'y'
        assert ok('write',path='.env',content='y')['ok'] is False
        r=ok('exec',argv=['node','-e','setTimeout(()=>{},60000)'],cwd='.',timeout_ms=800)['result']
        assert r['timed_out'] and r['exit_code']==124
        assert ok('nope')['ok'] is False
    finally:c.remove()

def test_exec_timeout_removes_container(rt):
    c=rt.new_container(IMG,'t3','agent').start()
    r=c.exec(['sleep','30'],timeout=1)
    assert r['timed_out'] and owned()==[]

def test_refuses_mutable_tag(rt):
    with pytest.raises(DockerError):rt.new_container('node:22','t4','agent')

@pytest.fixture
def real_env(tmp_path):
    cases=tmp_path/'cases';cases.mkdir();make_case(cases,image=IMG,serve=False)
    s=Settings(data_dir=tmp_path/'data',auth_token='t',enable_live=True,cases_dir=cases,acceptance_key=KEY);s.data_dir.mkdir()
    return s,Registry(cases,KEY),Store(s.db_path)

def test_acceptance_procedure_runs_real_evaluators_but_browser_smoke_is_required(rt,real_env):
    s,reg,store=real_env;case=reg.load('synthetic-case')
    ev=accept_case(rt,reg,case,smoke=True)          # no serve profile -> browser_smoke False
    assert ev['independent_fails_before'] is True and ev['independent_passes_reference'] is True
    assert ev['browser_smoke'] is False and not reg.acceptance_status(case)['accepted']

def test_end_to_end_live_flow_in_real_containers_with_scripted_model(rt,real_env):
    s,reg,store=real_env;case=reg.load('synthetic-case');accept(reg,case)
    video=b'synthetic-video-bytes'
    vp=s.data_dir/'v.mp4';vp.write_bytes(video)
    with store.connection() as c:c.execute('INSERT INTO uploads VALUES(?,?,?,?,?,?)',('b'*32,str(vp),'v.mp4',len(video),hashlib.sha256(video).hexdigest(),now()))
    run=store.create({'case_id':'synthetic-case','method':'W1','mode':'live','title':'abc','expected_behavior':'x'*10,'video_id':'b'*32},None)
    store.transition(run['id'],'PREFLIGHT','c')
    budget=Budget(s.db_path,'24.00','3.00')
    script=[('list_files',{}),('read_file',{'path':'src/pagination.mjs'}),('write_reproduction_test',{'content':REPRO_OK}),
            ('run_reproduction',{}),('freeze_reproduction',{}),
            ('write_source',{'path':'src/pagination.mjs','content':CORRECT}),('run_public_regressions',{}),
            ('submit_candidate',{'claim':'fixed'})]
    run_live(store,s,store.get(run['id']),runtime=rt,client=ScriptedClient(budget,script),registry=reg)
    row=store.get(run['id']);assert row['status']=='VERIFIED',row['result']
    assert row['result']['evaluation']['independent']['passed'] and row['result']['frozen_test_sha256']
    assert owned()==[]
    patch=row['result']['patch'];assert '+++ b/src/pagination.mjs' in patch

def test_real_container_false_fix_rejected(rt,real_env):
    s,reg,store=real_env;case=reg.load('synthetic-case');accept(reg,case)
    g=SandboxGateway(case,'W1',rt,'rx',s.data_dir).setup()
    try:
        g.execute('write_reproduction_test',{'content':'import {{ nope\n'})
        assert g.execute('freeze_reproduction',{})['error']=='not_a_valid_reproduction'
        g.execute('write_reproduction_test',{'content':REPRO_OK});assert g.execute('freeze_reproduction',{})['frozen']
        g.execute('write_source',{'path':'src/pagination.mjs','content':(FIX/'false-fix.mjs').read_text()})
        out=g.execute('submit_candidate',{'claim':'fixed'});assert out['files_changed']==['src/pagination.mjs']
    finally:g.close()

def test_model_test_cannot_change_source_or_remove_snapshot(rt,real_env):
    from repropatch.verify import fresh_run, classify
    from repropatch.cases import tree_files
    s,reg,store=real_env;case=reg.load('synthetic-case')
    for attack in ["require('fs').writeFileSync('src/pagination.mjs','changed')", "require('fs').renameSync('/workspace/repo','/workspace/moved')"]:
        result=fresh_run(rt,case,'readonly-proof','untrusted-test',tree_files(case.snapshot_dir),['node','-e',attack])
        assert result['exit_code']!=0
        assert 'EACCES' in result['stderr'] or 'EPERM' in result['stderr']
        assert classify(case,result)['outcome']=='INFRA_ERROR'
