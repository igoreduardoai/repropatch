"""Reviewed case-manifest registry. Only registered, hash-verified cases run live.

Layout (outside Git; REPROPATCH_CASES_DIR, default <data_dir>/cases):
  <case_id>/manifest.json   reviewed manifest (schema_version 2)
  <case_id>/snapshot/       sanitized agent-visible tree at base_commit, no history
  <case_id>/private/reference/  full tree WITH the reference fix (harness only)
  <case_id>/private/evaluator/  maintainer tests (fresh evaluator container only)
  <case_id>/acceptance.json signed evidence; without it live stays blocked
See docs/CASE_REGISTRY.md. Nothing here executes target code.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import hmac
import json
import re
from .security import BoundaryError, sha256

CASE_ID=re.compile(r'^[a-z0-9][a-z0-9-]{2,62}$')
HEX40=re.compile(r'^[a-f0-9]{40}$')
IMAGE_ID=re.compile(r'^sha256:[a-f0-9]{64}$')
FORBIDDEN_PARTS={'.git','.env','.hg','.svn','hidden','oracle','answers','evaluation','__eval__','private'}
MAX_FILE=500_000
MAX_FILES=4000
MAX_TREE=40_000_000
SCHEMA=2

class CaseError(ValueError):pass

def _argv(value,label):
    if not isinstance(value,list) or not value or not all(isinstance(x,str) and x and '\x00' not in x for x in value):
        raise CaseError(f'{label} must be a non-empty argv list')
    return tuple(value)

def _safe_rel(value,label):
    if not isinstance(value,str) or not value:raise CaseError(f'{label} must be a relative path')
    p=Path(value)
    if p.is_absolute() or '..' in p.parts or '\\' in value or '\x00' in value or value.startswith('./'):
        raise CaseError(f'{label} is not a safe relative path')
    return value

def _rel(value,label):
    _safe_rel(value,label)
    if any(x in FORBIDDEN_PARTS or x.startswith('.env') for x in Path(value).parts):
        raise CaseError(f'{label} points to a forbidden location')
    return value

@dataclass(frozen=True)
class Case:
    case_id:str;title:str;repository_url:str;license:str;base_commit:str
    video_origin:str;video_sha256:str;expected_behavior:str
    image_id:str;editable_paths:tuple;readable_suffixes:tuple
    repro_path:str;repro_argv:tuple;public_argv:tuple|None
    serve_argv:tuple|None;serve_url:str|None;serve_ready_s:int
    evaluator_dest:str;evaluator_argv:tuple;failure_pattern:str
    command_timeout_s:int;protocol_version:str;root:Path;manifest_sha256:str

    @property
    def snapshot_dir(self):return self.root/'snapshot'
    @property
    def reference_dir(self):return self.root/'private'/'reference'
    @property
    def evaluator_dir(self):return self.root/'private'/'evaluator'
    @property
    def acceptance_path(self):return self.root/'acceptance.json'

    def public(self):
        """Sanitized view for the UI/API. No host paths, no private locators."""
        return {'case_id':self.case_id,'title':self.title,'repository_url':self.repository_url,
                'license':self.license,'base_commit':self.base_commit,'video_origin':self.video_origin,
                'expected_behavior':self.expected_behavior,'protocol_version':self.protocol_version,
                'has_browser':self.serve_argv is not None}

def parse_manifest(raw:bytes,root:Path)->Case:
    try:d=json.loads(raw)
    except json.JSONDecodeError as exc:raise CaseError('manifest is not valid JSON') from exc
    if not isinstance(d,dict) or d.get('schema_version')!=SCHEMA:raise CaseError('unsupported schema_version')
    cid=d.get('case_id')
    if not isinstance(cid,str) or not CASE_ID.fullmatch(cid) or cid!=root.name:
        raise CaseError('case_id must match its directory name')
    if d.get('model')!='muse-wonder-1.0':raise CaseError('model must be muse-wonder-1.0')
    if d.get('methods')!=['W0','W1']:raise CaseError('methods must be [W0, W1]')
    if not HEX40.fullmatch(str(d.get('base_commit',''))):raise CaseError('base_commit must be a full SHA')
    if not IMAGE_ID.fullmatch(str(d.get('sandbox_image_id',''))):raise CaseError('sandbox_image_id must be a sha256 image ID')
    if d.get('video_origin') not in {'original_issue','independently_recorded_reproduction'}:
        raise CaseError('video_origin must say whether the video is original or our own recording')
    if not re.fullmatch(r'[a-f0-9]{64}',str(d.get('video_sha256',''))):raise CaseError('video_sha256 required')
    for k in ('title','repository_url','license','expected_behavior','protocol_version'):
        if not isinstance(d.get(k),str) or not d[k].strip() or d[k].strip().upper()=='TBD':
            raise CaseError(f'{k} is required')
    if not d['repository_url'].startswith('https://'):raise CaseError('repository_url must be https')
    p=d.get('profile')
    if not isinstance(p,dict):raise CaseError('profile missing')
    editable=tuple(_rel(x,'editable_paths') for x in d.get('editable_paths',[]))
    if not editable:raise CaseError('editable_paths required')
    if any(x.endswith('/')==False for x in editable):raise CaseError('editable_paths must be directory prefixes ending in /')
    repro=p.get('repro',{});ev=p.get('evaluator',{});serve=p.get('serve');pub=p.get('public_regressions')
    pattern=p.get('failure_pattern')
    if not isinstance(pattern,str) or not pattern:raise CaseError('profile.failure_pattern required')
    try:re.compile(pattern)
    except re.error as exc:raise CaseError('profile.failure_pattern invalid') from exc
    url=None
    if serve is not None:
        url=serve.get('url','')
        if not re.fullmatch(r'http://(127\.0\.0\.1|localhost):\d{2,5}(/[\w./-]*)?',url):
            raise CaseError('serve.url must be a loopback URL; public targets need a reviewed allowlist change')
    return Case(cid,d['title'],d['repository_url'],d['license'],d['base_commit'],d['video_origin'],
        d['video_sha256'],d['expected_behavior'],d['sandbox_image_id'],editable,
        tuple(d.get('readable_suffixes',['.js','.mjs','.cjs','.jsx','.ts','.tsx','.json','.md','.css','.html'])),
        _rel(repro.get('path'),'profile.repro.path'),_argv(repro.get('argv'),'profile.repro.argv'),
        _argv(pub['argv'],'profile.public_regressions.argv') if pub else None,
        _argv(serve['argv'],'profile.serve.argv') if serve else None,url,
        int(serve.get('ready_timeout_s',30)) if serve else 0,
        _safe_rel(ev.get('dest'),'profile.evaluator.dest'),
        _argv(ev.get('argv'),'profile.evaluator.argv'),pattern,
        int(p.get('command_timeout_s',120)),d['protocol_version'],root,sha256(raw))

def tree_files(root:Path)->dict[str,bytes]:
    """Read a sanitized tree. Symlinks, forbidden names and oversize trees are errors."""
    if not root.is_dir() or root.is_symlink():raise CaseError(f'missing tree: {root.name}')
    files={};total=0
    for path in sorted(root.rglob('*')):
        rel=path.relative_to(root)
        if path.is_symlink():raise CaseError(f'symlink in tree: {rel}')
        if any(x in {'.git','.env'} or x.startswith('.env') for x in rel.parts):
            raise CaseError(f'forbidden path in tree: {rel}')
        if path.is_dir():continue
        if not path.is_file():raise CaseError(f'special file in tree: {rel}')
        body=path.read_bytes();total+=len(body)
        if len(body)>MAX_FILE and rel.suffix not in {'.png','.woff2'}:raise CaseError(f'oversized file: {rel}')
        if len(files)>=MAX_FILES or total>MAX_TREE:raise CaseError('tree too large')
        files[rel.as_posix()]=body
    return files

def tree_hash(files:dict[str,bytes])->str:
    h=hashlib.sha256()
    for name in sorted(files):
        h.update(name.encode()+b'\0'+sha256(files[name]).encode()+b'\n')
    return h.hexdigest()

def canonical(obj)->bytes:
    return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()

def sign_acceptance(evidence:dict,key:str)->dict:
    if len(key)<16:raise CaseError('acceptance key too short')
    body={k:v for k,v in evidence.items() if k!='signature'}
    return {**body,'signature':hmac.new(key.encode(),canonical(body),'sha256').hexdigest()}

class Registry:
    def __init__(self,root:Path,acceptance_key:str=''):
        self.root=root;self.key=acceptance_key

    def ids(self):
        if not self.root.is_dir():return []
        return sorted(p.name for p in self.root.iterdir() if p.is_dir() and CASE_ID.fullmatch(p.name))

    def load(self,case_id:str)->Case:
        if not isinstance(case_id,str) or not CASE_ID.fullmatch(case_id):raise CaseError('unknown case')
        root=(self.root/case_id)
        if not root.is_dir() or root.is_symlink() or not (root/'manifest.json').is_file():raise CaseError('unknown case')
        return parse_manifest((root/'manifest.json').read_bytes(),root)

    def hashes(self,case:Case)->dict:
        return {'manifest_sha256':case.manifest_sha256,
                'snapshot_tree_sha256':tree_hash(tree_files(case.snapshot_dir)),
                'reference_tree_sha256':tree_hash(tree_files(case.reference_dir)),
                'evaluator_tree_sha256':tree_hash(tree_files(case.evaluator_dir))}

    def acceptance_status(self,case:Case,live_image_id:str|None=None)->dict:
        """Live is allowed only with signed evidence matching the current bytes."""
        def no(reason):return {'accepted':False,'reason':reason}
        if not self.key:return no('REPROPATCH_ACCEPTANCE_KEY not configured')
        if not case.acceptance_path.is_file():return no('no acceptance evidence')
        try:
            ev=json.loads(case.acceptance_path.read_text())
            expected=sign_acceptance(ev,self.key)['signature']
            if not isinstance(ev.get('signature'),str) or not hmac.compare_digest(ev['signature'],expected):
                return no('acceptance signature invalid')
            current=self.hashes(case)
        except (CaseError,json.JSONDecodeError,OSError,TypeError) as exc:return no(f'acceptance unreadable: {exc}')
        for k,v in current.items():
            if ev.get(k)!=v:return no(f'{k} changed since acceptance')
        if ev.get('case_id')!=case.case_id or ev.get('sandbox_image_id')!=case.image_id:
            return no('acceptance does not match manifest image/case')
        if live_image_id is not None and live_image_id!=case.image_id:return no('local image differs from manifest')
        if not (ev.get('independent_fails_before') is True and ev.get('independent_passes_reference') is True
                and ev.get('browser_smoke') is True):
            return no('acceptance evidence incomplete')
        return {'accepted':True,'reason':'signed evidence matches current bytes','signature':ev['signature']}

    def accepted_cases(self):
        out=[]
        for cid in self.ids():
            try:
                c=self.load(cid)
                if self.acceptance_status(c)['accepted']:out.append(c)
            except CaseError:continue
        return out

def check_agent_path(case:Case,relative:str,write=False)->str:
    """Host-side path policy shared by every file tool."""
    if not isinstance(relative,str):raise BoundaryError('Invalid path')
    if relative.startswith('/'):raise BoundaryError('Absolute paths and traversal are forbidden')
    rel=relative.rstrip('/') or '.'
    if rel=='.':return rel
    parts=Path(rel).parts
    if '\\' in rel or '\x00' in rel or Path(rel).is_absolute() or '..' in parts:
        raise BoundaryError('Absolute paths and traversal are forbidden')
    if any(x in FORBIDDEN_PARTS or x.startswith('.env') or (x.startswith('.') and x not in {'.'}) for x in parts):
        raise BoundaryError('This path is outside agent visibility')
    if 'node_modules' in parts:raise BoundaryError('This path is outside agent visibility')
    return rel
