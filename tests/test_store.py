import pytest
from repropatch.store import Store
from repropatch.models import RunCreate
from repropatch.worker import process_next

def test_claim_once(tmp_path):
    s=Store(tmp_path/'db');r=s.create(RunCreate().model_dump());assert s.claim()['id']==r['id'];assert s.claim() is None

def test_cannot_mark_queued_verified(tmp_path):
    s=Store(tmp_path/'db');r=s.create(RunCreate().model_dump())
    with pytest.raises(ValueError):s.transition(r['id'],'VERIFIED','No proof')

def test_crash_becomes_error_not_replayed(tmp_path):
    s=Store(tmp_path/'db');r=s.create(RunCreate().model_dump());s.claim();s.fail_interrupted()
    assert s.get(r['id'])['status']=='ERROR' and s.claim() is None

def test_fixture_baseline_false_success_detected(settings):
    s=Store(settings.db_path);r=s.create(RunCreate(method='W0').model_dump());process_next(s,settings)
    result=s.get(r['id'])
    assert result['status']=='REJECTED' and result['result']['false_success'] is True
    assert result['result']['benchmark_eligible'] is False
