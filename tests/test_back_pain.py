import pytest
from src.agents.triage import triage_agent_node
from src.core.state import PatientDemographics, VitalSigns
from src.core.data_requests import apply_response_to_state, validate_response
from test_triage_foundation import client
from test_optional_imaging import resolve


def state(**kwargs):
    return {'demographics':PatientDemographics(patient_id='P', age=45, chief_complaint='back pain'),
        'pathway_decisions':{'low_back':'applicable'}, **kwargs}


def answer(cause='not_suspected', scope='confirmed'):
    return {'back_review_scope':scope, 'back_review_serious_cause':cause}


def test_only_back_assessment_questions_no_chest_calculator():
    result=triage_agent_node(state())
    req,=result['pending_data_requests']
    assert req.pathway_name=='Low-back clinical assessment'
    assert result['risk_scores']==[]
    assert validate_response(req,answer())[0]


@pytest.mark.parametrize('cause,scope', [('suspected','confirmed'),('unknown','confirmed'),('__unavailable__','confirmed'),('not_suspected','outside_scope'),('not_suspected','unknown')])
def test_concern_or_incomplete_ends_with_handoff(cause,scope):
    initial=state(); result=triage_agent_node({**initial,**apply_response_to_state(initial,answer(cause,scope))})
    assert result['current_step']=='triage_manual_review_required'
    assert not result.get('pending_data_requests')
    assert result['presentation']['back_pain_assessment']['status']=='REQUIRES_CLINICIAN_ASSESSMENT'


def test_completed_clinician_record_is_not_score_and_changes_require_reassessment():
    initial=state(); current={**initial,**apply_response_to_state(initial,answer())}
    result=triage_agent_node(current)
    assert result['current_step']=='triage_completed'
    assert result['risk_scores']==[]
    assert result['presentation']['back_pain_assessment']['status']=='CLINICIAN_ASSESSED'
    current['vitals']=VitalSigns(heart_rate_bpm=90)
    assert triage_agent_node(current)['pending_data_requests'][0].pathway_name=='Low-back clinical assessment'


@pytest.mark.parametrize('age,pregnant',[(17,False),(45,True)])
def test_excluded_patients_do_not_enter_pathway(age,pregnant):
    initial=state(urgency_context={'pregnant':pregnant});initial['demographics'].age=age
    result=triage_agent_node(initial)
    assert result['current_step']=='triage_manual_review_required'
    assert not result.get('pending_data_requests')


def test_unrelated_concern_remains_handoff():
    initial=state();initial['demographics'].chief_complaint='back pain and abdominal pain'
    result=triage_agent_node({**initial, **apply_response_to_state(initial,answer())})
    assert result['current_step']=='triage_manual_review_required'
    assert any('abdominal_pain' in r for r in result['presentation']['routing']['handoff_reasons'])


@pytest.mark.parametrize('cause',['not_suspected','suspected','__unavailable__'])
def test_api_persistence_and_no_imaging_on_handoff(client,cause):
    client.put('/api/patients/P',json={'chief_complaint':'back pain'})
    created=client.post('/api/clinical/sessions',json={'patient_id':'P','pathway_decisions':{'low_back':'applicable'},
        'imaging_decision':{'decision':'optional','reason':'Clinician decision'}})
    assert created.status_code==201,created.text
    path='/api/clinical/sessions/'+created.json()['session_id']
    assert client.post(path+'/run').status_code==200
    res=resolve(client,path,answer(cause))
    assert res.status_code==200,res.text
    expected='WAITING_FOR_CLINICIAN_REVIEW' if cause=='not_suspected' else 'REQUIRES_CLINICIAN_ASSESSMENT'
    assert res.json()['status']==expected
    assert client.get(path+'/data-requests').json()==[]
    result=client.get(path+'/results').json()
    assert result['presentation']['back_pain_assessment']
    assert result['risk_scores']==[]


def test_invalid_answers_and_other_request_cannot_set_assessment():
    req=triage_agent_node(state())['pending_data_requests'][0]
    assert not validate_response(req,answer(cause='false'))[0]
    assert not validate_response(req,{**answer(),'extra':'data'})[0]
    req.pathway_name='Assessment applicability'
    assert not validate_response(req,answer())[0]


def test_api_owner_and_reassessment(client):
    from src.api.dependencies import get_current_clinician
    from src.db.models import DoctorModel
    client.put('/api/patients/P',json={'chief_complaint':'back pain'})
    created=client.post('/api/clinical/sessions',json={'patient_id':'P','pathway_decisions':{'low_back':'applicable'},
        'imaging_decision':{'decision':'optional','reason':'Clinician decision'}})
    path='/api/clinical/sessions/'+created.json()['session_id']
    client.post(path+'/run')
    owner=client.app.dependency_overrides[get_current_clinician]
    client.app.dependency_overrides[get_current_clinician]=lambda:DoctorModel(doctor_id='OTHER',full_name='Other',department='Test')
    assert resolve(client,path,answer()).status_code==400
    client.app.dependency_overrides[get_current_clinician]=owner
    assert resolve(client,path,answer()).status_code==200
    changed=client.post(path+'/reevaluate',json={'notes':'back pain'})
    assert changed.status_code==200,changed.text
    req,=client.get(path+'/data-requests').json()
    assert req['pathway_name']=='Low-back clinical assessment'
    assert client.get(path+'/results').json()['presentation']['back_pain_assessment'] is None
