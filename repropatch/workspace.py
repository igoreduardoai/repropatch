"""Read/write capability boundary. Not a substitute for Docker isolation."""
from pathlib import Path
from .security import safe_path, BoundaryError, sha256

FORBIDDEN={'.git','.env','evaluation','hidden','oracle','answers','node_modules'}

class Workspace:
    def __init__(self,root:Path,editable:tuple[str,...]=('src/',),method='W1'):
        self.root=root.resolve();self.editable=editable;self.method=method
        self.frozen=False;self.repro_sha=None

    def resolve(self,relative:str):
        parts=Path(relative).parts
        if any(p in FORBIDDEN or p.startswith('.env') for p in parts):
            raise BoundaryError('This path is outside agent visibility')
        return safe_path(self.root,relative)

    def read(self,relative:str):
        path=self.resolve(relative)
        if path.suffix not in {'.js','.mjs','.cjs','.jsx','.ts','.tsx','.json','.md','.css','.html'}:
            raise BoundaryError('File type not allowed')
        if not path.is_file() or path.stat().st_size>200_000:
            raise BoundaryError('Missing file or file exceeds read limit')
        return path.read_text(encoding='utf-8')

    def write_source(self,relative:str,content:str):
        if self.method=='W1' and not self.frozen:
            raise BoundaryError('Source edits require a frozen reproduction test')
        if not any(relative.startswith(p) for p in self.editable):
            raise BoundaryError('Path is not in editable source scope')
        path=self.resolve(relative)
        if path.suffix not in {'.js','.mjs','.jsx','.ts','.tsx','.css'}:
            raise BoundaryError('Source file type not permitted')
        if len(content.encode())>100_000:raise BoundaryError('Write exceeds limit')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
        return {'path':relative,'sha256':sha256(content.encode())}

    def write_reproduction(self,content:str):
        if self.frozen:raise BoundaryError('Reproduction test is immutable')
        if len(content.encode())>50_000:raise BoundaryError('Test exceeds limit')
        path=self.root/'repro.spec.ts';path.write_text(content);return path

    def freeze(self,confirmed_issue_failure:bool,original_commit:str):
        # This boolean must be supplied by the harness's reviewed validation step,
        # not trusted directly from an LLM argument.
        if not confirmed_issue_failure or not original_commit:
            raise BoundaryError('Independent confirmation of the reported assertion failure is required')
        if self.frozen:raise BoundaryError('Already frozen')
        path=self.root/'repro.spec.ts'
        if not path.is_file():raise BoundaryError('No reproduction test')
        self.repro_sha=sha256(path.read_bytes());self.frozen=True
        return {'test_sha256':self.repro_sha,'original_commit':original_commit}

    def verify_integrity(self):
        if self.frozen and sha256((self.root/'repro.spec.ts').read_bytes())!=self.repro_sha:
            raise BoundaryError('Frozen test integrity violation')
