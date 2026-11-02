"""Reviewed sandbox Gateway for AgentLoop. The model never picks a command.

All commands come from the case profile; file tools run through the fixed
in-container dispatcher after host-side path policy; confirmation, freezing and
candidate extraction use bytes the HOST reads out via `docker cp`, not claims
from inside the container. No host execution of target or model-written code.
"""
import difflib
import re
from pathlib import Path
from .cases import Case,check_agent_path,tree_files,tree_hash
from .fixture import Cancelled
from .security import BoundaryError,sha256,freeze_bytes
from .verify import classify,confirm_reproduction,redact,REPO,fresh_run

SOURCE_SUFFIX={'.js','.mjs','.cjs','.jsx','.ts','.tsx','.css','.json','.html'}
MAX_BROWSER=40
MAX_FREEZE_TRIES=5
MAX_TOOL_OUT=6000

class GatewayError(ValueError):pass

def _obj(props,required=()):
    return {'type':'object','properties':props,'required':list(required),'additionalProperties':False}

def apply_unified_diff(original:str|None,diff:str,path:str)->str:
    """Strict single-file hunk applier. Context must match exactly or it fails."""
    lines=original.splitlines(keepends=True) if original else []
    out=[];pos=0;hunks=0
    body=diff.splitlines(keepends=True);i=0
    while i<len(body):
        m=re.match(r'@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@',body[i])
        if not m:i+=1;continue
        hunks+=1;start=max(int(m.group(1))-1,0)
        if original is None and start>0:raise GatewayError('New file hunk must start at line 1')
        if start<pos:raise GatewayError('Overlapping hunks')
        out+=lines[pos:start];pos=start;i+=1
        while i<len(body) and not body[i].startswith('@@'):
            ln=body[i]
            if ln.startswith('\\'):i+=1;continue
            tag,text=ln[:1],ln[1:]
            if tag==' ' or (tag=='\n'):
                text=text if tag==' ' else '\n'
                if pos>=len(lines) or lines[pos].rstrip('\n')!=text.rstrip('\n'):raise GatewayError(f'Context mismatch in {path}')
                out.append(lines[pos]);pos+=1
            elif tag=='-':
                if pos>=len(lines) or lines[pos].rstrip('\n')!=text.rstrip('\n'):raise GatewayError(f'Removed line mismatch in {path}')
                pos+=1
            elif tag=='+':out.append(text if text.endswith('\n') else text+'\n')
            else:raise GatewayError('Malformed patch line')
            i+=1
    if not hunks:raise GatewayError('Patch has no hunks')
    out+=lines[pos:]
    return ''.join(out)

def split_patch(patch:str):
    """Yield (path, diff_text) per file. Renames, deletions and absolute paths are refused."""
    files=[];cur=None
    for ln in patch.splitlines(keepends=True):
        if ln.startswith('--- '):
            cur={'old':ln[4:].strip().split('\t')[0],'new':None,'lines':[]};continue
        if ln.startswith('+++ ') and cur is not None and cur['new'] is None:
            cur['new']=ln[4:].strip().split('\t')[0];files.append(cur);continue
        if cur is not None and cur['new'] is not None:cur['lines'].append(ln)
    if not files:raise GatewayError('No file headers found; use a unified diff')
    out=[]
    for f in files:
        if f['new']=='/dev/null':raise GatewayError('Deleting files is not allowed')
        new=re.sub(r'^b/','',f['new']);old=re.sub(r'^a/','',f['old'])
        if f['old']!='/dev/null' and old!=new:raise GatewayError('Renames are not allowed')
        out.append((new,''.join(f['lines']),f['old']=='/dev/null'))
    return out

