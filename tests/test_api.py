from fastapi.testclient import TestClient
from repropatch.worker import process_next

def test_health_is_public(app):
    with TestClient(app) as c:assert c.get('/healthz').status_code==200

def test_api_requires_auth(app):
    with TestClient(app) as c:assert c.get('/api/runs').status_code==401

def test_missing_token_fails_closed(tmp_path):
    from repropatch.api import create_app
    from repropatch.config import Settings
    with TestClient(create_app(Settings(tmp_path,''))) as c:
        assert c.get('/api/runs').status_code==503

def test_fixture_api_roundtrip(client,app,settings):
    created=client.post('/api/runs',json={}).json()
    assert created['status']=='QUEUED'
    assert process_next(app.state.store,settings)
    row=client.get('/api/runs/'+created['id']).json()
    assert row['status']=='VERIFIED'
    assert row['result']['model_calls']==0
    assert row['result']['benchmark_eligible'] is False
    assert len(row['artifacts'])==3
    a=row['artifacts'][0]
    artifact=client.get('/api/runs/'+row['id']+'/artifacts/'+a['id'])
    assert artifact.status_code==200
    assert 'path' not in a

def test_live_never_falls_back_to_fixture(client):
    r=client.post('/api/runs',json={'mode':'live'})
    assert r.status_code==409
    assert client.get('/api/runs').json()['items']==[]

def test_idempotency(client):
    headers={'Idempotency-Key':'same-request'}
    first=client.post('/api/runs',json={},headers=headers).json()
    second=client.post('/api/runs',json={},headers=headers).json()
    assert first['id']==second['id']
    assert client.post('/api/runs',json={'method':'W0'},headers=headers).status_code==409

def test_unknown_run(client):assert client.get('/api/runs/'+'a'*32).status_code==404

def test_cancel_queued(client,app,settings):
    r=client.post('/api/runs',json={}).json()
    assert client.post('/api/runs/'+r['id']+'/cancel').json()['status']=='CANCELLED'
    assert not process_next(app.state.store,settings)

def test_evaluation_excludes_fixture(client,app,settings):
    client.post('/api/runs',json={});process_next(app.state.store,settings)
    e=client.get('/api/evaluation').json()
    assert e['status']=='NOT_MEASURED' and e['metrics'] is None and e['live_runs']==0

def test_mp4_upload_is_not_sent_to_meta(client):
    body=b'\x00\x00\x00\x18ftypisom'+b'0'*20
    r=client.post('/api/videos',files={'file':('test.mp4',body,'video/mp4')})
    assert r.status_code==200 and r.json()['sent_to_meta'] is False

def test_bad_video_rejected(client):
    assert client.post('/api/videos',files={'file':('bad.mp4',b'not-a-video','video/mp4')}).status_code==415
    assert client.post('/api/videos',files={'file':('bad.html',b'anything','text/html')}).status_code==415

def test_artifact_cross_run_forbidden(client,app,settings):
    one=client.post('/api/runs',json={}).json();process_next(app.state.store,settings)
    two=client.post('/api/runs',json={}).json()
    artifact=client.get('/api/runs/'+one['id']).json()['artifacts'][0]['id']
    assert client.get('/api/runs/'+two['id']+'/artifacts/'+artifact).status_code==404

def test_config_does_not_expose_keys(client):
    text=client.get('/api/config').text
    assert 'test-operator-token' not in text and 'api_key' not in text
