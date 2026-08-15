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


def test_triage_heart_parameter_validation():
    """Test that validate_response rejects invalid HEART score parameters."""
    from src.core.data_requests import create_data_request, validate_response
    from src.core.state import ClinicalFieldRequirement

    req = create_data_request(
        requesting_agent="triage",
        pathway_name="HEART Score Assessment",
        reason="HEART parameters required",
        required_fields=[
            ClinicalFieldRequirement(field_key="history_score", label="History Score", data_type="enum", required=True),
            ClinicalFieldRequirement(field_key="ecg_score", label="ECG Score", data_type="enum", required=True),
            ClinicalFieldRequirement(field_key="troponin_score", label="Troponin Score", data_type="enum", required=True),
            ClinicalFieldRequirement(field_key="cardiac_risk_factors_count", label="Risk Factors Count", data_type="int", required=True)
        ]
    )

    # Invalid history score (> 2)
    is_valid, errors = validate_response(req, {"history_score": 5, "ecg_score": 1, "troponin_score": 0, "cardiac_risk_factors_count": 2})
    assert is_valid is False

    # Negative risk factors count
    is_valid, errors = validate_response(req, {"history_score": 2, "ecg_score": 1, "troponin_score": 0, "cardiac_risk_factors_count": -1})
    assert is_valid is False

    # Valid HEART parameters
    is_valid, errors = validate_response(req, {"history_score": 2, "ecg_score": 1, "troponin_score": 0, "cardiac_risk_factors_count": 2})
    assert is_valid is True
    assert len(errors) == 0




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


def test_triage_curb65_missing_inputs_creates_request(base_clinical_state):
    """Test that shortness of breath without confusion and BUN creates a CURB-65 ClinicalDataRequest and omits score."""
    base_clinical_state["raw_notes"] = ["Patient presenting with acute shortness of breath."]
    result = triage_agent_node(base_clinical_state)

    assert "pending_data_requests" in result
    curb_reqs = [r for r in result["pending_data_requests"] if r.pathway_name == "CURB-65 Pneumonia Assessment"]
    assert len(curb_reqs) == 1

    req = curb_reqs[0]
    field_keys = [f.field_key for f in req.required_fields]
    assert "confusion" in field_keys
    assert "bun_mg_dl" in field_keys

    # Confirm CURB-65 score was not calculated
    curb_scores = [s for s in result["risk_scores"] if s.score_name == "CURB-65 Score"]
    assert len(curb_scores) == 0


def test_triage_curb65_with_acquired_data_calculates_score(base_clinical_state):
    """Test that shortness of breath with complete acquired CURB-65 data calculates score accurately."""
    base_clinical_state["raw_notes"] = [
        "Patient presenting with acute shortness of breath.",
        "[ACQUIRED CLINICAL DATA]: confusion = False",
        "[ACQUIRED CLINICAL DATA]: bun_mg_dl = 22.0",
        "[ACQUIRED CLINICAL DATA]: pe_most_likely = False",
        "[ACQUIRED CLINICAL DATA]: clinical_signs_dvt = False",
        "[ACQUIRED CLINICAL DATA]: immobilization_surgery = False",
        "[ACQUIRED CLINICAL DATA]: previous_dvt_pe = False",
        "[ACQUIRED CLINICAL DATA]: hemoptysis = False",
        "[ACQUIRED CLINICAL DATA]: malignancy = False"
    ]
    result = triage_agent_node(base_clinical_state)
    curb_reqs = [r for r in result.get("pending_data_requests", []) if r.pathway_name == "CURB-65 Pneumonia Assessment"]
    assert len(curb_reqs) == 0

    curb_scores = [s for s in result["risk_scores"] if s.score_name == "CURB-65 Score"]
    assert len(curb_scores) == 1
    # BUN 22.0 > 19 (+1), RR 18 (<30), SBP 125 / DBP 82 (normal), Age 55 (<65), Confusion False (0) -> total 1.0
    assert curb_scores[0].value == 1.0


def test_triage_wells_missing_inputs_creates_request(base_clinical_state):
    """Test that suspected PE without explicit Wells criteria creates a ClinicalDataRequest and omits score."""
    base_clinical_state["raw_notes"] = ["Patient presenting with leg swelling."]
    base_clinical_state["vitals"] = None  # Unknown heart rate
    result = triage_agent_node(base_clinical_state)

    assert "pending_data_requests" in result
    wells_reqs = [r for r in result["pending_data_requests"] if r.pathway_name == "Wells PE Assessment"]
    assert len(wells_reqs) == 1

    req = wells_reqs[0]
    field_keys = [f.field_key for f in req.required_fields]
    assert "heart_rate_gt_100" in field_keys
    assert "pe_most_likely" in field_keys
    assert "clinical_signs_dvt" in field_keys
    assert "immobilization_surgery" in field_keys
    assert "previous_dvt_pe" in field_keys
    assert "hemoptysis" in field_keys
    assert "malignancy" in field_keys

    # Confirm Wells score was not calculated prematurely
    wells_scores = [s for s in result["risk_scores"] if s.score_name == "Wells Score (PE)"]
    assert len(wells_scores) == 0



def test_triage_wells_with_acquired_data_calculates_score(base_clinical_state):
    """Test that complete acquired Wells criteria calculates Wells PE score accurately."""
    base_clinical_state["raw_notes"] = [
        "Patient presenting with leg swelling.",
        "[ACQUIRED CLINICAL DATA]: pe_most_likely = True",
        "[ACQUIRED CLINICAL DATA]: clinical_signs_dvt = True",
        "[ACQUIRED CLINICAL DATA]: immobilization_surgery = False",
        "[ACQUIRED CLINICAL DATA]: previous_dvt_pe = False",
        "[ACQUIRED CLINICAL DATA]: hemoptysis = False",
        "[ACQUIRED CLINICAL DATA]: malignancy = False"
    ]
    result = triage_agent_node(base_clinical_state)
    wells_reqs = [r for r in result.get("pending_data_requests", []) if r.pathway_name == "Wells PE Assessment"]
    assert len(wells_reqs) == 0

    wells_scores = [s for s in result["risk_scores"] if s.score_name == "Wells Score (PE)"]
    assert len(wells_scores) == 1
    # DVT signs (3.0) + PE most likely (3.0) = 6.0
    assert wells_scores[0].value == 6.0




