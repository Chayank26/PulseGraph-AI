import pytest
from src.agents.triage import triage_agent_node
from src.core.state import PatientDemographics
from src.tools.calculators import calculate_heart_score, calculate_curb65_score
from src.core.urgency import assess_urgency
from test_urgency import state as urgency_state
from test_triage_foundation import client


def heart_state():
    return {'demographics': PatientDemographics(patient_id='P',age=50,chief_complaint='chest pain'),
        'pathway_decisions': {'heart':'applicable'},
        'raw_notes':[f'[ACQUIRED CLINICAL DATA]: {key} = 0' for key in
            ('history_score','ecg_score','troponin_score','cardiac_risk_factors_count')]}


def test_old_heart_intake_requests_new_field_without_default():
    result = triage_agent_node(heart_state())
    assert result['risk_scores'] == []
    field, = result['pending_data_requests'][0].required_fields
    assert field.field_key == 'atherosclerotic_disease'
    assert field.allow_unavailable


@pytest.mark.parametrize('answer,points', [('true',3),('false',1)])
def test_explicit_history_changes_heart_risk_component(answer,points):
    state = heart_state()
    state['raw_notes'].append('[ACQUIRED CLINICAL DATA]: atherosclerotic_disease = '+answer)
    result = triage_agent_node(state)
    assert result['risk_scores'][0].value == points


def test_unavailable_history_hands_off_without_reasking():
    state = heart_state()
    state['raw_notes'].append('[ACQUIRED CLINICAL DATA]: atherosclerotic_disease = __unavailable__')
    result = triage_agent_node(state)
    assert result['current_step'] == 'triage_manual_review_required'
    assert result['risk_scores'] == []
    assert not result.get('pending_data_requests')


@pytest.mark.parametrize('bad', [None,'false',0])
def test_calculator_requires_explicit_boolean_history(bad):
    with pytest.raises(ValueError):
        calculate_heart_score(0,0,50,0,0,bad)


@pytest.mark.parametrize('bun,points', [(19,0),(19.5,0),(7/0.357,0),(19.7,1),(20,1)])
def test_bun_conversion_boundary(bun,points):
    score = calculate_curb65_score(False,bun,20,120,80,50)
    assert score.value == points
    assert score.details['urea_mmol_l'] == bun*0.357


@pytest.mark.parametrize('field,inside,outside', [
    ('heart_rate_bpm',40,40.01), ('heart_rate_bpm',131,130.99),
    ('respiratory_rate',8,8.01), ('respiratory_rate',25,24.99),
    ('blood_pressure_sys',90,90.01), ('blood_pressure_sys',220,219.99),
    ('temperature_c',35,35.01), ('spo2_percent',91,91.01)])
def test_fractional_urgency_boundaries(field,inside,outside):
    assert assess_urgency(urgency_state(**{field:inside})).status == 'URGENT_REVIEW'
    assert assess_urgency(urgency_state(**{field:outside})).status == 'NO_TRIGGER_DETECTED'


@pytest.mark.parametrize('age,pregnant,status', [(15,False,'OUTSIDE_SCOPE'),(16,False,'URGENT_REVIEW'),
    (50,True,'OUTSIDE_SCOPE'),(50,None,'OUTSIDE_SCOPE')])
def test_urgency_scope_boundaries(age,pregnant,status):
    state = urgency_state(heart_rate_bpm=131)
    state['demographics'].age = age
    state['urgency_context']['pregnant'] = pregnant
    assert assess_urgency(state).status == status


def test_pharmacology_no_longer_issues_vital_treatment():
    from src.tools.pharmacology import check_drug_safety_profile
    assert check_drug_safety_profile([],[],urgency_state(spo2_percent=80,heart_rate_bpm=140)['vitals']) == []


def test_api_new_heart_answer_resumes_and_persists(client):
    client.put('/api/patients/P',json={'chief_complaint':'chest pain'})
    response = client.post('/api/clinical/sessions',json={'patient_id':'P',
        'raw_notes':heart_state()['raw_notes'], 'pathway_decisions':{'heart':'applicable'},
        'imaging_decision':{'decision':'no_imaging','reason':'Clinician decision'}})
    path = '/api/clinical/sessions/'+response.json()['session_id']
    assert client.post(path+'/run').status_code == 200
    req, = client.get(path+'/data-requests').json()
    assert [f['field_key'] for f in req['required_fields']] == ['atherosclerotic_disease']
    response = client.post(path+'/data-requests/'+req['request_id']+'/resolve',json={'response_data':{'atherosclerotic_disease':True}})
    assert response.status_code == 200, response.text
    score, = client.get(path+'/results').json()['risk_scores']
    assert score['value'] == 3
    assert score['details']['atherosclerotic_disease'] is True
