"""Phase 5 routing and persistence; no external services or image models."""
import pytest
from pydantic import ValidationError
from src.agents.imaging import imaging_agent_node
from src.core.imaging import ImagingDecision
from src.core.data_requests import validate_response
from src.core.state import PatientDemographics
from test_triage_foundation import client


def decision(kind='optional', **kwargs):
    return {'decision': kind, 'reason': 'Reviewed clinical context', **kwargs}


def evaluate(value=None, **extra):
    return imaging_agent_node({'demographics': PatientDemographics(patient_id='P', age=50, chief_complaint='chest pain'),
                               'raw_notes': [], 'imaging_decision': value, **extra})


@pytest.mark.parametrize('kind', ['no_imaging', 'optional'])
def test_optional_and_none_do_not_request_a_study(kind):
    result = evaluate(decision(kind))
    assert result['current_step'] == 'imaging_skipped'
    assert 'pending_data_requests' not in result
    assert result['imaging_data'] is None


def test_path_and_filename_are_not_an_interpretation():
    result = evaluate(decision(), image_path='pneumothorax_scan.png')
    assert result['imaging_data'] is None
    assert result['presentation']['imaging_plan']['study_reference'] == 'pneumothorax_scan.png'


def test_required_study_is_specific_and_does_not_default_to_chest():
    result = evaluate(decision('required', modality='Ultrasound', anatomy='abdomen'))
    assert 'Ultrasound of abdomen' in result['pending_data_requests'][0].reason
    assert result['presentation']['imaging_plan']['status'] == 'WAITING_FOR_REPORT'


@pytest.mark.parametrize('kind', ['optional', 'required'])
def test_existing_report_is_retained_verbatim_without_fabricated_findings(kind):
    result = evaluate(decision(kind, modality='MRI', anatomy='brain', report='No acute abnormality reported.'))
    assert result['current_step'] == 'imaging_report_provided'
    assert result['imaging_data'].findings == []
    assert result['imaging_data'].impression == 'No acute abnormality reported.'


def test_unknown_indication_hands_off():
    assert evaluate(decision('uncertain'))['current_step'] == 'imaging_manual_review_required'


@pytest.mark.parametrize('value', [decision('required'), decision(report='report'), decision(reason=' '), decision(reason=False)])
def test_invalid_intake_decisions_are_rejected(value):
    with pytest.raises(ValidationError):
        ImagingDecision.model_validate(value)


def test_override_requires_reason_and_report_action_requires_report():
    req = evaluate(decision('required', modality='CT', anatomy='abdomen'))['pending_data_requests'][0]
    for response in [{'imaging_action':'submit_report'}, {'imaging_action':'proceed_without_imaging'},
                     {'imaging_action':'clinician_assessment'}, {'imaging_action':'submit_report','imaging_report':5}]:
        assert not validate_response(req, response)[0]


def start(client, imaging=None):
    client.put('/api/patients/P', json={'chief_complaint':'chest pain'})
    payload = {'patient_id':'P', 'pathway_decisions':{'heart':'applicable'},
        'raw_notes':['history_score=0 ecg_score=0 troponin_score=0 cardiac_risk_factors_count=0']}
    if imaging: payload['imaging_decision'] = imaging
    created = client.post('/api/clinical/sessions', json=payload)
    assert created.status_code == 201, created.text
    path = '/api/clinical/sessions/' + created.json()['session_id']
    result = client.post(path+'/run')
    assert result.status_code == 200, result.text
    # Triage parsers may request the explicitly supplied score fields separately.
    reqs = client.get(path+'/data-requests').json()
    if reqs and reqs[0]['requesting_agent'] == 'triage':
        req = reqs[0]
        result = client.post(path+'/data-requests/'+req['request_id']+'/resolve',json={'response_data':{
            f['field_key']:0 for f in req['required_fields']}})
        assert result.status_code == 200, result.text
    return path


def resolve(client, path, payload):
    req = client.get(path+'/data-requests').json()[0]
    result = client.post(path+'/data-requests/'+req['request_id']+'/resolve', json={'response_data':payload})
    return result


@pytest.mark.parametrize('kind', ['optional','no_imaging'])
def test_api_skip_reaches_human_review_without_imaging(client,kind):
    path = start(client)
    result = resolve(client,path,{'imaging_decision':kind,'imaging_reason':'No study needed for this assessment'})
    assert result.status_code == 200, result.text
    assert result.json()['status'] == 'WAITING_FOR_CLINICIAN_REVIEW'
    plan = client.get(path+'/results').json()['presentation']['imaging_plan']
    assert plan['status'] == 'SKIPPED'
    assert plan['report'] is None
    assert client.get(path+'/data-requests').json() == []


