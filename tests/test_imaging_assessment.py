import pytest
from src.agents.imaging import imaging_agent_node
from src.core.data_requests import apply_response_to_state, validate_response
from src.core.state import PatientDemographics, VitalSigns
from test_triage_foundation import client
from test_optional_imaging import start, decision, resolve


def state():
    return {'demographics':PatientDemographics(patient_id='P',age=50,chief_complaint='chest pain'),
        'raw_notes':[], 'imaging_decision':{'decision':'required','reason':'Clinician decision','modality':'CT','anatomy':'chest'}}


def test_legacy_required_decision_requests_purpose_first():
    result=imaging_agent_node(state())
    assert result['presentation']['imaging_plan']['status']=='NEEDS_ASSESSMENT_QUESTION'
    req,=result['pending_data_requests']
    assert req.required_fields[0].field_key=='imaging_assessment_question'
    updated=apply_response_to_state(state(),{'imaging_assessment_question':'What explains the presenting concern?'})
    result=imaging_agent_node({**state(),**updated})
    assert result['presentation']['imaging_plan']['status']=='WAITING_FOR_REPORT'
    assert 'What explains' in result['pending_data_requests'][0].reason


def test_unavailable_question_hands_off():
    initial=state();req=imaging_agent_node(initial)['pending_data_requests'][0]
    response={'imaging_assessment_question':'__unavailable__'}
    assert validate_response(req,response)[0]
    result=imaging_agent_node({**initial,**apply_response_to_state(initial,response)})
    assert result['current_step']=='imaging_manual_review_required'
    assert result['imaging_data'] is None


def test_report_is_available_not_question_resolved():
    initial=state();initial['imaging_decision'].update(assessment_question='What explains the concern?',report='Supplied report')
    result=imaging_agent_node(initial)
    assert result['presentation']['imaging_plan']['question_status']=='REPORT_AVAILABLE_FOR_REVIEW'
    assert result['presentation']['imaging_plan']['evidence_status']=='INDICATION_NOT_INDEPENDENTLY_VERIFIED'
    assert result['imaging_data'].findings==[]


def test_changed_observations_invalidate_required_plan_and_report():
    initial=state();initial['imaging_decision'].update(assessment_question='What explains the concern?',report='Old report')
    result=imaging_agent_node(initial)
    changed={**initial,**result,'vitals':VitalSigns(heart_rate_bpm=110)}
    rerun=imaging_agent_node(changed)
    assert rerun['presentation']['imaging_plan']['status']=='NEEDS_DECISION'
    assert rerun['imaging_data'] is None
    assert rerun['presentation']['imaging_plan']['report'] is None
    new=apply_response_to_state(changed,{'imaging_decision':'optional','imaging_reason':'Reassessed'})
    assert new['imaging_response'] is None
    assert new['imaging_assessment_fingerprint'] is None


def test_unchanged_plan_does_not_repeat_confirmation():
    initial=state();initial['imaging_decision'].update(assessment_question='Question',report='Report')
    result=imaging_agent_node(initial)
    assert imaging_agent_node({**initial,**result})['current_step']=='imaging_report_provided'


def test_api_question_and_report_persist(client):
    legacy=decision('required',modality='CT',anatomy='chest');legacy.pop('assessment_question')
    path=start(client,legacy)
    req,=client.get(path+'/data-requests').json()
    assert req['pathway_name']=='Imaging assessment question'
    response=resolve(client,path,{'imaging_assessment_question':'What finding explains the concern?'})
    assert response.status_code==200,response.text
    assert response.json()['status']=='WAITING_FOR_CLINICAL_DATA'
    response=resolve(client,path,{'imaging_action':'submit_report','imaging_report':'Supplied clinician report'})
    assert response.status_code==200,response.text
    plan=client.get(path+'/results').json()['presentation']['imaging_plan']
    assert plan['assessment_question']=='What finding explains the concern?'
    assert plan['question_status']=='REPORT_AVAILABLE_FOR_REVIEW'


@pytest.mark.parametrize('value',['', '   ', '__unknown__', 123])
def test_invalid_question_answers_rejected(value):
    req=imaging_agent_node(state())['pending_data_requests'][0]
    assert not validate_response(req,{'imaging_assessment_question':value})[0]


def test_api_reassessment_requires_reconfirmation_and_discards_old_report(client):
    path=start(client,decision('required',modality='CT',anatomy='chest',report='Old supplied report'))
    assert client.get(path+'/results').json()['presentation']['imaging_plan']['status']=='REPORT_PROVIDED'
    response=client.post(path+'/reevaluate',json={'notes':'chest pain'})
    assert response.status_code==200,response.text
    assert response.json()['status']=='WAITING_FOR_CLINICAL_DATA'
    req,=client.get(path+'/data-requests').json()
    assert req['pathway_name']=='Imaging decision'
    assert client.get(path+'/results').json()['presentation']['imaging_plan']['report'] is None
    response=resolve(client,path,{'imaging_decision':'optional','imaging_reason':'Reassessed after new information'})
    assert response.status_code==200,response.text
    plan=client.get(path+'/results').json()['presentation']['imaging_plan']
    assert plan['status']=='SKIPPED' and plan['report'] is None
