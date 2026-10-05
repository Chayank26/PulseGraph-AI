import json
import pytest
from src.agents.diagnostic import diagnostic_agent_node
from src.core.diagnostic import build_diagnostic_context
from src.core.differential import prepare_context, validate_proposal
from src.tools.differential_provider import OllamaProvider
from test_diagnostic_context import state_for
from differential_fixture import SyntheticProvider


def payload():
    return prepare_context(build_diagnostic_context(state_for('chest pain. No cough')))[0]


def proposal():
    return json.loads(SyntheticProvider().generate(payload(),{}))


def test_validated_proposal_exposes_source_refs_without_probabilities():
    data=proposal();data['candidates'][0]['contradicting_ids']=['finding-1']
    data['candidates'][0]['missing_ids']=['spo2_percent']
    result,_=validate_proposal(json.dumps(data),payload(),5)
    assert result[0].conflicting_evidence
    assert result[0].missing_information==['spo2_percent']
    assert result[0].evidence_references[0]['source_version']
    assert result[0].likelihood=='Not estimated'
    assert result[0].recommended_workup==[]


@pytest.mark.parametrize('field,value', [('supporting_ids',['invented']),('supporting_ids',['finding-1']),
    ('contradicting_ids',['finding-0']),('evidence_ids',['invented-paper']),('missing_ids',['spo2_is_normal']),
    ('probability',0.99),('rationale','Patient has elevated troponin')])
def test_invented_or_wrong_assertion_references_rejected(field,value):
    data=proposal();data['candidates'][0][field]=value
    with pytest.raises(ValueError):validate_proposal(json.dumps(data),payload(),5)


def test_abstention_and_limit_validation():
    assert validate_proposal(json.dumps(dict(outcome='abstain',reason='insufficient_evidence',candidates=[])),payload(),5)[0]==[]
    data=proposal();data['candidates']*=2
    with pytest.raises(ValueError):validate_proposal(json.dumps(data),payload(),5)
    with pytest.raises(ValueError):validate_proposal(json.dumps(proposal()),payload(),0)


def test_disabled_mode_abstains_without_network(monkeypatch):
    monkeypatch.setattr('src.agents.diagnostic.configured_provider',lambda:None)
    result=diagnostic_agent_node(state_for('chest pain'))
    assert result['differentials']==[]
    assert result['presentation']['diagnostic_review']['generation']['reason']=='provider_not_configured'


@pytest.mark.parametrize('output',['not json',json.dumps({'outcome':'abstain','reason':'outside_scope','candidates':[{}]})])
def test_invalid_provider_output_clears_results(monkeypatch,output):
    class Invalid:
        def generate(self,*args):return output
    monkeypatch.setattr('src.agents.diagnostic.configured_provider',lambda:Invalid())
    result=diagnostic_agent_node(state_for('chest pain'))
    assert result['differentials']==[]
    assert result['presentation']['diagnostic_review']['generation']['status']=='FAILED'


def test_provider_error_not_exposed(monkeypatch):
    class Failed:
        def generate(self,*args):raise TimeoutError('sensitive content')
    monkeypatch.setattr('src.agents.diagnostic.configured_provider',lambda:Failed())
    result=diagnostic_agent_node(state_for('chest pain'))
    assert 'sensitive content' not in str(result)
    assert result['differentials']==[]


@pytest.mark.parametrize('url',['https://example.com','http://localhost:11434','http://127.0.0.1.evil.test','http://user:password@127.0.0.1','http://127.0.0.1/path'])
def test_non_loopback_or_ambiguous_endpoints_rejected(url):
    with pytest.raises(ValueError):OllamaProvider(url,'local-model')


def test_adapter_format_timeout_and_proxy_policy(monkeypatch):
    import src.tools.differential_provider as module
    class Response:
        status_code=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def iter_content(self,size):yield json.dumps({'done':True,'message':{'content':'{}'}}).encode()
    class Session:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,**kwargs):
            assert self.trust_env is False
            assert url=='http://127.0.0.1:11434/api/chat'
            assert kwargs['json']['stream'] is False
            assert kwargs['json']['format']=={'type':'object'}
            assert kwargs['allow_redirects'] is False
            assert kwargs['timeout']==(3,30)
            return Response()
    monkeypatch.setattr(module.requests,'Session',Session)
    assert OllamaProvider('http://127.0.0.1:11434','local-model').generate({}, {'type':'object'})=='{}'


def test_empty_or_unsupported_findings_do_not_call_provider(monkeypatch):
    class Unexpected:
        def generate(self,*args):raise AssertionError('must not call')
    monkeypatch.setattr('src.agents.diagnostic.configured_provider',lambda:Unexpected())
    for complaint,reason in [('No chest pain','insufficient_information'),('chest pain and blurred vision','outside_scope')]:
        generation=diagnostic_agent_node(state_for(complaint))['presentation']['diagnostic_review']['generation']
        assert generation['status']=='ABSTAINED'
        assert generation['reason']==reason


def test_context_excludes_identity_and_previous_review_metadata():
    state=state_for('chest pain')
    state['presentation']['evidence_review']={'reviewer':'doctor-secret'}
    prepared,_=prepare_context(build_diagnostic_context(state))
    assert 'patient_id' not in prepared['clinical']['demographics']
    assert 'evidence_review' not in prepared['clinical']['presentation']


def test_missing_collection_and_expired_collection_prevent_generation(monkeypatch,tmp_path):
    monkeypatch.setattr('src.agents.diagnostic.configured_provider',lambda:SyntheticProvider())
    import src.core.differential as module
    path=tmp_path/'evidence.json'
    monkeypatch.setattr(module,'CORPUS_PATH',path)
    assert diagnostic_agent_node(state_for('chest pain'))['presentation']['diagnostic_review']['generation']['status']=='FAILED'
    path.write_text(json.dumps({'version':'expired','documents':[]}))
    generation=diagnostic_agent_node(state_for('chest pain'))['presentation']['diagnostic_review']['generation']
    assert generation['status']=='ABSTAINED' and generation['reason']=='insufficient_evidence'


@pytest.mark.parametrize('status,body',[(302,b'{}'),(500,b'{}'),(200,b'{"done":false}'),(200,b'x'*131073)])
def test_adapter_rejects_redirect_error_incomplete_and_oversize(monkeypatch,status,body):
    import src.tools.differential_provider as module
    class Response:
        status_code=status
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def iter_content(self,size):yield body
    class Session:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,*args,**kwargs):return Response()
    monkeypatch.setattr(module.requests,'Session',Session)
    with pytest.raises(ValueError):OllamaProvider('http://127.0.0.1:11434','local').generate({}, {})


def test_api_disabled_mode_and_failed_reevaluation_are_explicit(client,monkeypatch):
    from test_optional_imaging import start, decision
    path=start(client,decision('no_imaging'))
    assert client.get(path+'/results').json()['differentials']
    monkeypatch.setattr('src.agents.diagnostic.configured_provider',lambda:None)
    response=client.post(path+'/reevaluate',json={'notes':'chest pain'})
    assert response.status_code==200
    result=client.get(path+'/results').json()
    assert result['differentials']==[] and result['evidence']==[]
    assert result['presentation']['diagnostic_review']['generation']['reason']=='provider_not_configured'


from test_triage_foundation import client
