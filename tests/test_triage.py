import pytest
from src.core.state import ClinicalState, PatientDemographics, VitalSigns
from src.agents.triage import triage_agent_node


@pytest.fixture
def base_clinical_state() -> ClinicalState:
    demographics = PatientDemographics(
        patient_id="PAT-TRIAGE-001",
        age=55,
        gender="Male",
        allergies=[],
        chronic_conditions=["Hypertension"],
        current_medications=[]
    )
    vitals = VitalSigns(
        heart_rate_bpm=82.0,
        blood_pressure_sys=125.0,
        blood_pressure_dia=82.0,
        temperature_c=37.0,
        respiratory_rate=18.0,
        spo2_percent=97.0
    )
    return {
        "patient_id": demographics.patient_id,
        "demographics": demographics,
        "raw_notes": ["Patient presenting with acute chest pain."],
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


def test_triage_chest_pain_missing_data_creates_request(base_clinical_state):
    """Test that chest pain without complete HEART parameters creates a ClinicalDataRequest and omits HEART score."""
    result = triage_agent_node(base_clinical_state)
    assert "pending_data_requests" in result
    assert len(result["pending_data_requests"]) == 1

    req = result["pending_data_requests"][0]
    assert req.requesting_agent == "triage"
    assert req.pathway_name == "HEART Score Assessment"
    assert len(req.required_fields) == 4

    field_keys = [f.field_key for f in req.required_fields]
    assert "history_score" in field_keys
    assert "ecg_score" in field_keys
    assert "troponin_score" in field_keys
    assert "cardiac_risk_factors_count" in field_keys

    # Confirm HEART score was not calculated prematurely
    heart_scores = [s for s in result["risk_scores"] if s.score_name == "HEART Score"]
    assert len(heart_scores) == 0


def test_triage_chest_pain_with_acquired_data_calculates_heart_score(base_clinical_state):
    """Test that chest pain with acquired HEART parameters calculates HEART score accurately."""
    base_clinical_state["raw_notes"] = [
        "Patient presenting with acute chest pain.",
        "[ACQUIRED CLINICAL DATA]: history_score = 2",
        "[ACQUIRED CLINICAL DATA]: ecg_score = 1",
        "[ACQUIRED CLINICAL DATA]: troponin_score = 0",
        "[ACQUIRED CLINICAL DATA]: cardiac_risk_factors_count = 2"
    ]
    result = triage_agent_node(base_clinical_state)
    assert "pending_data_requests" not in result

    heart_scores = [s for s in result["risk_scores"] if s.score_name == "HEART Score"]
    assert len(heart_scores) == 1
    assert heart_scores[0].value == 5.0  # History(2) + ECG(1) + Age 55(1) + Risk Factors 2(1) + Trop(0) = 5



def test_triage_missing_age_creates_intake_request(base_clinical_state):
    """Test that missing age creates a mandatory Patient Intake ClinicalDataRequest and pauses triage."""
    base_clinical_state["demographics"].age = None
    result = triage_agent_node(base_clinical_state)

    assert "pending_data_requests" in result
    assert len(result["pending_data_requests"]) == 1

    req = result["pending_data_requests"][0]
    assert req.requesting_agent == "triage"
    assert req.pathway_name == "Patient Intake"
    assert len(req.required_fields) == 1
    assert req.required_fields[0].field_key == "age"
    assert req.required_fields[0].required is True
    assert len(result["risk_scores"]) == 0


def test_triage_invalid_age_validation(base_clinical_state):
    """Test that validate_response rejects invalid patient ages."""
    from src.core.data_requests import create_data_request, validate_response
    from src.core.state import ClinicalFieldRequirement

    req = create_data_request(
        requesting_agent="triage",
        pathway_name="Patient Intake",
        reason="Age required",
        required_fields=[
            ClinicalFieldRequirement(field_key="age", label="Patient Age", data_type="int", required=True)
        ]
    )

    # Negative age
    is_valid, errors = validate_response(req, {"age": -5})
    assert is_valid is False
    assert any("0 and 130" in e for e in errors)

    # Age > 130
    is_valid, errors = validate_response(req, {"age": 150})
    assert is_valid is False
    assert any("0 and 130" in e for e in errors)

    # Valid age
    is_valid, errors = validate_response(req, {"age": 42})
    assert is_valid is True
    assert len(errors) == 0