class SandboxGateway:
    def __init__(self,case:Case,method:str,runtime,run_id:str,data_dir:Path,
                 on_stage=lambda s,m:None,on_event=lambda m,d:None,on_artifact=lambda n,b,t:None,
                 should_cancel=lambda:False):
        if method not in {'W0','W1'}:raise GatewayError('Unknown method')
        self.case=case;self.method=method;self.runtime=runtime;self.run_id=run_id
        self.evidence=data_dir/'frozen'/run_id
        self.on_stage=on_stage;self.on_event=on_event;self.on_artifact=on_artifact;self.should_cancel=should_cancel
        self.c=None;self.base=None;self.test_written=None
        self.frozen=None;self.frozen_bytes=None;self.edited=set();self.submitted=False
        self.candidate=None;self.browser_calls=0;self.freeze_tries=0;self.served=False;self.seq=0

    # -- lifecycle ---------------------------------------------------------------
    def setup(self):
        self.base=tree_files(self.case.snapshot_dir)
        self.c=self.runtime.new_container(self.case.image_id,self.run_id,'agent').start()
        self.c.put('/workspace',{'repo/'+n:b for n,b in self.base.items()})
        self.c.open_dispatcher()
        return self

    def close(self):
        if self.c:self.c.remove();self.c=None

    def _call(self,op,**kw):
        self.seq+=1
        reply=self.c.call({'op':op,'id':self.seq,**kw},timeout=kw.get('timeout_ms',60000)/1000+15)
        if not reply.get('ok'):raise GatewayError(str(reply.get('error','sandbox error'))[:300])
        return reply['result']

    # -- tools -------------------------------------------------------------------
    def definitions(self):
        path={'path':{'type':'string','description':'Relative path inside the repository.'}}
        tools=[
          ('list_files','List a directory of the sandboxed repository snapshot.',_obj(path)),
          ('read_file','Read a source/text file (secrets redacted, size limited).',_obj(path,['path'])),
          ('write_reproduction_test','Write the single reproduction test file. Not possible after it is frozen.',
             _obj({'content':{'type':'string'}},['content'])),
          ('run_reproduction','Run the reproduction test in your sandbox. Feedback only; it does not confirm anything.',_obj({})),
          ('freeze_reproduction','Ask the harness to confirm the test fails on the original code for the reported assertion and passes on the expected behavior, then freeze it by hash.',_obj({})),
          ('write_source','Replace an editable source file with new content.',
             _obj({**path,'content':{'type':'string'}},['path','content'])),
          ('apply_patch','Apply a unified diff to editable source files.',_obj({'patch':{'type':'string'}},['patch'])),
          ('run_public_regressions','Run the reviewed public regression command. Hidden tests are never included.',_obj({})),
          ('submit_candidate','Finalize the candidate. No tool works afterwards.',_obj({'claim':{'type':'string'}},['claim'])),
        ]
        if self.case.serve_argv:
            tools[2:2]=[
              ('browser_observe','Open the reported app (loopback only) and return page text; optional relative URL.',
                 _obj({'url':{'type':'string'}})),
              ('browser_action','Perform a real browser action on the app: click, fill, press, select, scroll or wait.',
                 _obj({'kind':{'type':'string','enum':['click','fill','press','select','scroll','wait']},
                       'selector':{'type':'string'},'value':{'type':'string'}},['kind'])),
            ]
        return [{'type':'function','name':n,'description':d,'parameters':p} for n,d,p in tools]

    def execute(self,name:str,arguments:dict)->dict:
        if self.should_cancel():raise Cancelled()
        if self.submitted:raise GatewayError('The candidate was submitted; no further tools are available')
        if self.c is None:raise GatewayError('Sandbox is not running')
        fn=getattr(self,'t_'+name,None)
        if fn is None or name not in {d['name'] for d in self.definitions()}:raise GatewayError('Unregistered tool')
        try:return fn(**{k:v for k,v in arguments.items() if k in self._params(name)})
        except TypeError as exc:raise GatewayError('Invalid tool arguments') from exc

    def _params(self,name):
        d=next(x for x in self.definitions() if x['name']==name)
        return set(d['parameters']['properties'])

    def t_list_files(self,path='.'):
        return self._call('list',path=check_agent_path(self.case,path))

    def t_read_file(self,path):
        rel=check_agent_path(self.case,path)
        if Path(rel).suffix not in self.case.readable_suffixes:raise BoundaryError('File type not allowed')
        r=self._call('read',path=rel)
        return {'path':rel,'content':redact(r['content'])}

    def _browser(self,op,**kw):
        self.browser_calls+=1
        if self.browser_calls>MAX_BROWSER:raise GatewayError('Browser call limit reached')
        if not self.served:
            self._call('serve_start',argv=list(self.case.serve_argv),url=self.case.serve_url,
                       ready_timeout_s=self.case.serve_ready_s,timeout_ms=(self.case.serve_ready_s+10)*1000)
            self.served=True
        r=self._call(op,**kw)
        import base64
        png=base64.b64decode(r.pop('screenshot_b64','') or b'')
        shot=None
        if png.startswith(b'\x89PNG'):
            shot=sha256(png);self.on_artifact(f'browser-{self.browser_calls:02d}.png',png,'image/png')
        return {'url':r.get('url'),'title':r.get('title'),'text':redact(r.get('text',''))[:MAX_TOOL_OUT],
                'screenshot_sha256':shot,'note':'Screenshot stored as evidence; text snapshot only is returned here.'}

    def t_browser_observe(self,url=None):
        return self._browser('observe',url=url if isinstance(url,str) and url else None)

    def t_browser_action(self,kind,selector=None,value=None):
        if kind not in {'click','fill','press','select','scroll','wait'}:raise GatewayError('Unknown browser action')
        return self._browser('action',kind=kind,selector=selector if isinstance(selector,str) else None,
                             value=value if isinstance(value,str) else None)

    def t_write_reproduction_test(self,content):
        if self.frozen:raise BoundaryError('Reproduction test is immutable after freeze')
        if not isinstance(content,str) or len(content.encode())>50_000:raise BoundaryError('Test exceeds limit')
        self._call('write',path=self.case.repro_path,content=content)
        self.test_written=sha256(content.encode())
        return {'path':self.case.repro_path,'sha256':self.test_written}

    def t_run_reproduction(self):
        if not self.test_written and not self.frozen:raise GatewayError('Write a reproduction test first')
        files=self.c.get_dir(REPO)
        r=fresh_run(self.runtime,self.case,self.run_id,'agent-repro',files,self.case.repro_argv)
        return {'exit_code':r['exit_code'],'timed_out':r['timed_out'],
                'output':redact((r['stdout']+'\n'+r['stderr'])[-MAX_TOOL_OUT:]),
                'classification_unverified':classify(self.case,r)['outcome'],
                'note':'Agent-sandbox result. Only freeze_reproduction confirms a valid failure.'}

    def t_freeze_reproduction(self):
        if self.frozen:raise GatewayError('Already frozen')
        if not self.test_written:raise GatewayError('Write a reproduction test first')
        self.freeze_tries+=1
        if self.freeze_tries>MAX_FREEZE_TRIES:raise GatewayError('Freeze attempt limit reached')
        # Host reads the bytes itself; the in-container copy is not trusted.
        body=self.c.get_file(f'{REPO}/{self.case.repro_path}')
        if body is None or len(body)>50_000:raise GatewayError('Reproduction test missing')
        v=confirm_reproduction(self.runtime,self.case,self.run_id,body)
        self.on_event('reproduction_check',{'baseline':v['baseline'],'reference':v['reference'],'confirmed':v['confirmed']})
        if not v['confirmed']:
            b=v['baseline']['outcome']
            if b!='ASSERTION_FAILED':
                return {'error':'not_a_valid_reproduction','reason':b+':'+v['baseline'].get('reason',''),
                        'excerpt':v['baseline_excerpt'],
                        'hint':'Setup, syntax, import, timeout or browser errors are not reproductions.'}
            return {'error':'test_not_sensitive_to_expected_behavior',
                    'reason':'The test fails on the original code but also fails on the expected behavior; fix the test.'}
        ext=Path(self.case.repro_path).suffix or '.txt'
        ev=freeze_bytes(body,self.evidence,'reproduction.frozen'+ext)
        self.frozen={'test_sha256':ev['sha256'],'path':ev['path']};self.frozen_bytes=body
        self.on_stage('FROZEN','Reproduction confirmed (expected assertion fails on baseline, passes on reference) and frozen.')
        return {'frozen':True,'test_sha256':ev['sha256']}

    def _writable(self,rel):
        rel=check_agent_path(self.case,rel,write=True)
        if self.method=='W1' and not self.frozen:
            raise BoundaryError('Source edits require a frozen reproduction test')
        if rel==self.case.repro_path:raise BoundaryError('The reproduction test is not source')
        if not any(rel.startswith(p) for p in self.case.editable_paths):raise BoundaryError('Path is not in editable source scope')
        if Path(rel).suffix not in SOURCE_SUFFIX:raise BoundaryError('Source file type not permitted')
        return rel

    def _write_source(self,rel,content):
        rel=self._writable(rel)
        if len(content.encode())>100_000:raise BoundaryError('Write exceeds limit')
        self.on_stage('PATCHING','Source edits started.')
        self._call('write',path=rel,content=content);self.edited.add(rel)
        return {'path':rel,'sha256':sha256(content.encode())}

    def t_write_source(self,path,content):
        if not isinstance(content,str):raise BoundaryError('content must be text')
        return self._write_source(path,content)

    def t_apply_patch(self,patch):
        if not isinstance(patch,str) or len(patch.encode())>200_000:raise BoundaryError('Patch too large')
        results=[]
        planned=[]
        for rel,diff,is_new in split_patch(patch):
            rel=self._writable(rel)
            try:old=None if is_new else self._call('read',path=rel)['content']
            except GatewayError:
                if not is_new:raise
                old=None
            planned.append((rel,apply_unified_diff(old,diff,rel)))
        for rel,new in planned:results.append(self._write_source(rel,new))
        return {'applied':results}

    def t_run_public_regressions(self):
        if not self.case.public_argv:raise GatewayError('No public regression command is configured for this case')
        files=self.c.get_dir(REPO)
        r=fresh_run(self.runtime,self.case,self.run_id,'agent-public',files,self.case.public_argv)
        return {'exit_code':r['exit_code'],'timed_out':r['timed_out'],
                'output':redact((r['stdout']+'\n'+r['stderr'])[-MAX_TOOL_OUT:])}

    def t_submit_candidate(self,claim):
        if self.method=='W1' and not self.frozen:
            raise GatewayError('W1 requires a frozen reproduction before submitting')
        # Host-side extraction: diff the editable trees against the pristine snapshot.
        changes={};deleted=[];tampered=False
        for prefix in self.case.editable_paths:
            now=self.c.get_dir(f'{REPO}/{prefix.rstrip("/")}')
            for rel,body in now.items():
                full=prefix+rel
                if self.base.get(full)!=body:changes[full]=body
            for full in self.base:
                if full.startswith(prefix) and full[len(prefix):] not in now:deleted.append(full)
        if self.frozen:
            cur=self.c.get_file(f'{REPO}/{self.case.repro_path}')
            tampered=cur is None or sha256(cur)!=self.frozen['test_sha256']
        parts=[]
        for full in sorted(changes):
            old=self.base.get(full,b'').decode(errors='replace').splitlines(True)
            parts.append(''.join(difflib.unified_diff(old,changes[full].decode(errors='replace').splitlines(True),
                         fromfile='a/'+full,tofile='b/'+full)))
        for full in sorted(deleted):
            parts.append(''.join(difflib.unified_diff(self.base[full].decode(errors='replace').splitlines(True),[],
                         fromfile='a/'+full,tofile='/dev/null')))
        patch=''.join(parts)
        snapshot={**self.base,**changes}
        for name in deleted:snapshot.pop(name,None)
        tree=tree_hash(snapshot)
        self.candidate={'changes':changes,'deleted':sorted(deleted),'patch':patch,
                        'patch_sha256':sha256(patch.encode()),'candidate_sha256':tree,
                        'claim':str(claim)[:1000],'frozen_test_sha256':self.frozen['test_sha256'] if self.frozen else None,
                        'workspace_test_modified':tampered}
        self.submitted=True
        self.close()
        return {'submitted':True,'candidate_sha256':tree,'patch_sha256':self.candidate['patch_sha256'],
                'files_changed':sorted([*changes,*deleted]),'frozen_test_sha256':self.candidate['frozen_test_sha256']}
