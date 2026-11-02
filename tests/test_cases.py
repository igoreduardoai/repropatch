import json
import pytest
from repropatch.cases import Registry,CaseError,parse_manifest,tree_files,check_agent_path
from repropatch.security import BoundaryError
from livekit import make_case,accept,KEY

def reg(tmp_path,**kw):
    root=tmp_path/'cases';root.mkdir()
    make_case(root,**kw);return Registry(root,KEY)

def test_valid_manifest_loads_without_host_paths_in_public_view(tmp_path):
    r=reg(tmp_path);c=r.load('synthetic-case')
    pub=c.public()
    assert pub['case_id']=='synthetic-case' and 'root' not in pub and str(tmp_path) not in json.dumps(pub)

@pytest.mark.parametrize('field,value',[
    ('model','gpt-4'),('base_commit','abc'),('sandbox_image_id','node:22'),
    ('video_origin','found_somewhere'),('repository_url','http://x'),('schema_version',1)])
def test_manifest_rejects_unreviewed_fields(tmp_path,field,value):
    r=reg(tmp_path);p=r.root/'synthetic-case'/'manifest.json'
    d=json.loads(p.read_text());d[field]=value;p.write_text(json.dumps(d))
    with pytest.raises(CaseError):r.load('synthetic-case')

def test_tbd_placeholder_manifest_is_rejected(tmp_path):
    r=reg(tmp_path);p=r.root/'synthetic-case'/'manifest.json'
    d=json.loads(p.read_text());d['license']='TBD';p.write_text(json.dumps(d))
    with pytest.raises(CaseError):r.load('synthetic-case')

def test_commands_must_be_argv_lists_and_serve_must_be_loopback(tmp_path):
    r=reg(tmp_path);p=r.root/'synthetic-case'/'manifest.json'
    d=json.loads(p.read_text());d['profile']['repro']['argv']='npm test && curl evil';p.write_text(json.dumps(d))
    with pytest.raises(CaseError):r.load('synthetic-case')
    d['profile']['repro']['argv']=['node','tests/repro.mjs'];d['profile']['serve']['url']='https://example.com/';p.write_text(json.dumps(d))
    with pytest.raises(CaseError):r.load('synthetic-case')

def test_case_id_must_match_directory_and_be_registered(tmp_path):
    r=reg(tmp_path)
    for bad in ['../etc','Synthetic','nope-nope','a','']:
        with pytest.raises(CaseError):r.load(bad)

def test_acceptance_required_and_bound_to_bytes(tmp_path):
    r=reg(tmp_path);c=r.load('synthetic-case')
    assert not r.acceptance_status(c)['accepted']
    accept(r,c);assert r.acceptance_status(c)['accepted']
    # Any change to the evaluator, reference, snapshot or manifest invalidates live.
    (c.evaluator_dir/'check.mjs').write_text('// tampered')
    assert 'evaluator_tree_sha256' in r.acceptance_status(c)['reason']
    assert r.accepted_cases()==[]

def test_acceptance_signature_and_key(tmp_path):
    r=reg(tmp_path);c=r.load('synthetic-case');accept(r,c)
    assert not Registry(r.root,'a-different-key-of-sufficient-length').acceptance_status(c)['accepted']
    assert not Registry(r.root,'').acceptance_status(c)['accepted']
    ev=json.loads(c.acceptance_path.read_text());ev['browser_smoke']=True;ev['independent_fails_before']=False
    c.acceptance_path.write_text(json.dumps(ev))
    assert 'signature' in r.acceptance_status(c)['reason']

def test_incomplete_evidence_is_not_acceptance(tmp_path):
    r=reg(tmp_path);c=r.load('synthetic-case')
    for over in ({'browser_smoke':False},{'independent_fails_before':False},{'independent_passes_reference':False}):
        accept(r,c,**over);assert not r.acceptance_status(c)['accepted'],over

def test_image_drift_blocks(tmp_path):
    r=reg(tmp_path);c=r.load('synthetic-case');accept(r,c)
    assert not r.acceptance_status(c,live_image_id='sha256:'+'c'*64)['accepted']

def test_tree_rejects_symlinks_and_git(tmp_path):
    d=tmp_path/'t';d.mkdir();(d/'a.js').write_text('x');(d/'l').symlink_to(d/'a.js')
    with pytest.raises(CaseError):tree_files(d)
    (d/'l').unlink();(d/'.git').mkdir();(d/'.git'/'HEAD').write_text('x')
    with pytest.raises(CaseError):tree_files(d)

def test_agent_path_policy(tmp_path):
    c=reg(tmp_path).load('synthetic-case')
    assert check_agent_path(c,'src/pagination.mjs')=='src/pagination.mjs'
    for bad in ['../x','/etc/passwd','.git/config','.env','src/.env.local','a\\b','node_modules/x','private/reference/a','evaluation/x','.hidden/a']:
        with pytest.raises(BoundaryError):check_agent_path(c,bad)
