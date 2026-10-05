import pytest
from pydantic import ValidationError
from src.core.presentation import extract_presentation, ClinicalPresentation
from src.core.state import PatientDemographics
from src.agents.triage import triage_agent_node
from test_triage_foundation import client


@pytest.mark.parametrize('text,symptom,status', [
    ('Chest pain', 'chest_pain', 'present'),
    ('Denies chest pain', 'chest_pain', 'absent'),
    ('No chest discomfort', 'chest_pain', 'absent'),
    ('Previous episode of chest pain', 'chest_pain', 'historical'),
    ('Chest pain resolved', 'chest_pain', 'historical'),
    ('Possible chest pain', 'chest_pain', 'uncertain'),
    ('Cannot rule out chest pain', 'chest_pain', 'uncertain'),
    ('If chest pain develops', 'chest_pain', 'uncertain'),
    ('Family history of DVT', 'dvt', 'other_person'),
    ('Father has chest pain', 'chest_pain', 'other_person'),
    ('History of DVT', 'dvt', 'historical'),
    ('Difficulty breathing', 'breathlessness', 'present'),
    ('Abdominal pain', 'abdominal_pain', 'present'),
    ('Painful urination', 'dysuria', 'present'),
    ('No fever or cough', 'cough', 'absent'),
    ('No fever but cough', 'cough', 'present'),
    ('Chest pain absent', 'chest_pain', 'absent'),
])
def test_assertion_context(text, symptom, status):
    result = extract_presentation(text, [])
    assert next(s for s in result.symptoms if s.symptom == symptom).status == status


def test_sources_and_attributes_are_exact():
    text = 'Severe right abdominal pain for 2 days'
    result = extract_presentation(text, [])
    mention = result.symptoms[0].mentions[0]
    assert mention.time_course == 'for 2 days'
    assert mention.location == 'right'
    assert mention.severity == 'Severe'
    assert text[mention.start:mention.end] == mention.quote
    assert ClinicalPresentation.model_validate(result.model_dump()) == result
    invalid = result.model_dump()
    invalid['symptoms'][0]['mentions'][0]['quote'] = 'invented text'
    with pytest.raises(ValidationError):
        ClinicalPresentation.model_validate(invalid)


def test_attributes_are_not_assigned_between_multiple_symptoms():
    result = extract_presentation('Mild headache and severe abdominal pain for 2 days', [])
    assert all(m.severity is None and m.time_course is None for s in result.symptoms for m in s.mentions)


def test_unknowns_and_administrative_notes_do_not_become_symptoms():
    result = extract_presentation('Unusual sensation', ['[ACQUIRED CLINICAL DATA]: previous_dvt_pe = False',
        'Conditions: DVT', 'Allergies: cough medicine'])
    assert result.symptoms == []
    assert result.unrecognized_sources == ['chief_complaint']


def test_conflicting_sources_are_not_silently_overwritten():
    result = extract_presentation('chest pain', ['Denies chest pain'])
    symptom = result.symptoms[0]
    assert symptom.status == 'conflicting'
    assert {m.source_id for m in symptom.mentions} == {'chief_complaint', 'raw_notes[0]'}


@pytest.mark.parametrize('complaint', ['No chest pain', 'History of DVT', 'Possible chest pain', 'Headache'])
def test_noncurrent_or_unrelated_symptoms_do_not_activate_calculators(complaint):
    result = triage_agent_node({'demographics': PatientDemographics(patient_id='P', age=40, chief_complaint=complaint), 'raw_notes': []})
    assert result['risk_scores'] == []
    assert 'pending_data_requests' not in result
    assert result['presentation']['symptoms']


def test_conflict_is_persisted_and_clinician_answer_resumes_triage(client):
    created = client.post('/api/clinical/sessions', json={
        'patient_id': 'P', 'raw_notes': ['Denies shortness of breath']})
    path = '/api/clinical/sessions/' + created.json()['session_id']
    assert client.post(path + '/run').status_code == 200
    result = client.get(path + '/results')
    assert result.status_code == 200, result.text
    assert result.json()['presentation']['symptoms'][0]['status'] == 'conflicting'
    request = client.get(path + '/data-requests').json()[0]
    assert request['pathway_name'] == 'Presentation clarification'
    resolved = client.post(path + '/data-requests/' + request['request_id'] + '/resolve',
        json={'response_data': {'symptom_present_breathlessness': True}})
    assert resolved.status_code == 200, resolved.text
    result = client.get(path + '/results').json()
    assert result['presentation']['symptoms'][0]['status'] == 'present'
    assert result['presentation']['symptoms'][0]['clarification_source'] == 'symptom_present_breathlessness'
    assert client.get(path + '/data-requests').json()[0]['pathway_name'] == 'Assessment applicability'


@pytest.mark.parametrize('text,status', [
    ('pain in my chest','present'), ('Pain in the chest','present'),
    ('My chest hurts','present'), ('No pain in my chest','absent'),
    ('Previous pain in her chest','historical'), ('Father has pain in his chest','other_person'),
    ('Possible pain in my chest','uncertain')])
def test_chest_paraphrases_retain_context_and_exact_spans(text,status):
    result = extract_presentation(text,[])
    assert result.symptoms[0].symptom == 'chest_pain'
    assert result.symptoms[0].status == status
    mention = result.symptoms[0].mentions[0]
    assert text[mention.start:mention.end] == mention.quote
    assert not result.unrecognized_fragments


@pytest.mark.parametrize('complaint,notes', [
    ('chest pain and blurred vision',[]),
    ('chest pain. Blurred vision',[]),
    ('chest pain',['Blurred vision']),
    ('blurred vision with chest pain',[]),
    ('chest pain and ringing in my ears',[]),
    ('pain in my chest; unusual sensation in my arm',[])])
def test_partial_recognition_preserves_unknown_text_and_hands_off(complaint,notes):
    from src.core.state import PatientDemographics
    result = triage_agent_node({'demographics':PatientDemographics(patient_id='P',age=50,chief_complaint=complaint),
        'pathway_decisions':{'heart':'applicable'}, 'raw_notes':notes+[
            '[ACQUIRED CLINICAL DATA]: history_score = 0', '[ACQUIRED CLINICAL DATA]: ecg_score = 0',
            '[ACQUIRED CLINICAL DATA]: troponin_score = 0', '[ACQUIRED CLINICAL DATA]: cardiac_risk_factors_count = 0']})
    assert result['current_step'] == 'triage_manual_review_required'
    assert result['risk_scores'][0].score_name == 'HEART Score'
    presentation = ClinicalPresentation.model_validate(result['presentation'])
    assert presentation.unrecognized_fragments
    assert any('Uninterpreted text' in reason for reason in presentation.routing.handoff_reasons)


def test_unrecognized_span_validation_and_benign_attributes():
    result = extract_presentation('Severe right chest pain for 2 days', ['Symptoms started today'])
    assert not result.unrecognized_fragments
    result = extract_presentation('chest pain and blurred vision',[]).model_dump()
    result['unrecognized_fragments'][0]['quote'] = 'invented'
    with pytest.raises(ValidationError):
        ClinicalPresentation.model_validate(result)
