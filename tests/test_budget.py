import pytest
from repropatch.budget import Budget,BudgetExceeded,UsageMismatch

def test_no_cache_reservation(tmp_path):
    b=Budget(tmp_path/'db',run_cap='3')
    assert b.reserve('r1','run',600_000,30_000)==3_000_000
    with pytest.raises(BudgetExceeded):b.reserve('r2','run',1,1)

def test_settlement_releases_difference(tmp_path):
    b=Budget(tmp_path/'db')
    b.reserve('r1','run',100_000,1000)
    assert b.settle('r1',100_000,500,50_000)==220_000
    assert b.summary()['settled_usd']==0.22

def test_batch_cap_applies_across_runs(tmp_path):
    b=Budget(tmp_path/'db',batch_cap='3.00')
    b.reserve('r1','run1',600_000,30_000)
    with pytest.raises(BudgetExceeded):b.reserve('r2','run2',1,1)

def test_unknown_billing_keeps_reservation_and_halts(tmp_path):
    b=Budget(tmp_path/'db');b.reserve('r1','run',1000,100);b.unknown('r1')
    assert b.summary()['committed_usd']==0.006
    with pytest.raises(BudgetExceeded):b.reserve('r2','run',1,1)

def test_idempotent_reservation_is_not_replayed(tmp_path):
    b=Budget(tmp_path/'db');b.reserve('r1','run',1000,100)
    with pytest.raises(ValueError):b.reserve('r1','run',1000,100)

def test_usage_larger_than_reservation_halts(tmp_path):
    b=Budget(tmp_path/'db');b.reserve('r1','run',1,1)
    with pytest.raises(UsageMismatch):b.settle('r1',1000,100)
    assert b.summary()['halted']

def test_persisted_budget(tmp_path):
    path=tmp_path/'db';b=Budget(path);b.reserve('r1','run',1000,100)
    assert Budget(path).summary()['committed_usd']==0.006

def test_invalid_cached_tokens(tmp_path):
    b=Budget(tmp_path/'db');b.reserve('r1','run',100,100)
    with pytest.raises(UsageMismatch):b.settle('r1',10,5,11)

def test_restart_halts_orphaned_reservation(tmp_path):
    from repropatch.budget import Budget,BudgetExceeded
    b=Budget(tmp_path/'restart.sqlite3');b.reserve('interrupted','one',1000,1800)
    assert b.recover_inflight()==1 and b.recover_inflight()==0
    assert b.summary()['halted']=='interrupted_request_billing_unknown'
    assert b.run_spend('one')['unknown_calls']==1
    import pytest
    with pytest.raises(BudgetExceeded):b.reserve('new','two',1000,1800)
