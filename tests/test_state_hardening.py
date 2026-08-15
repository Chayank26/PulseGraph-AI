import pytest
from src.core.state import (
    ClinicalState,
    PatientDemographics,
    VitalSigns,
    ImagingData,
    ImagingFinding,
    ClinicianIdentity,
    ClinicalEvidence,
    SymbolicOverrideFlag,
    ClinicalDataRequest,
    ClinicalFieldRequirement
)
from src.agents.triage import triage_agent_node, get_acquired_data
from src.core.data_requests import create_data_request, resolve_request, validate_response


def test_missing_age_blocks_triage():
    """1. Missing age blocks triage."""
    state: ClinicalState = {
        "patient_id": "P-HARDEN-001",
        "demographics": PatientDemographics(patient_id="P-HARDEN-001", age=None, gender="Female"),
        "raw_notes": ["Routine intake."],
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
        "resolved_data_requests": [],
        "active_data_request_id": None
    }
    res = triage_agent_node(state)
    assert res["current_step"] == "intake_age_required"
    assert len(res["pending_data_requests"]) == 1
    assert len(res.get("risk_scores", [])) == 0


def test_missing_heart_data_blocks_heart_calculation():
    """2. Missing HEART data blocks HEART calculation."""
    state: ClinicalState = {
        "patient_id": "P-HARDEN-002",
        "demographics": PatientDemographics(patient_id="P-HARDEN-002", age=60, gender="Male"),
        "raw_notes": ["Patient presenting with acute chest pain."],
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
        "resolved_data_requests": [],
        "active_data_request_id": None
    }
    res = triage_agent_node(state)
    assert res["current_step"] == "waiting_for_clinical_data"
    assert len(res["pending_data_requests"]) == 1
    assert res["pending_data_requests"][0].pathway_name == "HEART Score Assessment"
    assert len([s for s in res.get("risk_scores", []) if s.score_name == "HEART Score"]) == 0


def test_missing_curb65_data_blocks_curb65_calculation():
    """3. Missing CURB-65 data blocks CURB-65 calculation."""
    state: ClinicalState = {
        "patient_id": "P-HARDEN-003",
        "demographics": PatientDemographics(patient_id="P-HARDEN-003", age=70, gender="Female"),
        "raw_notes": ["Patient presents with acute shortness of breath."],
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
        "resolved_data_requests": [],
        "active_data_request_id": None
    }
    res = triage_agent_node(state)
    assert res["current_step"] == "waiting_for_clinical_data"
    assert len(res["pending_data_requests"]) == 1
    assert res["pending_data_requests"][0].pathway_name == "CURB-65 Pneumonia Assessment"
    assert len([s for s in res.get("risk_scores", []) if s.score_name == "CURB-65 Score"]) == 0


def test_missing_wells_data_blocks_wells_calculation():
    """4. Missing Wells data blocks Wells calculation."""
    state: ClinicalState = {
        "patient_id": "P-HARDEN-004",
        "demographics": PatientDemographics(patient_id="P-HARDEN-004", age=45, gender="Male"),
        "raw_notes": ["Patient presenting with unilateral leg swelling."],
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
        "resolved_data_requests": [],
        "active_data_request_id": None
    }
    res = triage_agent_node(state)
    assert res["current_step"] == "waiting_for_clinical_data"
    assert len(res["pending_data_requests"]) == 1
    assert res["pending_data_requests"][0].pathway_name == "Wells PE Assessment"
    assert len([s for s in res.get("risk_scores", []) if s.score_name == "Wells Score (PE)"]) == 0


def test_invalid_clinician_responses_do_not_resolve_request():
    """5. Invalid clinician responses do not resolve a request."""
    req = create_data_request(
        requesting_agent="triage",
        pathway_name="HEART Score Assessment",
        reason="Testing invalid response rejection",
        required_fields=[
            ClinicalFieldRequirement(field_key="history_score", label="History Score", data_type="enum", required=True)
        ]
    )
    # Invalid enum value (5)
    is_valid, errors = validate_response(req, {"history_score": 5})
    assert is_valid is False
    assert len(errors) >= 1

    with pytest.raises(ValueError) as exc_info:
        resolve_request(req, {"history_score": 5})
    assert "Cannot resolve ClinicalDataRequest" in str(exc_info.value)
    assert req.status == "PENDING"


def test_request_cannot_be_resolved_with_missing_required_fields():
    """6. A request cannot be RESOLVED with missing required fields."""
    req = create_data_request(
        requesting_agent="triage",
        pathway_name="HEART Score Assessment",
        reason="Testing missing required field",
        required_fields=[
            ClinicalFieldRequirement(field_key="ecg_score", label="ECG Score", data_type="enum", required=True),
            ClinicalFieldRequirement(field_key="troponin_score", label="Troponin Score", data_type="enum", required=True)
        ]
    )
    # Missing troponin_score
    is_valid, errors = validate_response(req, {"ecg_score": 1})
    assert is_valid is False

    with pytest.raises(ValueError):
        resolve_request(req, {"ecg_score": 1})
    assert req.status == "PENDING"


def test_pending_requests_cannot_be_treated_as_acquired_data():
    """7. Pending requests cannot be treated as acquired data."""
    pending_req = create_data_request(
        requesting_agent="triage",
        pathway_name="HEART Score Assessment",
        reason="Missing data",
        required_fields=[
            ClinicalFieldRequirement(field_key="history_score", label="History Score", data_type="enum", required=True)
        ]
    )
    # Simulate clinician response attached to pending request object without resolution
    pending_req.clinician_response = {"history_score": 2}
    pending_req.status = "PENDING"

    # get_acquired_data must IGNORE pending requests!
    acquired = get_acquired_data(raw_notes=[], resolved_reqs=[])
    assert "history_score" not in acquired


def test_no_clinical_default_values_in_state_classes():
    """8. No clinical default values are introduced in state models."""
    demo = PatientDemographics(patient_id="P-001")
    assert demo.age is None

    vitals = VitalSigns()
    assert vitals.heart_rate_bpm is None
    assert vitals.blood_pressure_sys is None
    assert vitals.respiratory_rate is None
    assert vitals.spo2_percent is None

    img = ImagingData(image_path="test.png")
    assert img.impression is None  # Not default "Normal imaging study"

    finding = ImagingFinding(finding_name="Infiltrate", confidence=0.9)
    assert finding.clinical_significance is None  # Not default "MODERATE"

    clinician = ClinicianIdentity(doctor_id="D-1", full_name="Dr. Test", department="ER")
    assert clinician.role is None  # Not default "Attending Physician"

    ev = ClinicalEvidence(title="Guideline", source="PubMed", snippet="Text")
    assert ev.relevance_score is None  # Not default 0.0

    flag = SymbolicOverrideFlag(
        rule_id="R1",
        message="Test",
        deterministic_rule="IF A THEN B",
        action_required="Act"
    )
    assert flag.severity is None  # Not default "CRITICAL_OVERRIDE"
