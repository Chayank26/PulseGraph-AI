import pytest
from pydantic import ValidationError
from src.core.urgency import assess_urgency, UrgencyRules
from src.core.state import PatientDemographics, VitalSigns
from test_triage_foundation import client


def state(**vitals):
    return {'demographics': PatientDemographics(patient_id='P', age=50),
            'vitals': VitalSigns(heart_rate_bpm=80, respiratory_rate=18, blood_pressure_sys=120,
                temperature_c=37, spo2_percent=98).model_copy(update=vitals),
            'urgency_context': {'pregnant': False, 'clinician_concern': False,
                'new_confusion': False, 'oxygen_scale': 'standard'}}


@pytest.mark.parametrize('field,value', [
    ('heart_rate_bpm',40), ('heart_rate_bpm',131), ('respiratory_rate',8), ('respiratory_rate',25),
    ('blood_pressure_sys',90), ('blood_pressure_sys',220), ('temperature_c',35), ('spo2_percent',91),
])
def test_thresholds_trigger_review(field,value):
    result = assess_urgency(state(**{field:value}))
    assert result.status == 'URGENT_REVIEW'
    assert result.reasons[0].field == field
    assert result.reasons[0].value == value
    assert not result.acknowledged
    assert result.rules_review_status == 'PENDING_CLINICAL_REVIEW'


@pytest.mark.parametrize('field,value', [
    ('heart_rate_bpm',41), ('heart_rate_bpm',130), ('respiratory_rate',9), ('respiratory_rate',24),
    ('blood_pressure_sys',91), ('blood_pressure_sys',219), ('temperature_c',35.1), ('spo2_percent',92),
])
def test_adjacent_values_do_not_trigger_individual_rule(field,value):
    result = assess_urgency(state(**{field:value}))
    assert result.status == 'NO_TRIGGER_DETECTED'
    assert 'does not establish low risk' in result.action


def test_incomplete_unsupported_and_individualized_oxygen():
    initial = state()
    initial['vitals'] = None
    assert assess_urgency(initial).status == 'INCOMPLETE'
    initial['demographics'].age = 10
    assert assess_urgency(initial).status == 'OUTSIDE_SCOPE'
    initial['urgency_context']['clinician_concern'] = True
    assert assess_urgency(initial).status == 'URGENT_REVIEW'
    initial = state(spo2_percent=89)
    initial['urgency_context']['oxygen_scale'] = 'individualized'
    assert assess_urgency(initial).status == 'INCOMPLETE'
    initial['urgency_context']['pregnant'] = True
    assert assess_urgency(initial).status == 'OUTSIDE_SCOPE'


def test_unknown_context_is_not_assumed_normal():
    initial = state()
    initial['urgency_context'] = {}
    result = assess_urgency(initial)
    assert result.status == 'OUTSIDE_SCOPE'
    assert 'pregnant' in result.missing_information
    assert 'clinician_concern' in result.missing_information


def test_rule_configuration_validation_and_version():
    with pytest.raises(ValidationError):
        UrgencyRules(heart_rate_low=140, heart_rate_high=130)
    result = assess_urgency(state(heart_rate_bpm=129), UrgencyRules(version='local-test', heart_rate_high=125))
    assert result.status == 'URGENT_REVIEW'
    assert result.rules_version == 'local-test'


def test_urgent_review_precedes_questions_and_requires_true(client):
    created = client.post('/api/clinical/sessions',json={'patient_id':'P',
        'vitals': {'heart_rate_bpm':140}, 'urgency_context': state()['urgency_context']})
    assert created.status_code == 201, created.text
    path = '/api/clinical/sessions/' + created.json()['session_id']
    assert client.post(path+'/run').status_code == 200
    request = client.get(path+'/data-requests').json()[0]
    assert request['requesting_agent'] == 'urgency_check'
    key = request['required_fields'][0]['field_key']
    result = client.get(path+'/results').json()
    assert result['risk_scores'] == []
    assert result['urgency']['status'] == 'URGENT_REVIEW'
    assert client.post(path+'/data-requests/'+request['request_id']+'/resolve',json={'response_data':{key:False}}).status_code == 400
    acknowledged = client.post(path+'/data-requests/'+request['request_id']+'/resolve',json={'response_data':{key:True}})
    assert acknowledged.status_code == 200, acknowledged.text
    result = client.get(path+'/results').json()
    assert result['urgency']['acknowledged']
    assert result['urgency']['status'] == 'URGENT_REVIEW'
    assert client.get(path+'/data-requests').json()[0]['pathway_name'] == 'CURB-65 Pneumonia Assessment'


def test_new_data_interrupts_resumption_before_more_questions(client):
    created = client.post('/api/clinical/sessions',json={'patient_id':'P',
        'vitals': {'heart_rate_bpm':80,'respiratory_rate':18,'blood_pressure_sys':120,'blood_pressure_dia':80},
        'urgency_context': state()['urgency_context']})
    path = '/api/clinical/sessions/' + created.json()['session_id']
    client.post(path+'/run')
    request = client.get(path+'/data-requests').json()[0]
    response = client.post(path+'/data-requests/'+request['request_id']+'/resolve',json={
        'response_data': {'confusion':True,'bun_mg_dl':14}})
    assert response.status_code == 200, response.text
    urgent = client.get(path+'/data-requests').json()[0]
    assert urgent['requesting_agent'] == 'urgency_check'
    key = urgent['required_fields'][0]['field_key']
    assert client.post(path+'/data-requests/'+urgent['request_id']+'/resolve',json={'response_data':{key:True}}).status_code == 200
    request = client.get(path+'/data-requests').json()[0]
    assert request['pathway_name'] == 'Wells PE Assessment'
    answers = {field['field_key']:False for field in request['required_fields']}
    answers['heart_rate_bpm'] = 150
    assert client.post(path+'/data-requests/'+request['request_id']+'/resolve',json={'response_data':answers}).status_code == 200
    next_urgent = client.get(path+'/data-requests').json()[0]
    assert next_urgent['requesting_agent'] == 'urgency_check'
    assert next_urgent['required_fields'][0]['field_key'] != key
    assert not client.get(path+'/results').json()['urgency']['acknowledged']


def test_approval_cannot_bypass_urgency_pause(client):
    created = client.post('/api/clinical/sessions',json={'patient_id':'P',
        'urgency_context': {'clinician_concern':True}})
    path = '/api/clinical/sessions/' + created.json()['session_id']
    client.post(path+'/run')
    assert client.post(path+'/approve',json={}).status_code == 400
    assert client.get(path).json()['status'] == 'WAITING_FOR_CLINICAL_DATA'
