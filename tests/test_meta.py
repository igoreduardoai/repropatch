import httpx
import pytest
from repropatch.meta import MetaClient,MetaError
from repropatch.budget import Budget

def test_request_shape_and_reasoning_not_double_counted(tmp_path):
    seen=[]
    def handler(req):
        import json
        body=json.loads(req.content);seen.append((req.url.path,body))
        if req.url.path.endswith('input_tokens'):return httpx.Response(200,json={'input_tokens':1000})
        return httpx.Response(200,json={'id':'resp_1','output':[],
          'usage':{'input_tokens':1000,'output_tokens':100,'input_tokens_details':{'cached_tokens':0},'output_tokens_details':{'reasoning_tokens':80}}})
    client=MetaClient(api_key='not-a-real-key',transport=httpx.MockTransport(handler))
    b=Budget(tmp_path/'db');r=client.respond('run',[{'role':'user','content':'test'}],[],b,1000)
    assert r['id']=='resp_1' and b.summary()['settled_usd']==0.006
    assert seen[0][0]=='/v1/responses/input_tokens'
    assert seen[1][1]['model']=='muse-wonder-1.0'
    client.close()

def test_unknown_usage_halts(tmp_path):
    def handler(req):return httpx.Response(200,json={'input_tokens':100} if req.url.path.endswith('input_tokens') else {'output':[]})
    client=MetaClient(api_key='test',transport=httpx.MockTransport(handler));b=Budget(tmp_path/'db')
    with pytest.raises(MetaError):client.respond('run',[],[],b)
    assert b.summary()['halted'] and b.summary()['committed_usd']>0
    client.close()

def test_no_missing_key(monkeypatch):
    monkeypatch.delenv('META_MODEL_API_KEY',raising=False);monkeypatch.delenv('MODEL_API_KEY',raising=False)
    with pytest.raises(MetaError):MetaClient()

def test_unverified_host_blocked():
    with pytest.raises(MetaError):MetaClient(base_url='https://attacker.test',api_key='test')
