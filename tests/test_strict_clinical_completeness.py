import pytest
from src.core.state import ClinicalState, PatientDemographics, VitalSigns
from src.agents.triage import triage_agent_node
from src.core.graph import build_clinical_graph
from src.core.data_requests import (
    get_pending_requests,
    validate_response,
    resolve_request,
    apply_response_to_state
)


@pytest.fixture
def empty_clinical_state() -> ClinicalState:
    demographics = PatientDemographics(
        patient_id="PAT-PHASE9-001",
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


def test_1_chest_pain_missing_all_heart_parameters_creates_request_and_pauses(empty_clinical_state):
    """
    Behavior Scenario 1:
    A patient with chest pain + NO ECG / troponin / history suspicion / risk factors
    generates ClinicalDataRequest for HEART Score Assessment, pauses, and does NOT calculate HEART score.
    """
    empty_clinical_state["raw_notes"] = ["Patient presenting with acute chest pain."]
    result = triage_agent_node(empty_clinical_state)

    assert "pending_data_requests" in result
    heart_reqs = [r for r in result["pending_data_requests"] if r.pathway_name == "HEART Score Assessment"]
    assert len(heart_reqs) == 1

    req = heart_reqs[0]
    assert req.requesting_agent == "triage"
    field_keys = [f.field_key for f in req.required_fields]
    assert "history_score" in field_keys
    assert "ecg_score" in field_keys
    assert "troponin_score" in field_keys
    assert "cardiac_risk_factors_count" in field_keys

    # Must NOT calculate HEART score
    heart_scores = [s for s in result.get("risk_scores", []) if s.score_name == "HEART Score"]
    assert len(heart_scores) == 0


def test_2_dyspnea_missing_curb65_parameters_creates_request_and_pauses(empty_clinical_state):
    """
    Behavior Scenario 2:
    A patient with dyspnea + NO confusion / BUN
    generates ClinicalDataRequest for CURB-65 Pneumonia Assessment, pauses, and does NOT calculate CURB-65 score.
    """
    empty_clinical_state["raw_notes"] = ["Patient presenting with acute dyspnea."]
    result = triage_agent_node(empty_clinical_state)

    assert "pending_data_requests" in result
    curb_reqs = [r for r in result["pending_data_requests"] if r.pathway_name == "CURB-65 Pneumonia Assessment"]
    assert len(curb_reqs) == 1

    req = curb_reqs[0]
    assert req.requesting_agent == "triage"
    field_keys = [f.field_key for f in req.required_fields]
    assert "confusion" in field_keys
    assert "bun_mg_dl" in field_keys

    # Must NOT calculate CURB-65 score
    curb_scores = [s for s in result.get("risk_scores", []) if s.score_name == "CURB-65 Score"]
    assert len(curb_scores) == 0


def test_3_leg_swelling_missing_wells_criteria_creates_request_and_pauses(empty_clinical_state):
    """
    Behavior Scenario 3:
    A patient with leg swelling + NO explicit Wells criteria
    generates ClinicalDataRequest for Wells PE Assessment, pauses, and does NOT calculate Wells PE score.
    """
    empty_clinical_state["raw_notes"] = ["Patient presenting with leg swelling."]
    result = triage_agent_node(empty_clinical_state)

    assert "pending_data_requests" in result
    wells_reqs = [r for r in result["pending_data_requests"] if r.pathway_name == "Wells PE Assessment"]
    assert len(wells_reqs) == 1

    req = wells_reqs[0]
    assert req.requesting_agent == "triage"
    field_keys = [f.field_key for f in req.required_fields]
    assert "pe_most_likely" in field_keys
    assert "clinical_signs_dvt" in field_keys
    assert "immobilization_surgery" in field_keys
    assert "previous_dvt_pe" in field_keys
    assert "hemoptysis" in field_keys
    assert "malignancy" in field_keys

    # Must NOT calculate Wells PE score
    wells_scores = [s for s in result.get("risk_scores", []) if s.score_name == "Wells Score (PE)"]
    assert len(wells_scores) == 0


def test_4_missing_age_creates_intake_request_and_pauses(empty_clinical_state):
    """
    Behavior Scenario 4:
    A patient with missing age (demographics.age is None)
    generates ClinicalDataRequest for Patient Intake and pauses triage immediately.
    """
    empty_clinical_state["demographics"].age = None
    result = triage_agent_node(empty_clinical_state)

    assert "pending_data_requests" in result
    assert len(result["pending_data_requests"]) == 1

    req = result["pending_data_requests"][0]
    assert req.requesting_agent == "triage"
    assert req.pathway_name == "Patient Intake"
    assert len(req.required_fields) == 1
    assert req.required_fields[0].field_key == "age"
    assert req.required_fields[0].required is True

    # Must NOT calculate any risk scores
    assert len(result.get("risk_scores", [])) == 0


def test_5_providing_valid_responses_resolves_request_resumes_and_calculates(empty_clinical_state):
    """
    Behavior Scenario 5:
    Providing valid responses resolves ClinicalDataRequest, resumes graph execution,
    and calculates risk scores correctly.
    """
    graph = build_clinical_graph()
    thread_config = {"configurable": {"thread_id": "phase9_behavior_test_session"}}

    empty_clinical_state["raw_notes"] = ["Patient presenting with chest pain. cxr_path=data/mock_patients/patient_001_cxr.png"]

    # 1. Initial invocation -> missing HEART parameters -> pauses at data_request_review
    graph.invoke(empty_clinical_state, config=thread_config)
    snapshot1 = graph.get_state(thread_config)

    assert snapshot1.next == ("data_request_review",)
    pending_reqs = get_pending_requests(snapshot1.values)
    assert len(pending_reqs) == 1

    req = pending_reqs[0]
    assert req.pathway_name == "HEART Score Assessment"

    # 2. Clinician provides valid responses
    clinician_resp = {
        "history_score": 2,
        "ecg_score": 1,
        "troponin_score": 0,
        "cardiac_risk_factors_count": 2
    }

    is_valid, errors = validate_response(req, clinician_resp)
    assert is_valid is True
    assert len(errors) == 0

    resolved = resolve_request(req, clinician_resp)
    assert resolved.status == "RESOLVED"
    assert resolved.resolved_at is not None

    state_updates = apply_response_to_state(snapshot1.values, clinician_resp)
    state_updates["pending_data_requests"] = [resolved]
    state_updates["resolved_data_requests"] = [resolved]

    graph.update_state(thread_config, state_updates, as_node="data_request_review")

    # 3. Resume execution -> calculates HEART score correctly -> completes to human_review
    graph.invoke(None, config=thread_config)
    snapshot2 = graph.get_state(thread_config)

    assert snapshot2.next == ("human_review",)
    heart_scores = [s for s in snapshot2.values["risk_scores"] if s.score_name == "HEART Score"]
    assert len(heart_scores) == 1
    # History(2) + ECG(1) + Age 55(1) + RF 2(1) + Trop(0) = 5.0
    assert heart_scores[0].value == 5.0
