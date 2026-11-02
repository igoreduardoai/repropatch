"""Test-only helpers. FakeRuntime runs test-owned node scripts in temp dirs on the
host to mimic container semantics; it is NEVER used outside tests/. Real isolation
is exercised separately in test_docker_live.py."""
import json
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from repropatch.cases import sign_acceptance, Registry, tree_files
from repropatch.budget import Budget

FIX=Path(__file__).resolve().parents[1]/'fixtures'/'pagination'
KEY='unit-test-acceptance-key'
IMAGE='sha256:'+'a'*64

REPRO_OK="""import assert from 'node:assert/strict';
import {pageRows} from '../src/pagination.mjs';
const data=[{id:1,status:'active'},{id:2,status:'inactive'},{id:3,status:'active'},{id:4,status:'inactive'},{id:5,status:'active'},{id:6,status:'active'}];
const a=pageRows(data,'active',2,2);
assert.deepEqual(a.rows.map(r=>r.id),[5,6]);
"""
REPRO_SYNTAX="import {{{ broken\n"
REPRO_ALWAYS_FAIL="import assert from 'node:assert/strict';\nassert.equal(1,2);\n"
PUBLIC="""import assert from 'node:assert/strict';
import {pageRows} from '../src/pagination.mjs';
const d=[{id:1,status:'active'},{id:2,status:'inactive'},{id:3,status:'active'},{id:4,status:'inactive'}];
assert.deepEqual(pageRows(d,'inactive',1,2).rows.map(r=>r.id),[2,4]);
"""
HIDDEN="""import assert from 'node:assert/strict';
import {pageRows} from '../src/pagination.mjs';
const rows=Array.from({length:11},(_,i)=>({id:100+i,status:i%3===0?'inactive':'active'}));
for(const s of ['active','inactive'])for(const p of [1,2,3]){
 const w=rows.filter(r=>r.status===s);
 assert.deepEqual(pageRows(rows,s,p,2),{rows:w.slice((p-1)*2,p*2),total:w.length});}
"""
FALSE_FIX=(FIX/'false-fix.mjs').read_text()
CORRECT=(FIX/'correct.mjs').read_text()

def make_case(root:Path,case_id='synthetic-case',serve=True,video=b'synthetic-video-bytes',image=IMAGE):
    import hashlib
    d=root/case_id
    (d/'snapshot'/'src').mkdir(parents=True);(d/'snapshot'/'tests').mkdir()
    (d/'snapshot'/'src'/'pagination.mjs').write_text((FIX/'buggy.mjs').read_text())
    (d/'snapshot'/'tests'/'public.mjs').write_text(PUBLIC)
    (d/'snapshot'/'README.md').write_text('# synthetic\n')
    (d/'private'/'reference'/'src').mkdir(parents=True);(d/'private'/'reference'/'tests').mkdir()
    (d/'private'/'reference'/'src'/'pagination.mjs').write_text(CORRECT)
    (d/'private'/'reference'/'tests'/'public.mjs').write_text(PUBLIC)
    (d/'private'/'reference'/'README.md').write_text('# synthetic\n')
    (d/'private'/'evaluator').mkdir(parents=True)
    (d/'private'/'evaluator'/'check.mjs').write_text(HIDDEN)
    profile={'repro':{'path':'tests/repro.mjs','argv':['node','tests/repro.mjs']},
             'public_regressions':{'argv':['node','tests/public.mjs']},
             'evaluator':{'dest':'maintainer','argv':['node','maintainer/check.mjs']},
             'failure_pattern':'AssertionError','command_timeout_s':20}
    if serve:profile['serve']={'argv':['node','server.mjs'],'url':'http://127.0.0.1:3000/','ready_timeout_s':5}
    manifest={'schema_version':2,'case_id':case_id,'title':'Active filter disappears on page 2',
      'repository_url':'https://example.invalid/synthetic','license':'MIT','base_commit':'b'*40,
      'video_origin':'independently_recorded_reproduction','video_sha256':hashlib.sha256(video).hexdigest(),
      'expected_behavior':'Keep the active filter on every page.','sandbox_image_id':image,
      'editable_paths':['src/'],'protocol_version':'repropatch-pilot-v1','methods':['W0','W1'],
      'model':'muse-wonder-1.0','profile':profile}
    (d/'manifest.json').write_text(json.dumps(manifest))
    return d

def accept(registry:Registry,case,**over):
    ev={'schema_version':1,'case_id':case.case_id,'sandbox_image_id':case.image_id,**registry.hashes(case),
        'independent_fails_before':True,'independent_passes_reference':True,'browser_smoke':True,**over}
    case.acceptance_path.write_text(json.dumps(sign_acceptance(ev,registry.key)))
    return ev

