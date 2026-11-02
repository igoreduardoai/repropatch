from repropatch.agent import AgentLoop
from repropatch.budget import Budget

class Gateway:
    def definitions(self):return [{'type':'function','name':'submit_candidate','parameters':{'type':'object','properties':{}}}]
    def execute(self,name,arguments):return {'patch_sha':'abc','claim':'fixed'}

class Client:
    def respond(self,*args):return {'id':'mock','output':[{'type':'function_call','name':'submit_candidate','call_id':'c1','arguments':'{}'}]}
    def public_usage(self,response):return {'response_id':response['id']}

def test_finish_is_not_verification(tmp_path):
    events=[]
    result=AgentLoop(Client(),Gateway(),Budget(tmp_path/'db'),lambda k,v:events.append((k,v))).run('run','W0','bug','expected')
    assert result['status']=='CANDIDATE_SUBMITTED' and 'verified' not in result
    assert events
