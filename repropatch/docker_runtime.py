"""Docker CLI runtime for agent/evaluator containers. Fixed argv only, never a shell.

Every container: prebuilt image referenced by immutable image ID (--pull=never),
network none, read-only root, tmpfs workspace, no host mounts, no env from the
host, no Docker socket, no capabilities. Files enter via `docker cp` tar streams
and leave the same way. This is hardening for a dedicated worker host, not a
multi-tenant guarantee (see docs/SECURITY.md).
"""
from dataclasses import dataclass
from pathlib import Path
import io
import json
import re
import select
import shutil
import subprocess
import tarfile
import time
import uuid

OWNER_LABEL='repropatch.owner=live'
NAME=re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,100}$')
IMAGE_ID=re.compile(r'^sha256:[a-f0-9]{64}$')
DISPATCH_SRC=Path(__file__).with_name('sandbox_runtime')/'dispatch.mjs'
DISPATCH_DEST='/tmp/rp'
UID=65534
MAX_TAR=64*1024*1024
MAX_LINE=12*1024*1024

class DockerError(RuntimeError):pass

@dataclass(frozen=True)
class Limits:
    memory:str='2g';cpus:str='2';pids:int=512;shm:str='512m'
    workspace:str='512m';tmp:str='256m'

def _docker(args,timeout=60,stdin:bytes|None=None,check=True):
    if not shutil.which('docker'):raise DockerError('Docker unavailable; no host fallback permitted')
    try:
        r=subprocess.run(['docker',*args],input=stdin,capture_output=True,timeout=timeout)
    except subprocess.TimeoutExpired as exc:raise DockerError('docker command timed out') from exc
    if check and r.returncode!=0:
        raise DockerError('docker '+args[0]+' failed: '+r.stderr.decode(errors='replace')[:300])
    return r

def build_tar(files:dict[str,bytes],executable=())->bytes:
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w') as t:
        for name,body in sorted(files.items()):
            p=Path(name)
            if p.is_absolute() or '..' in p.parts:raise DockerError('unsafe tar member')
            info=tarfile.TarInfo(name);info.size=len(body);info.uid=info.gid=UID
            info.mode=0o755 if name in executable else 0o644;info.mtime=0
            t.addfile(info,io.BytesIO(body))
    return buf.getvalue()

def parse_tar(data:bytes,strip:str='')->dict[str,bytes]:
    """Untrusted tar from a container: regular files only, bounded, no escapes."""
    out={};total=0
    with tarfile.open(fileobj=io.BytesIO(data),mode='r') as t:
        for m in t:
            if m.isdir():continue
            if not m.isreg():raise DockerError('non-regular file in container output')
            name=m.name.removeprefix('./')
            if name.startswith('/') or '..' in Path(name).parts:raise DockerError('unsafe path in container output')
            total+=m.size
            if total>MAX_TAR:raise DockerError('container output too large')
            out[name]=t.extractfile(m).read()
    return out

def image_id(ref:str)->str:
    r=_docker(['image','inspect','--format','{{.Id}}',ref],timeout=20)
    value=r.stdout.decode().strip()
    if not IMAGE_ID.fullmatch(value):raise DockerError('unexpected image id')
    return value

def sweep_owned(run_id:str|None=None)->int:
    """Remove only containers carrying our label (optionally for one run)."""
    flt=['--filter','label='+OWNER_LABEL]
    if run_id:flt+=['--filter','label=repropatch.run='+run_id]
    ids=_docker(['ps','-aq',*flt],timeout=30,check=False).stdout.decode().split()
    ids=[i for i in ids if re.fullmatch(r'[a-f0-9]{12,64}',i)]
    if ids:_docker(['rm','-f',*ids],timeout=60,check=False)
    return len(ids)