class FakeContainer:
    def __init__(self,rt,image,run_id,role):
        self.rt=rt;self.image=image;self.run_id=run_id;self.role=role
        self.dir=Path(tempfile.mkdtemp(prefix='fake-container-'));self.alive=False;self.started=False
    def start(self):self.alive=self.started=True;self.rt.live.add(self);return self
    def put(self,dest,files,executable=(),user=None):
        self.rt.puts.append((self.role,{n:b for n,b in files.items()}))
        for n,b in files.items():
            p=self.dir/Path(dest).relative_to('/')/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    def _p(self,path):return self.dir/Path(path).relative_to('/')
    def get_file(self,path):
        p=self._p(path);return p.read_bytes() if p.is_file() else None
    def get_dir(self,path):
        p=self._p(path)
        return {f.relative_to(p).as_posix():f.read_bytes() for f in sorted(p.rglob('*')) if f.is_file()} if p.is_dir() else {}
    def open_dispatcher(self):return self
    def exec(self,argv,cwd='/workspace',timeout=60,env=None,cap=65536,user=None):
        if user=='0:0' and argv[0]=='chmod':return {'exit_code':0,'stdout':'','stderr':'','timed_out':False}
        self.rt.execs.append((self.role,tuple(argv)))
        r=subprocess.run(['node',*argv[1:]] if argv[0]=='node' else argv,cwd=self._p(cwd),capture_output=True,timeout=timeout)
        return {'exit_code':r.returncode,'stdout':r.stdout.decode()[-cap:],'stderr':r.stderr.decode()[-cap:],
                'timed_out':False,'duration_ms':1}
    def call(self,op,timeout=60):
        o=op['op'];repo=self._p('/workspace/repo')
        try:
            if o=='list':return {'ok':True,'result':{'entries':[{'name':x.name,'type':'dir' if x.is_dir() else 'file'} for x in sorted((repo/op.get('path','.')).iterdir())]}}
            if o=='read':return {'ok':True,'result':{'content':(repo/op['path']).read_text()}}
            if o=='write':
                p=repo/op['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(op['content']);return {'ok':True,'result':{'written':True}}
            if o=='exec':return {'ok':True,'result':self.exec(op['argv'],'/workspace/repo',timeout)}
            if o=='serve_start':return {'ok':True,'result':{'started':True}}
            if o in {'observe','action'}:
                import base64
                return {'ok':True,'result':{'url':'http://127.0.0.1:3000/','title':'t','text':'rows api_key=sk-abcdefghijklmnopqrstuv',
                        'screenshot_b64':base64.b64encode(b'\x89PNG\r\n'+b'0'*20).decode()}}
        except (OSError,FileNotFoundError) as exc:return {'ok':False,'error':str(exc)}
        return {'ok':False,'error':'unknown op'}
    def remove(self):
        if self.started:self.rt.live.discard(self);self.started=False;self.alive=False
        shutil.rmtree(self.dir,ignore_errors=True)

class FakeRuntime:
    def __init__(self,image=IMAGE):self.live=set();self.execs=[];self.puts=[];self.created=[];self.image=image
    def new_container(self,image,run_id,role):
        assert image.startswith('sha256:'),'containers must start from immutable image IDs'
        c=FakeContainer(self,image,run_id,role);self.created.append(c);return c
    def sweep(self,run_id=None):
        n=len(self.live)
        for c in list(self.live):c.remove()
        return n
    def image_id(self,ref):return self.image

class ScriptedClient:
    """Stands in for MetaClient: plays scripted tool calls and exercises the REAL ledger."""
    def __init__(self,budget:Budget,script):
        self.budget=budget;self.script=list(script);self.uploaded=[];self.calls=0
    def upload_video(self,path):self.uploaded.append(path);return 'file_test'
    def respond(self,run_id,inputs,tools,budget,max_output=1800):
        self.calls+=1;rid=uuid.uuid4().hex
        self.budget.reserve(rid,run_id,1000,max_output)
        self.budget.settle(rid,900,200,0)
        step=self.script.pop(0)
        if isinstance(step,Exception):raise step
        name,args=step
        return {'id':f'resp_{self.calls}','usage':{'input_tokens':900,'output_tokens':200},
                'output':[{'type':'function_call','name':name,'call_id':f'c{self.calls}','arguments':json.dumps(args)}]}
    @staticmethod
    def public_usage(response):return {'response_id':response['id'],'input_tokens':900,'output_tokens':200,'cached_tokens':0}
