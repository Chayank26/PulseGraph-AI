import pytest
from src.core.state import ClinicalState, PatientDemographics, VitalSigns, ClinicalFieldRequirement
from src.agents.triage import triage_agent_node
from src.core.graph import build_clinical_graph
from src.core.data_requests import (
    create_data_request,
    get_pending_requests,
    validate_response,
    resolve_request,
    apply_response_to_state
)


@pytest.fixture
def base_state() -> ClinicalState:
    demographics = PatientDemographics(
        patient_id="PAT-PHASE4-001",
        age=55,
        gender="Female",
        allergies=[],
        chronic_conditions=[],
        current_medications=[]
    )
    vitals = VitalSigns(
        heart_rate_bpm=80.0,
        blood_pressure_sys=120.0,
        blood_pressure_dia=80.0,
        temperature_c=37.0,
        respiratory_rate=18.0,
        spo2_percent=98.0
    )
    return {
        "patient_id": demographics.patient_id,
        "demographics": demographics,
        "raw_notes": [],
        "vitals": vitals,
        "risk_scores": [],
        "differentials": [],
        "imaging_data": None,
        "safety_flags": [],
        "symbolic_overrides": [],
        "evidence": [],
        "audit_trail": [],
        "current_step": "initialized",
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


def test_1_no_age_requests_age_no_risk_scores(base_state):
    """TEST 1: No age -> request age -> no risk score calculated."""
    base_state["demographics"].age = None
    result = triage_agent_node(base_state)

    assert "pending_data_requests" in result
    assert len(result["pending_data_requests"]) == 1

    req = result["pending_data_requests"][0]
    assert req.requesting_agent == "triage"
    assert req.pathway_name == "Patient Intake"
    assert len(req.required_fields) == 1
    assert req.required_fields[0].field_key == "age"
    assert result["current_step"] == "intake_age_required"
    assert len(result.get("risk_scores", [])) == 0


def test_2_age_present_no_pathway_symptoms_completes_without_inventing_data(base_state):
    """TEST 2: Age present, no symptoms requiring a conditional pathway -> triage completes without inventing data."""
    base_state["raw_notes"] = ["Patient presenting for routine annual physical exam."]
    result = triage_agent_node(base_state)

    assert "pending_data_requests" not in result
    assert result["current_step"] == "triage_completed"
    assert len(result["risk_scores"]) == 0


def test_3_chest_pain_no_heart_inputs_requests_all_missing_heart_no_heart_score(base_state):
    """TEST 3: Age + chest pain, but no HEART inputs -> request all missing HEART inputs -> no HEART score."""
    base_state["raw_notes"] = ["Patient presenting with acute chest pain."]
    result = triage_agent_node(base_state)

    assert "pending_data_requests" in result
    assert len(result["pending_data_requests"]) == 1

    req = result["pending_data_requests"][0]
    assert req.pathway_name == "HEART Score Assessment"
    field_keys = [f.field_key for f in req.required_fields]
    assert set(field_keys) == {"history_score", "ecg_score", "troponin_score", "cardiac_risk_factors_count"}
    assert result["current_step"] == "waiting_for_clinical_data"

    heart_scores = [s for s in result.get("risk_scores", []) if s.score_name == "HEART Score"]
    assert len(heart_scores) == 0


def test_4_chest_pain_only_ecg_requests_remaining_heart_inputs_no_heart_score(base_state):
    """TEST 4: Age + chest pain + only ECG -> request remaining HEART inputs -> no HEART score."""
    base_state["raw_notes"] = [
        "Patient presenting with acute chest pain.",
        "[ACQUIRED CLINICAL DATA]: ecg_score = 1"
    ]
    result = triage_agent_node(base_state)

    assert "pending_data_requests" in result
    assert len(result["pending_data_requests"]) == 1

    req = result["pending_data_requests"][0]
    assert req.pathway_name == "HEART Score Assessment"
    field_keys = [f.field_key for f in req.required_fields]
    assert "history_score" in field_keys
    assert "troponin_score" in field_keys
    assert "cardiac_risk_factors_count" in field_keys
    assert "ecg_score" not in field_keys

    heart_scores = [s for s in result.get("risk_scores", []) if s.score_name == "HEART Score"]
    assert len(heart_scores) == 0


def test_5_chest_pain_all_heart_inputs_calculates_heart_exact_values_no_defaults(base_state):
    """TEST 5: Age + chest pain + all HEART inputs -> calculate HEART using exactly those values -> no defaults."""
    base_state["raw_notes"] = [
        "Patient presenting with acute chest pain.",
        "[ACQUIRED CLINICAL DATA]: history_score = 2",
        "[ACQUIRED CLINICAL DATA]: ecg_score = 1",
        "[ACQUIRED CLINICAL DATA]: troponin_score = 0",
        "[ACQUIRED CLINICAL DATA]: cardiac_risk_factors_count = 2"
    ]
    result = triage_agent_node(base_state)

    assert "pending_data_requests" not in result
    assert result["current_step"] == "triage_completed"
    heart_scores = [s for s in result["risk_scores"] if s.score_name == "HEART Score"]
    assert len(heart_scores) == 1
    # History(2) + ECG(1) + Age 55(1) + RF 2(1) + Trop(0) = 5.0
    assert heart_scores[0].value == 5.0


def test_6_dyspnea_missing_curb_data_requests_missing_fields_no_normal_fallbacks(base_state):
    """TEST 6: Age + shortness of breath + missing CURB-65 data -> request missing CURB-65 fields -> do not use normal BP/BUN/RR values."""
    base_state["raw_notes"] = ["Patient presenting with acute dyspnea."]
    base_state["vitals"] = None  # No vitals
    result = triage_agent_node(base_state)

    assert "pending_data_requests" in result
    assert len(result["pending_data_requests"]) == 1

    req = result["pending_data_requests"][0]
    assert req.pathway_name == "CURB-65 Pneumonia Assessment"
    field_keys = [f.field_key for f in req.required_fields]
    assert "confusion" in field_keys
    assert "bun_mg_dl" in field_keys
    assert "respiratory_rate" in field_keys
    assert "blood_pressure_sys" in field_keys
    assert "blood_pressure_dia" in field_keys

    curb_scores = [s for s in result.get("risk_scores", []) if s.score_name == "CURB-65 Score"]
    assert len(curb_scores) == 0


def test_7_dyspnea_all_curb_data_calculates_curb65_exact_supplied_values(base_state):
    """TEST 7: Age + dyspnea + all CURB data -> calculate CURB-65 with exactly supplied values."""
    base_state["raw_notes"] = [
        "Patient presenting with acute dyspnea.",
        "[ACQUIRED CLINICAL DATA]: confusion = False",
        "[ACQUIRED CLINICAL DATA]: bun_mg_dl = 24.0",
        "[ACQUIRED CLINICAL DATA]: pe_most_likely = False",
        "[ACQUIRED CLINICAL DATA]: clinical_signs_dvt = False",
        "[ACQUIRED CLINICAL DATA]: immobilization_surgery = False",
        "[ACQUIRED CLINICAL DATA]: previous_dvt_pe = False",
        "[ACQUIRED CLINICAL DATA]: hemoptysis = False",
        "[ACQUIRED CLINICAL DATA]: malignancy = False"
    ]
    result = triage_agent_node(base_state)

    assert "pending_data_requests" not in result
    curb_scores = [s for s in result["risk_scores"] if s.score_name == "CURB-65 Score"]
    assert len(curb_scores) == 1
    # BUN 24 (>19 -> +1), Confusion False (0), RR 18 (0), BP 120/80 (0), Age 55 (0) -> total 1.0
    assert curb_scores[0].value == 1.0


def test_8_wells_active_incomplete_criteria_requests_missing_never_assumes_false(base_state):
    """TEST 8: Wells pathway active with incomplete Wells criteria -> request missing criteria -> never assume False."""
    base_state["raw_notes"] = ["Patient presenting with leg swelling."]
    base_state["vitals"] = None
    result = triage_agent_node(base_state)

    assert "pending_data_requests" in result
    req = result["pending_data_requests"][0]
    assert req.pathway_name == "Wells PE Assessment"
    field_keys = [f.field_key for f in req.required_fields]
    assert set(field_keys) == {
        "heart_rate_gt_100",
        "pe_most_likely",
        "clinical_signs_dvt",
        "immobilization_surgery",
        "previous_dvt_pe",
        "hemoptysis",
        "malignancy"
    }

    wells_scores = [s for s in result.get("risk_scores", []) if s.score_name == "Wells Score (PE)"]
    assert len(wells_scores) == 0


def test_9_chest_pain_and_dyspnea_sequential_blocking_requests(base_state):
    """
    TEST 9: Patient has chest pain + dyspnea -> only the first blocking request should be generated
    -> execution should stop -> after resolution, resume and request the next missing pathway data.
    """
    base_state["raw_notes"] = ["Patient presenting with acute chest pain and shortness of breath."]

    # Step 1: First pass -> detects chest pain with missing HEART parameters -> generates ONLY 1 request (HEART) and stops
    res1 = triage_agent_node(base_state)
    assert len(res1["pending_data_requests"]) == 1
    req1 = res1["pending_data_requests"][0]
    assert req1.pathway_name == "HEART Score Assessment"
    assert res1["current_step"] == "waiting_for_clinical_data"

    # Resolve HEART request
    resp1 = {"history_score": 2, "ecg_score": 1, "troponin_score": 0, "cardiac_risk_factors_count": 2}
    resolved1 = resolve_request(req1, resp1)
    base_state["resolved_data_requests"] = [resolved1]
    base_state["pending_data_requests"] = []
    base_state["risk_scores"] = res1.get("risk_scores", [])

    # Step 2: Second pass -> calculates HEART score, detects missing CURB-65 parameters -> generates ONLY 1 request (CURB-65) and stops
    res2 = triage_agent_node(base_state)
    assert len(res2["pending_data_requests"]) == 1
    req2 = res2["pending_data_requests"][0]
    assert req2.pathway_name == "CURB-65 Pneumonia Assessment"
    assert res2["current_step"] == "waiting_for_clinical_data"
    assert len(res2["risk_scores"]) == 1  # HEART score calculated!

    # Resolve CURB-65 request
    resp2 = {"confusion": False, "bun_mg_dl": 14.0}
    resolved2 = resolve_request(req2, resp2)
    base_state["resolved_data_requests"] = [resolved1, resolved2]
    base_state["pending_data_requests"] = []
    base_state["risk_scores"] = res2["risk_scores"]

    # Step 3: Third pass -> calculates CURB-65 score, detects missing Wells parameters -> generates ONLY 1 request (Wells) and stops
    res3 = triage_agent_node(base_state)
    assert len(res3["pending_data_requests"]) == 1
    req3 = res3["pending_data_requests"][0]
    assert req3.pathway_name == "Wells PE Assessment"
    assert res3["current_step"] == "waiting_for_clinical_data"
    assert len(res3["risk_scores"]) == 2  # HEART + CURB calculated!


def test_10_resolved_request_uses_clinician_response_does_not_ask_again(base_state):
    """TEST 10: Resolved request contains clinician_response -> triage must use that response -> must not ask for the same field again."""
    base_state["raw_notes"] = ["Patient presenting with acute chest pain."]
    
    req = create_data_request(
        requesting_agent="triage",
        pathway_name="HEART Score Assessment",
        reason="Testing resolved response recovery",
        required_fields=[
            ClinicalFieldRequirement(field_key="history_score", label="History", data_type="enum", required=True),
            ClinicalFieldRequirement(field_key="ecg_score", label="ECG", data_type="enum", required=True),
            ClinicalFieldRequirement(field_key="troponin_score", label="Trop", data_type="enum", required=True),
            ClinicalFieldRequirement(field_key="cardiac_risk_factors_count", label="RF", data_type="int", required=True)
        ]
    )
    resolved = resolve_request(req, {"history_score": 2, "ecg_score": 1, "troponin_score": 0, "cardiac_risk_factors_count": 2})
    base_state["resolved_data_requests"] = [resolved]

    result = triage_agent_node(base_state)
    assert "pending_data_requests" not in result
    assert result["current_step"] == "triage_completed"
    heart_scores = [s for s in result["risk_scores"] if s.score_name == "HEART Score"]
    assert len(heart_scores) == 1
    assert heart_scores[0].value == 5.0


def test_11_invalid_inputs_rejected(base_state):
    """TEST 11: Invalid age / invalid enum / invalid numeric input -> do not calculate -> request correction."""
    # Invalid age range (age = 150)
    req_age = create_data_request(
        requesting_agent="triage",
        pathway_name="Patient Intake",
        reason="Age required",
        required_fields=[ClinicalFieldRequirement(field_key="age", label="Age", data_type="int", required=True)]
    )
    is_valid, errors = validate_response(req_age, {"age": 150})
    assert is_valid is False
    assert any("0 and 130" in e for e in errors)

    # Invalid HEART enum (history_score = 5)
    base_state["raw_notes"] = [
        "Patient presenting with chest pain.",
        "[ACQUIRED CLINICAL DATA]: history_score = 5"  # Invalid!
    ]
    result = triage_agent_node(base_state)
    assert "pending_data_requests" in result
    req = result["pending_data_requests"][0]
    field_keys = [f.field_key for f in req.required_fields]
    assert "history_score" in field_keys  # Requests valid history_score again!


def test_12_notes_omitting_condition_absence_from_notes_not_treated_as_false(base_state):
    """TEST 12: Notes omit a clinical condition -> absence from notes must NOT be treated as False."""
    base_state["raw_notes"] = ["Patient presents with shortness of breath."]
    result = triage_agent_node(base_state)

    # Absence of mention of hemoptysis, malignancy, etc. in raw_notes must NOT treat them as False!
    assert "pending_data_requests" in result
    req = result["pending_data_requests"][0]
    # In sequential mode, CURB-65 is requested first for shortness of breath
    assert req.pathway_name == "CURB-65 Pneumonia Assessment"
    field_keys = [f.field_key for f in req.required_fields]
    assert "confusion" in field_keys  # Not assumed False!
