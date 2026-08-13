import pytest
from src.core.state import ClinicalState, ClinicalFieldRequirement, ClinicalDataRequest, VitalSigns
from src.core.data_requests import (
    create_data_request,
    get_pending_requests,
    validate_response,
    resolve_request,
    has_resolved_request_for_pathway,
    apply_response_to_state
)


@pytest.fixture
def sample_field_requirements():
    return [
        ClinicalFieldRequirement(
            field_key="ecg_score",
            label="ECG Findings Score",
            data_type="int",
            required=True,
            description="0=Normal, 1=Nonspecific, 2=ST depression"
        ),
        ClinicalFieldRequirement(
            field_key="troponin_score",
            label="Troponin Score",
            data_type="int",
            required=True,
            description="0=Normal, 1=1-3x normal, 2=>3x normal"
        )
    ]


def test_create_data_request(sample_field_requirements):
    req = create_data_request(
        requesting_agent="triage",
        pathway_name="HEART Score Assessment",
        reason="Chest pain detected but ECG and Troponin scores are missing",
        required_fields=sample_field_requirements,
        priority="HIGH"
    )
    assert req.request_id.startswith("REQ-TRIAGE-")
    assert req.requesting_agent == "triage"
    assert req.pathway_name == "HEART Score Assessment"
    assert req.status == "PENDING"
    assert len(req.required_fields) == 2


def test_get_pending_requests(sample_field_requirements):
    req = create_data_request(
        requesting_agent="triage",
        pathway_name="HEART Score Assessment",
        reason="Missing data",
        required_fields=sample_field_requirements
    )
    state: ClinicalState = {
        "patient_id": "TEST-001",
        "demographics": None,
        "raw_notes": [],
        "vitals": None,
        "risk_scores": [],
        "differentials": [],
        "imaging_data": None,
        "safety_flags": [],
        "symbolic_overrides": [],
        "evidence": [],
        "audit_trail": [],
        "current_step": "init",
        "error_logs": [],
        "authenticated_clinician": None,
        "approved_by_clinician": None,
        "iteration_count": 0,
        "re_evaluation_requested": False,
        "clinician_notes": None,
        "pending_data_requests": [req],
        "resolved_data_requests": [],
        "active_data_request_id": req.request_id
    }
    pending = get_pending_requests(state)
    assert len(pending) == 1
    assert pending[0].request_id == req.request_id


def test_validate_response(sample_field_requirements):
    req = create_data_request(
        requesting_agent="triage",
        pathway_name="HEART Score",
        reason="Missing ECG & Troponin",
        required_fields=sample_field_requirements
    )

    # Valid response
    valid_resp = {"ecg_score": 1, "troponin_score": 0}
    is_valid, errors = validate_response(req, valid_resp)
    assert is_valid is True
    assert len(errors) == 0

    # Invalid response (missing troponin)
    invalid_resp = {"ecg_score": 1}
    is_valid, errors = validate_response(req, invalid_resp)
    assert is_valid is False
    assert len(errors) == 1
    assert "troponin_score" in errors[0]


def test_resolve_request(sample_field_requirements):
    req = create_data_request(
        requesting_agent="triage",
        pathway_name="HEART Score",
        reason="Missing data",
        required_fields=sample_field_requirements
    )
    resp = {"ecg_score": 1, "troponin_score": 0}
    resolved = resolve_request(req, resp)
    assert resolved.status == "RESOLVED"
    assert resolved.resolved_at is not None
    assert resolved.clinician_response == resp


def test_has_resolved_request_for_pathway(sample_field_requirements):
    req = create_data_request(
        requesting_agent="triage",
        pathway_name="HEART Score Assessment",
        reason="Missing data",
        required_fields=sample_field_requirements
    )
    resolved = resolve_request(req, {"ecg_score": 1, "troponin_score": 0})
    state: ClinicalState = {
        "patient_id": "TEST-001",
        "demographics": None,
        "raw_notes": [],
        "vitals": None,
        "risk_scores": [],
        "differentials": [],
        "imaging_data": None,
        "safety_flags": [],
        "symbolic_overrides": [],
        "evidence": [],
        "audit_trail": [],
        "current_step": "init",
        "error_logs": [],
        "authenticated_clinician": None,
        "approved_by_clinician": None,
        "iteration_count": 0,
        "re_evaluation_requested": False,
        "clinician_notes": None,
        "pending_data_requests": [],
        "resolved_data_requests": [resolved],
        "active_data_request_id": None
    }
    assert has_resolved_request_for_pathway(state, "triage", "HEART Score Assessment") is True
    assert has_resolved_request_for_pathway(state, "triage", "Wells Score Assessment") is False


def test_apply_response_to_state():
    vitals = VitalSigns(heart_rate_bpm=60.0, blood_pressure_sys=120.0, blood_pressure_dia=80.0)
    state: ClinicalState = {
        "patient_id": "TEST-001",
        "demographics": None,
        "raw_notes": ["Initial note"],
        "vitals": vitals,
        "risk_scores": [],
        "differentials": [],
        "imaging_data": None,
        "safety_flags": [],
        "symbolic_overrides": [],
        "evidence": [],
        "audit_trail": [],
        "current_step": "init",
        "error_logs": [],
        "authenticated_clinician": None,
        "approved_by_clinician": None,
        "iteration_count": 0,
        "re_evaluation_requested": False,
        "clinician_notes": None,
        "pending_data_requests": [],
        "resolved_data_requests": [],
        "active_data_request_id": None
    }
    resp = {
        "heart_rate_bpm": 88.0,
        "ecg_score": 1,
        "troponin_score": 0
    }
    updates = apply_response_to_state(state, resp)
    assert updates["vitals"].heart_rate_bpm == 88.0
    assert len(updates["raw_notes"]) == 2
    assert "[ACQUIRED CLINICAL DATA]: ecg_score = 1" in updates["raw_notes"]
