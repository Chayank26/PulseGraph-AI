import pytest
from src.tools.medication_provider import assess_interactions
from src.core.medication_review import parse_reconciliation, apply_reconciliation
from src.core.state import PatientDemographics
from src.agents.safety import safety_agent_node
from test_triage_foundation import client
from test_optional_imaging import start, decision, resolve


class Provider:
    def __init__(self, result): self.result = result
    def check(self, medications): return self.result


def result():
    return dict(provider='Synthetic', source_version='test-v1', scope='Synthetic test pairs',
        normalization=[dict(index=i,status='resolved',ingredient_ids=[str(i)]) for i in range(2)],
        pairs=[dict(left=0,right=1,status='no_alert',description='Synthetic',source_reference='test-record')])


def test_disabled_complete_and_partial():
    assert assess_interactions(['a','b'])['status'] == 'NOT_CONFIGURED'
    assert assess_interactions(['a','b'],Provider(result()))['status'] == 'ASSESSED_WITHIN_PROVIDER_SCOPE'
    data=result(); data['pairs']=[]
    assert assess_interactions(['a','b'],Provider(data))['status'] == 'PARTIAL'
    data['normalization'][0].update(status='ambiguous',ingredient_ids=[])
    assert assess_interactions(['a','b'],Provider(data))['status'] == 'PARTIAL'


@pytest.mark.parametrize('case',['unknown_index','duplicate','ambiguous_assessed','missing_version','missing_normalization'])
def test_invalid_provider_output_fails_closed(case):
    data=result()
    if case=='unknown_index': data['pairs'][0]['right']=3
    if case=='duplicate': data['pairs']*=2
    if case=='ambiguous_assessed': data['normalization'][0].update(status='ambiguous',ingredient_ids=[])
    if case=='missing_version': data.pop('source_version')
    if case=='missing_normalization': data['normalization']=[]
    assert assess_interactions(['a','b'],Provider(data)) == {'status':'FAILED','result':None}


def test_failure_does_not_expose_exception():
    class Broken:
        def check(self, medications): raise RuntimeError('sensitive response')
    assert assess_interactions(['a'],Broken()) == {'status':'FAILED','result':None}


def response(status='unknown'):
    return {'medication_review_medications':status,'medication_review_allergies':status}


def test_unknown_preserves_entries_and_none_clears():
    state={'demographics':PatientDemographics(patient_id='P',current_medications=['A'],allergies=['B'])}
    unknown=apply_reconciliation(state,response())
    assert unknown['demographics'].current_medications==['A']
    assert state['demographics'].current_medications==['A']
    cleared=apply_reconciliation(state,response('none_confirmed'))
    assert cleared['demographics'].current_medications==[]
    assert cleared['demographics'].allergies==[]
    changed={**state, **unknown}
    changed['demographics'].current_medications=['C']
    assert safety_agent_node(changed)['pending_data_requests'][0].pathway_name=='Medication reconciliation'


@pytest.mark.parametrize('data',[response('recorded'), {**response(),'medication_review_medications_list':'A'},response('bogus')])
def test_contradictory_history_rejected(data):
    with pytest.raises(ValueError): parse_reconciliation(data)


@pytest.mark.parametrize('status',['recorded','none_confirmed','unknown','unavailable'])
def test_api_reconciliation_resumes_without_repeat(client,status):
    assert client.put('/api/patients/P',json={'current_medications':['Synthetic drug']}).status_code==200
    path=start(client,decision('no_imaging'))
    req,=client.get(path+'/data-requests').json()
    assert req['pathway_name']=='Medication reconciliation'
    data=response(status)
    if status=='recorded':
        data.update(medication_review_medications_list='Synthetic drug', medication_review_allergies_list='Synthetic allergy')
    res=resolve(client,path,data)
    assert res.status_code==200,res.text
    assert res.json()['status']=='WAITING_FOR_CLINICIAN_REVIEW'
    assert client.get(path+'/data-requests').json()==[]
    coverage=client.get(path+'/results').json()['presentation']['safety_review']
    assert coverage['medication_history']==status.upper()
    assert coverage['interaction_provider']=='NOT_CONFIGURED'


def test_provider_alert_requires_severity_and_retains_provenance():
    data=result(); data['pairs'][0]['status']='alert'
    assert assess_interactions(['a','b'],Provider(data))['status']=='FAILED'
    data['pairs'][0]['severity']='MODERATE'
    assessed=assess_interactions(['a','b'],Provider(data))
    assert assessed['result']['pairs'][0]['severity']=='MODERATE'
    assert assessed['result']['pairs'][0]['source_reference']=='test-record'


def test_only_session_owner_can_reconcile(client):
    from src.api.dependencies import get_current_clinician
    from src.db.models import DoctorModel
    client.put('/api/patients/P',json={'current_medications':['Synthetic drug']})
    path=start(client,decision('no_imaging'))
    client.app.dependency_overrides[get_current_clinician]=lambda:DoctorModel(doctor_id='OTHER',full_name='Other',department='Test')
    assert resolve(client,path,response()).status_code==400
    assert len(client.get(path+'/data-requests').json())==1