class Container:
    def __init__(self,image:str,run_id:str,role:str,limits=Limits()):
        if not IMAGE_ID.fullmatch(image):raise DockerError('Containers start from immutable image IDs only')
        self.image=image;self.run_id=run_id;self.role=role;self.limits=limits
        self.name=f'repropatch-{role}-{uuid.uuid4().hex[:12]}'
        assert NAME.fullmatch(self.name)
        self.proc=None;self.started=False

    def start(self):
        l=self.limits
        _docker(['run','-d','--init','--pull=never','--name',self.name,'--label',OWNER_LABEL,
            '--label','repropatch.run='+self.run_id,'--label','repropatch.role='+self.role,
            '--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges',
            '--user',f'{UID}:{UID}','--pids-limit',str(l.pids),'--memory',l.memory,
            '--memory-swap',l.memory,'--cpus',l.cpus,'--shm-size',l.shm,
            '--tmpfs',f'/workspace:rw,nosuid,nodev,size={l.workspace},uid=0,gid=0,mode=1777',
            '--tmpfs',f'/tmp:rw,nosuid,nodev,size={l.tmp},uid={UID},gid={UID},mode=1777',
            '--env','HOME=/tmp/home','--workdir','/workspace',
            '--entrypoint','node',self.image,'-e','setInterval(()=>{},1e6)'])
        self.started=True
        return self

    def put(self,dest:str,files:dict[str,bytes],executable=(),user=None):
        owner=user or f'{UID}:{UID}'
        # `docker cp` is refused for a read-only rootfs and cannot see tmpfs mounts at all
        # (verified on Docker 29.4.2), so the host-built tar is streamed through the image's
        # `tar` as the unprivileged user, in both directions. Reads are parsed defensively.
        _docker(['exec','-u',owner,self.name,'mkdir','-p',dest],timeout=30)
        _docker(['exec','-i','-u',owner,self.name,'tar','-x','--no-same-owner','--no-same-permissions',
                 '-C',dest,'-f','-'],stdin=build_tar(files,executable),timeout=120)

    def _tar_out(self,directory:str,member:str):
        r=_docker(['exec','-u',f'{UID}:{UID}',self.name,'tar','-c','-C',directory,member],timeout=120,check=False)
        if r.returncode!=0 or len(r.stdout)>MAX_TAR:return None
        return parse_tar(r.stdout)

    def get_dir(self,path:str)->dict[str,bytes]:
        files=self._tar_out(path,'.')
        return {} if files is None else {n.removeprefix('./'):b for n,b in files.items()}

    def get_file(self,path:str)->bytes|None:
        files=self._tar_out(str(Path(path).parent),Path(path).name)
        return next(iter(files.values())) if files and len(files)==1 else None

    def exec(self,argv:list[str],cwd='/workspace',timeout=120,env=None,cap=65536,user=None):
        """Run a reviewed argv inside the container. Timeout destroys the container."""
        args=['exec','-w',cwd]
        if user:args+=['-u',user]
        for k,v in (env or {}).items():args+=['-e',f'{k}={v}']
        t=time.monotonic()
        try:
            r=subprocess.run(['docker',*args,self.name,*argv],capture_output=True,timeout=timeout)
        except subprocess.TimeoutExpired:
            self.remove()
            return {'exit_code':124,'stdout':'','stderr':'Sandbox command timed out','timed_out':True,'duration_ms':round((time.monotonic()-t)*1000)}
        return {'exit_code':r.returncode,'stdout':r.stdout.decode(errors='replace')[-cap:],
                'stderr':r.stderr.decode(errors='replace')[-cap:],'timed_out':False,
                'duration_ms':round((time.monotonic()-t)*1000)}

    def open_dispatcher(self):
        self.put(DISPATCH_DEST,{'dispatch.mjs':DISPATCH_SRC.read_bytes()})
        self.proc=subprocess.Popen(['docker','exec','-i','-w','/workspace',
            self.name,'node',DISPATCH_DEST+'/dispatch.mjs'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL)
        return self

    def call(self,op:dict,timeout=120)->dict:
        """One JSON line out, one JSON line back; any protocol failure kills the sandbox."""
        if not self.proc or self.proc.poll() is not None:raise DockerError('dispatcher not running')
        try:
            self.proc.stdin.write(json.dumps(op).encode()+b'\n');self.proc.stdin.flush()
            deadline=time.monotonic()+timeout;buf=b''
            while b'\n' not in buf:
                left=deadline-time.monotonic()
                if left<=0 or not select.select([self.proc.stdout],[],[],left)[0]:raise DockerError('dispatcher timeout')
                chunk=self.proc.stdout.read1(65536)
                if not chunk:raise DockerError('dispatcher closed')
                buf+=chunk
                if len(buf)>MAX_LINE:raise DockerError('dispatcher response too large')
            return json.loads(buf.split(b'\n',1)[0])
        except (DockerError,OSError,ValueError):
            self.remove();raise

    def remove(self):
        if self.proc:
            try:self.proc.kill()
            except OSError:pass
            self.proc=None
        if self.started:
            _docker(['rm','-f',self.name],timeout=30,check=False);self.started=False

class DockerRuntime:
    def new_container(self,image:str,run_id:str,role:str)->Container:
        return Container(image,run_id,role)
    def sweep(self,run_id=None):return sweep_owned(run_id)
    def image_id(self,ref):return image_id(ref)
