"""Phase 1 regressions; isolated storage, no external services or model calls."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pydantic import ValidationError

from src.agents.triage import triage_agent_node
from src.core.clinical_parsing import parse_enum_score, parse_number
from src.core.data_requests import apply_response_to_state, create_data_request, validate_response
from src.core.state import PatientDemographics, VitalSigns, ClinicalFieldRequirement
from src.db.database import Base
from src.db.models import DoctorModel, PatientModel
from src.api.dependencies import get_db, get_current_clinician
from src.api.routes.sessions import router as sessions_router
from src.api.routes.clinical import router as clinical_router
from config.settings import settings


@pytest.mark.parametrize('value', ['20', '1garbage', '2.5', True, False, float('nan'), float('inf')])
def test_invalid_scores_are_not_coerced(value):
    assert parse_enum_score(value) is None
    request = create_data_request('triage', 'HEART', 'Missing score', [
        ClinicalFieldRequirement(field_key='history_score', label='History', data_type='enum', required=True)
    ])
    assert not validate_response(request, {'history_score': value})[0]


@pytest.mark.parametrize('value', [True, False, 'NaN', 'Infinity', float('-inf')])
def test_invalid_numbers_are_not_measurements(value):
    assert parse_number(value) is None
    with pytest.raises(ValidationError):
        VitalSigns(heart_rate_bpm=value)


def test_saved_complaint_activates_triage_without_duplicate_notes():
    result = triage_agent_node({'demographics': PatientDemographics(
        patient_id='P', age=50, chief_complaint='chest pain'), 'raw_notes': []})
    assert result['pending_data_requests'][0].pathway_name == 'Assessment applicability'


def test_resolved_vitals_create_structured_state_when_originally_missing():
    result = apply_response_to_state({'vitals': None}, {'respiratory_rate': 22, 'blood_pressure_sys': 120})
    assert result['vitals'].respiratory_rate == 22
    assert result['vitals'].blood_pressure_sys == 120
    assert result['vitals'].heart_rate_bpm is None


def test_fractional_age_is_rejected():
    request = create_data_request('triage', 'Intake', 'Age missing', [
        ClinicalFieldRequirement(field_key='age', label='Age', data_type='int', required=True)
    ])
    assert not validate_response(request, {'age': 42.7})[0]


@pytest.fixture
def client(monkeypatch):
    from differential_fixture import install
    install(monkeypatch)
    monkeypatch.setattr(settings, 'checkpoint_backend', 'memory')
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(DoctorModel(doctor_id='D', full_name='Test', department='Test', password_hash='unused'))
        db.add(PatientModel(patient_id='P', doctor_id='D', age=50, chief_complaint='shortness of breath'))
        db.commit()
    def database():
        with factory() as db:
            yield db
    app = FastAPI()
    from src.api.routes.patients import router as patients_router
    app.include_router(patients_router)
    app.include_router(sessions_router)
    app.include_router(clinical_router)
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_clinician] = lambda: DoctorModel(doctor_id='D', full_name='Test', department='Test')
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()


def test_saved_intake_survives_create_then_run_and_resolution(client):
    created = client.post('/api/clinical/sessions', json={
        'patient_id': 'P', 'pathway_decisions': {'curb65': 'applicable', 'wells': 'applicable'}, 'raw_notes': ['Symptoms started today'],
        'vitals': {'heart_rate_bpm': 80, 'respiratory_rate': 18,
                   'blood_pressure_sys': 120, 'blood_pressure_dia': 80},
    })
    assert created.status_code == 201, created.text
    path = '/api/clinical/sessions/' + created.json()['session_id']
    assert client.get(path).json()['intake_data']['vitals']['heart_rate_bpm'] == 80
    run = client.post(path + '/run')
    assert run.status_code == 200, run.text
    request = client.get(path + '/data-requests').json()[0]
    assert {f['field_key'] for f in request['required_fields']} == {'confusion', 'bun_mg_dl'}
    resolved = client.post(path + '/data-requests/' + request['request_id'] + '/resolve', json={
        'response_data': {'confusion': False, 'bun_mg_dl': 14}})
    assert resolved.status_code == 200, resolved.text
    next_request = client.get(path + '/data-requests').json()[0]
    assert next_request['pathway_name'] == 'Wells PE Assessment'
    assert next_request['request_id'] != request['request_id']
    assert 'heart_rate_gt_100' not in {f['field_key'] for f in next_request['required_fields']}
    results = client.get(path + '/results').json()
    assert results['risk_scores'][0]['score_name'] == 'CURB-65 Score'
    assert results['risk_scores'][0]['value'] == 0
    answered = {field['field_key']: False for field in next_request['required_fields']}
    result = client.post(path + '/data-requests/' + next_request['request_id'] + '/resolve',
                         json={'response_data': answered})
    assert result.status_code == 200, result.text
    scores = client.get(path + '/results').json()['risk_scores']
    assert [s['score_name'] for s in scores] == ['CURB-65 Score', 'Wells Score (PE)']
    assert client.get(path + '/data-requests').json()[0]['requesting_agent'] == 'imaging'



def test_run_object_body_and_invalid_intake(client):
    invalid = client.post('/api/clinical/sessions', json={'patient_id': 'P', 'vitals': {'spo2_percent': 101}})
    assert invalid.status_code == 422
    created = client.post('/api/clinical/sessions', json={'patient_id': 'P'})
    path = '/api/clinical/sessions/' + created.json()['session_id']
    result = client.post(path + '/run', json={'raw_notes': ['chest pain'], 'pathway_decisions': {'heart': 'applicable', 'curb65': 'applicable', 'wells': 'applicable'}, 'vitals': {'heart_rate_bpm': 80}})
    assert result.status_code == 200, result.text
    assert result.json()['pending_requests'][0]['pathway_name'] == 'HEART Score Assessment'
