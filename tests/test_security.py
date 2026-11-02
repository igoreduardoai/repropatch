import pytest
from repropatch.security import safe_path,BoundaryError,freeze_test,check_frozen
from repropatch.workspace import Workspace
from repropatch.sandbox import DockerSandbox

@pytest.mark.parametrize('path',['../secret','/etc/passwd','src/../../secret','src\\file'])
def test_traversal_blocked(tmp_path,path):
    with pytest.raises(BoundaryError):safe_path(tmp_path,path)

def test_symlink_blocked(tmp_path):
    (tmp_path/'link').symlink_to('/tmp')
    with pytest.raises(BoundaryError):safe_path(tmp_path,'link/x')

def test_freeze_detects_modification(tmp_path):
    original=tmp_path/'test';original.write_text('assert original')
    frozen=freeze_test(original,tmp_path/'frozen')
    from pathlib import Path
    path=Path(frozen['path']);check_frozen(path,frozen['sha256'])
    path.write_text('assert true')
    with pytest.raises(BoundaryError):check_frozen(path,frozen['sha256'])

def test_workspace_cannot_read_answers_or_credentials(tmp_path):
    w=Workspace(tmp_path)
    for path in ['.env','evaluation/answers.json','.git/logs/HEAD','hidden/test.ts']:
        with pytest.raises(BoundaryError):w.read(path)

def test_w1_cannot_patch_before_freeze(tmp_path):
    w=Workspace(tmp_path)
    with pytest.raises(BoundaryError):w.write_source('src/app.ts','export {}')
    w.write_reproduction('assert expected')
    w.freeze(True,'a'*40)
    assert w.write_source('src/app.ts','export {}')['sha256']
    with pytest.raises(BoundaryError):w.write_reproduction('assert true')

def test_w0_may_edit_without_forced_freeze(tmp_path):
    assert Workspace(tmp_path,method='W0').write_source('src/app.ts','export {}')

def test_unconfirmed_failure_cannot_freeze(tmp_path):
    w=Workspace(tmp_path);w.write_reproduction('assert expected')
    with pytest.raises(BoundaryError):w.freeze(False,'a'*40)

def test_sandbox_command_has_boundaries(tmp_path):
    c=DockerSandbox('node:22-bookworm-slim').command(tmp_path,['node','test.mjs'],'test-run')
    assert '--network=none' in c and '--read-only' in c and '--cap-drop=ALL' in c
    assert '--user' in c and '65534:65534' in c and '--pull=never' in c
    assert '/var/run/docker.sock' not in ' '.join(c)
    assert '--env' not in c and '--privileged' not in c

def test_no_host_sandbox_fallback(tmp_path,monkeypatch):
    monkeypatch.setattr('repropatch.sandbox.shutil.which',lambda _:None)
    with pytest.raises(RuntimeError):DockerSandbox('node:22').run(tmp_path,['node','x'])
