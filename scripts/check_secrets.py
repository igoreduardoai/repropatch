"""Best-effort local scan, not a replacement for full Git-history secret scanning."""
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
SKIP={'.git','.venv','.data','node_modules','__pycache__','.pytest_cache','.private-eval'}
patterns=[re.compile(r'LLM_[0-9]{8,}_[A-Za-z0-9_-]{20,}'),re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'),
          re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
          re.compile(r'(?:META_MODEL_API_KEY|MODEL_API_KEY|BASETEN_API_KEY)[ \t]*=[ \t]*[\"\']?([A-Za-z0-9_.-]{24,})')]
hits=[]
for p in ROOT.rglob('*'):
    if not p.is_file() or p.is_symlink() or any(x in SKIP for x in p.relative_to(ROOT).parts):continue
    if p.name.startswith('.env') and p.name!='.env.example':continue
    if p.stat().st_size>2_000_000:continue
    try:body=p.read_text()
    except UnicodeError:continue
    if any(pattern.search(body) for pattern in patterns):hits.append(str(p.relative_to(ROOT)))
if '--history' in sys.argv:
    import subprocess
    objects=subprocess.check_output(['git','rev-list','--objects','--all'],cwd=ROOT,text=True).splitlines()
    for line in objects:
        oid,_,name=line.partition(' ')
        if not name:continue
        kind=subprocess.check_output(['git','cat-file','-t',oid],cwd=ROOT,text=True).strip()
        if kind!='blob':continue
        body=subprocess.check_output(['git','cat-file','-p',oid],cwd=ROOT).decode('utf-8',errors='ignore')
        if any(pattern.search(body) for pattern in patterns):hits.append('history:'+name+'@'+oid[:12])
if hits:
    print('Potential secrets (values hidden):\n'+'\n'.join(hits));sys.exit(1)
print('Best-effort scan: no supported secret patterns detected. Review history before publication.')
