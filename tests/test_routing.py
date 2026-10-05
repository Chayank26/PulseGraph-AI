import pytest
from src.agents.triage import triage_agent_node
from src.core.state import PatientDemographics, VitalSigns
from src.core.routing import UNAVAILABLE
from test_triage_foundation import client


def evaluate(complaint, decisions=None, notes=None, age=45, pregnant=None):
    return triage_agent_node({'demographics': PatientDemographics(patient_id='P', age=age, chief_complaint=complaint),
        'raw_notes': notes or [], 'pathway_decisions': decisions or {},
        'urgency_context': {'pregnant': pregnant}})


@pytest.mark.parametrize('complaint,group', [
    ('abdominal pain', 'gastrointestinal'), ('headache', 'neurological'), ('rash', 'skin'),
    ('painful urination', 'urinary'), ('back pain', 'musculoskeletal_or_injury'), ('fever', 'systemic')])
def test_unsupported_groups_do_not_get_chest_questionnaires(complaint,group):
    result = evaluate(complaint)
    assert result['current_step'] == 'triage_manual_review_required'
    assert not result.get('pending_data_requests')
    assert group in result['presentation']['routing']['groups']
    assert result['risk_scores'] == []


def test_breathlessness_requires_confirmation_not_automatic_scores():
    result = evaluate('shortness of breath')
    req = result['pending_data_requests'][0]
    assert req.pathway_name == 'Assessment applicability'
    assert {f.field_key for f in req.required_fields} == {'pathway_decision_curb65', 'pathway_decision_wells'}
    assert all(f.options == ['applicable','not_applicable','unknown'] for f in req.required_fields)


def test_only_selected_assessment_collects_its_missing_fields():
    result = evaluate('shortness of breath', {'curb65':'not_applicable','wells':'applicable'})
    assert result['pending_data_requests'][0].pathway_name == 'Wells PE Assessment'
    assert all(f.field_key != 'bun_mg_dl' for f in result['pending_data_requests'][0].required_fields)


def test_declined_and_unknown_decisions_are_not_asked_again():
    for decision in ('not_applicable','unknown'):
        result = evaluate('shortness of breath', {'curb65':decision,'wells':decision})
        assert not result.get('pending_data_requests')
        assert result['current_step'] == 'triage_manual_review_required'


@pytest.mark.parametrize('age,pregnant', [(12,None),(45,True)])
def test_known_exclusions_override_applicable_decision(age,pregnant):
    result = evaluate('chest pain', {'heart':'applicable'}, age=age, pregnant=pregnant)
    assert result['current_step'] == 'triage_manual_review_required'
    assert result['presentation']['routing']['pathways'][0]['status'] == 'UNSUPPORTED'


def test_multiple_groups_preserved_with_supported_score_and_handoff():
    result = evaluate('chest pain and abdominal pain', {'heart':'applicable'}, [
        '[ACQUIRED CLINICAL DATA]: history_score = 1',
        '[ACQUIRED CLINICAL DATA]: ecg_score = 0',
        '[ACQUIRED CLINICAL DATA]: troponin_score = 0',
        '[ACQUIRED CLINICAL DATA]: cardiac_risk_factors_count = 0', "[ACQUIRED CLINICAL DATA]: atherosclerotic_disease = false"])
    assert result['current_step'] == 'triage_manual_review_required'
    assert result['risk_scores'][0].score_name == 'HEART Score'
    assert set(result['presentation']['routing']['groups']) == {'cardiovascular','gastrointestinal'}


def test_unavailable_age_is_not_requested_forever():
    result = evaluate('chest pain', notes=[f'[ACQUIRED CLINICAL DATA]: age = {UNAVAILABLE}'], age=None)
    assert not result.get('pending_data_requests')
    assert result['current_step'] == 'triage_manual_review_required'


def test_tachycardia_alone_does_not_select_wells():
    result = triage_agent_node({'demographics':PatientDemographics(patient_id='P',age=40,chief_complaint='rash'),
        'vitals':VitalSigns(heart_rate_bpm=110),'raw_notes':[]})
    assert result['current_step'] == 'triage_manual_review_required'


def test_unavailable_score_input_ends_with_persisted_handoff(client):
    path = '/api/clinical/sessions/' + client.post('/api/clinical/sessions',json={'patient_id':'P'}).json()['session_id']
    client.post(path+'/run')
    req = client.get(path+'/data-requests').json()[0]
    invalid = client.post(path+'/data-requests/'+req['request_id']+'/resolve', json={'response_data':{
        'pathway_decision_curb65':'invented', 'pathway_decision_wells':'not_applicable'}})
    assert invalid.status_code == 400
    result = client.post(path+'/data-requests/'+req['request_id']+'/resolve',json={'response_data':{
        'pathway_decision_curb65':'applicable', 'pathway_decision_wells':'not_applicable'}})
    assert result.status_code == 200, result.text
    req = client.get(path+'/data-requests').json()[0]
    assert req['pathway_name'] == 'CURB-65 Pneumonia Assessment'
    assert all(f['allow_unavailable'] for f in req['required_fields'])
    result = client.post(path+'/data-requests/'+req['request_id']+'/resolve',json={'response_data':{
        f['field_key']:UNAVAILABLE for f in req['required_fields']}})
    assert result.status_code == 200, result.text
    assert result.json()['status'] == 'REQUIRES_CLINICIAN_ASSESSMENT'
    assert client.get(path+'/data-requests').json() == []
    results = client.get(path+'/results').json()
    assert results['risk_scores'] == []
    assert results['presentation']['routing']['requires_clinician_assessment']
    assert results['presentation']['routing']['pathways'][1]['status'] == 'INCOMPLETE'


def test_unsupported_api_case_stops_before_imaging(client):
    assert client.put('/api/patients/P',json={'chief_complaint':'rash and headache'}).status_code == 200
    path = '/api/clinical/sessions/' + client.post('/api/clinical/sessions',json={'patient_id':'P'}).json()['session_id']
    result = client.post(path+'/run')
    assert result.status_code == 200, result.text
    assert result.json()['status'] == 'REQUIRES_CLINICIAN_ASSESSMENT'
    assert client.get(path+'/data-requests').json() == []
    assert client.get(path+'/results').json()['imaging_findings'] == []


def test_repeated_run_cannot_duplicate_pending_questions(client):
    path = '/api/clinical/sessions/' + client.post('/api/clinical/sessions',json={'patient_id':'P'}).json()['session_id']
    assert client.post(path+'/run').status_code == 200
    before = client.get(path+'/data-requests').json()
    assert client.post(path+'/run').status_code == 409
    after = client.get(path+'/data-requests').json()
    assert [r['request_id'] for r in before] == [r['request_id'] for r in after]