def test_api_required_report_blocks_approval_then_persists(client):
    path = start(client,decision('required',modality='CT',anatomy='abdomen'))
    assert client.post(path+'/approve',json={}).status_code != 200
    invalid = resolve(client,path,{'imaging_action':'submit_report','imaging_report':''})
    assert invalid.status_code == 400
    result = resolve(client,path,{'imaging_action':'submit_report','imaging_report':'Clinician reviewed report text.'})
    assert result.status_code == 200, result.text
    assert result.json()['status'] == 'WAITING_FOR_CLINICIAN_REVIEW'
    data = client.get(path+'/results').json()
    assert data['presentation']['imaging_plan']['report'] == 'Clinician reviewed report text.'
    assert data['imaging_findings'] == []


@pytest.mark.parametrize('action,answer,status', [
    ('submit_report',{'imaging_report':'__unavailable__'},'REQUIRES_CLINICIAN_ASSESSMENT'),
    ('clinician_assessment',{'imaging_override_reason':'Need specialist review'},'REQUIRES_CLINICIAN_ASSESSMENT'),
    ('proceed_without_imaging',{'imaging_override_reason':'Study deferred after clinical review'},'WAITING_FOR_CLINICIAN_REVIEW')])
def test_api_unavailable_and_override_have_explicit_outcomes(client,action,answer,status):
    path = start(client,decision('required',modality='Ultrasound',anatomy='abdomen'))
    result = resolve(client,path,{'imaging_action':action,**answer})
    assert result.status_code == 200, result.text
    assert result.json()['status'] == status
    assert client.get(path+'/data-requests').json() == []


def test_api_existing_optional_report_at_intake(client):
    path = start(client,decision('optional',modality='MRI',anatomy='brain',report='Existing report text'))
    assert client.get(path).json()['status'] == 'WAITING_FOR_CLINICIAN_REVIEW'
    assert client.get(path+'/results').json()['presentation']['imaging_plan']['report'] == 'Existing report text'


def test_api_uncertain_does_not_run_diagnostic(client):
    path = start(client,decision('uncertain'))
    assert client.get(path).json()['status'] == 'REQUIRES_CLINICIAN_ASSESSMENT'
    assert client.get(path+'/results').json()['differentials'] == []


def test_api_imaging_request_exposes_optional_report_fields(client):
    path = start(client)
    req = client.get(path+'/data-requests').json()[0]
    assert 'imaging_report' in {f['field_key'] for f in req['optional_fields']}
    result = resolve(client,path,{'imaging_decision':'required','imaging_reason':'Reviewed'})
    assert result.status_code == 400
    assert client.get(path+'/data-requests').json()[0]['request_id'] == req['request_id']


def test_imaging_resolution_rejects_other_clinician(client):
    from src.api.dependencies import get_current_clinician
    from src.db.models import DoctorModel
    path = start(client)
    client.app.dependency_overrides[get_current_clinician] = lambda: DoctorModel(doctor_id='OTHER',full_name='Other')
    result = resolve(client,path,{'imaging_decision':'optional','imaging_reason':'Reviewed'})
    assert result.status_code == 400
    assert client.get(path+'/data-requests').json()


def test_start_rejects_other_clinician(client):
    from src.api.dependencies import get_current_clinician
    from src.db.models import DoctorModel
    path = '/api/clinical/sessions/' + client.post('/api/clinical/sessions',json={'patient_id':'P'}).json()['session_id']
    client.app.dependency_overrides[get_current_clinician] = lambda: DoctorModel(doctor_id='OTHER',full_name='Other')
    assert client.post(path+'/run',json={'imaging_decision':decision()}).status_code == 403


def test_urgent_review_precedes_imaging_even_if_report_exists(client):
    payload = {'patient_id':'P','imaging_decision':decision('required',modality='MRI',anatomy='brain',report='Existing report'),
        'urgency_context':{'clinician_concern':True}}
    path = '/api/clinical/sessions/' + client.post('/api/clinical/sessions',json=payload).json()['session_id']
    assert client.post(path+'/run').status_code == 200
    requests = client.get(path+'/data-requests').json()
    assert requests[0]['requesting_agent'] == 'urgency_check'
    results = client.get(path+'/results').json()
    assert not (results.get('presentation') or {}).get('imaging_plan')
