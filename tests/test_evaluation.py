from repropatch.evaluation import summarize

def test_fixture_cannot_inflate_pilot():
    fixtures=[{'mode':'fixture','status':'VERIFIED','result':{'verified':True}}]
    assert summarize(fixtures)['metrics'] is None

def test_paired_failure_counts_without_becoming_verified():
    rows=[{'mode':'live','method':m,'case_id':'case-one','status':s,'result':{'cost_usd':.2,'duration_ms':100,'operator_interventions':0}} for m,s in [('W0','VERIFIED'),('W1','NOT_REPRODUCED')]]
    r=summarize(rows);assert r['completed_real_cases']==1
    assert r['metrics']['W0']['verified']==1 and r['metrics']['W1']['verified']==0
    assert r['metrics']['W1']['abstentions']==1 and r['metrics']['W1']['settled_usd']==.2
