import json, subprocess, shutil, sys, hashlib
from pathlib import Path
ROOT=Path('/workspace/rp-cases-2026-11-02'); SRC=ROOT/'van-src'; SPEC=ROOT/'spec'; CASES=ROOT/'data'/'cases'
IMAGE=subprocess.check_output(['docker','image','inspect','--format','{{.Id}}','repropatch-browser:pilot-v4'],text=True).strip()
C=[dict(id='vanx-raw-356',fix='17d5ce5eae691f9839b68454154d03a293a51368',files=['src/van.js','x/src/van-x.js'],edit=['x/src/'],
  title='vanX.raw breaks on reactive arrays and class instances',
  expected='The profile snapshot reads values through vanX.raw and must show "Name: Ada Lovelace", "Scores recorded: 3" and "Scores: 90%, 85%, 77%". vanX.raw must work for reactive arrays (length, map) and class instances (methods), while values read through vanX.raw do not subscribe to later changes.'),
]
def show(rev,path): return subprocess.check_output(['git','-C',str(SRC),'show',f'{rev}:{path}'])
lic=show('HEAD','LICENSE')
for c in C:
    base=subprocess.check_output(['git','-C',str(SRC),'rev-parse',c['fix']+'^'],text=True).strip()
    c['base']=base
    d=CASES/c['id']
    if d.exists(): shutil.move(str(d),str(d)+'.bak-2026-11-02-'+hashlib.sha1(str(d.stat().st_mtime).encode()).hexdigest()[:6])
    for tree,rev in (('snapshot',base),('private/reference',c['fix'])):
        t=d/tree; t.mkdir(parents=True)
        for f in c['files']:
            p=t/f; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(show(rev,f))
        (t/'demo.mjs').write_bytes((SPEC/c['id']/'demo.mjs').read_bytes())
        (t/'tests').mkdir(); (t/'tests/README.md').write_bytes((SPEC/'common-README.md').read_bytes())
        (t/'tests/public.cjs').write_bytes((SPEC/c['id']/'public.cjs').read_bytes())
        (t/'LICENSE').write_bytes(lic)
    ev=d/'private/evaluator'; ev.mkdir(parents=True); (ev/'check.cjs').write_bytes((SPEC/c['id']/'check.cjs').read_bytes())
    vid=ROOT/'videos'/(c['id']+'.mp4')
    vsha=hashlib.sha256(vid.read_bytes()).hexdigest() if vid.exists() else '0'*64
    m={"schema_version":2,"case_id":c['id'],"title":c['title'],"repository_url":"https://github.com/vanjs-org/van","license":"MIT",
       "base_commit":base,"video_origin":"independently_recorded_reproduction","video_sha256":vsha,"expected_behavior":c['expected'],
       "sandbox_image_id":IMAGE,"editable_paths":c['edit'],"protocol_version":"repropatch-pilot-v1","methods":["W0","W1"],"model":"muse-wonder-1.0",
       "profile":{"repro":{"path":"tests/repro.cjs","argv":["node","/opt/repropatch/run-test.cjs","/workspace/repo/tests/repro.cjs"]},
         "public_regressions":{"argv":["node","/opt/repropatch/run-test.cjs","/workspace/repo/tests/public.cjs"]},
         "serve":{"argv":["node","/opt/repropatch/serve.cjs"],"url":"http://127.0.0.1:4173/","ready_timeout_s":30},
         "evaluator":{"dest":"maintainer","argv":["node","/opt/repropatch/run-test.cjs","/workspace/repo/maintainer/check.cjs"]},
         "failure_pattern":"AssertionError","command_timeout_s":120}}
    (d/'manifest.json').write_text(json.dumps(m,indent=2))
    print(c['id'],base,vsha[:12])
