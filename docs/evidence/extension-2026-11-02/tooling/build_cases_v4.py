import json, subprocess, shutil, sys, hashlib
from pathlib import Path
ROOT=Path('/workspace/rp-cases-2026-11-02'); SRC=ROOT/'van-src'; SPEC=ROOT/'spec'; CASES=ROOT/'data'/'cases'
IMAGE=subprocess.check_output(['docker','image','inspect','--format','{{.Id}}','repropatch-browser:pilot-v4'],text=True).strip()
C=[dict(id='vanx-poplen-fc3',fix='fc3ee4c4bdab9f0a065ff6d897c53f2fa8f85eeb',files=['src/van.js','x/src/van-x.js'],edit=['x/src/'],
  title='Reactive array length does not update after pop',
  expected='The release checklist shows "Tasks left: 3". Each click on "Finish last task" pops one task, so the counter must read 2, then 1, then 0. The length of a reactive array must propagate to derived states and the DOM after pop, push and index writes.'),
 dict(id='vanx-replacelen-acb',fix='acb8ba839a28b53ef0e4cf9be0cf086df0a56ca6',files=['src/van.js','x/src/van-x.js'],edit=['x/src/'],
  title='vanX.replace with a shorter array leaves a stale length',
  expected='After "Keep top 2" the playlist must show "Songs: 2" and "Saved as: [\"Blue\",\"Gold\"]". After vanX.replace on a reactive array, the array length and JSON must match the new array, including when it shrinks or becomes empty.'),
 dict(id='vanx-proxyarg-1c5',fix='1c580f0a6598ddcff62b005e742a7d5e9fe4eaf7',files=['src/van.js','x/src/van-x.js'],edit=['x/src/'],
  title='Reading length or array methods on a reactive object throws',
  expected='The cart must show "Items: 2 (apple, pear)" and, after "Add plum", "Items: 3 (apple, pear, plum)" with no error. Non-state properties of reactive objects (array length, push, map, join) must be readable through the reactive proxy.'),
 dict(id='van-propgc-84f',fix='84f30ae917107c9d4b4c38b9969a0d56aaac5ac8',files=['src/van.js'],edit=['src/'],
  title='Function-valued property bindings keep recomputing after their element is removed',
  expected='After the price badge is closed (removed from the page), further price ticks must not recompute its title: "Badge title computations" must stop increasing. Property bindings created from functions must be released when their element is removed, while explicit van.derive states keep working.'),
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
