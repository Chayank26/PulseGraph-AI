import pytest
from src.core.state import (
    ClinicalState,
    PatientDemographics,
    VitalSigns,
    ClinicianIdentity
)
from src.core.graph import build_clinical_graph
from src.core.data_requests import (
    get_pending_requests,
    validate_response,
    resolve_request,
    apply_response_to_state
)


def _get_field(obj, key):
    if hasattr(obj, key):
        return getattr(obj, key)
    elif isinstance(obj, dict):
        return obj.get(key)
    return None


def test_e2e_conditional_clinical_data_acquisition_flow():
    """
    End-to-End System Integration Test:
    Verifies the complete conditional clinical data acquisition lifecycle:
    1. Patient intake with chest pain missing ECG/Troponin triggers data request interrupt.
    2. Graph execution pauses cleanly before data_request_review.
    3. Clinician validates and submits missing lab/ECG values.
    4. Graph resumes directly back to requesting agent (Triage), calculates HEART score, and completes full pipeline.
    5. Physician reviews recommendations and approves EHR export.
    """
    graph = build_clinical_graph()
    thread_config = {"configurable": {"thread_id": "e2e_data_acquisition_session_001"}}

    demographics = PatientDemographics(
        patient_id="E2E-PAT-9901",
        age=58,
        gender="Male",
        blood_type="O+",
        allergies=["Penicillin"],
        chronic_conditions=["Hypertension", "Hyperlipidemia"],
        current_medications=["Metoprolol 25mg daily", "Atorvastatin 20mg daily"]
    )
    vitals = VitalSigns(
        heart_rate_bpm=48.0,  # Bradycardia
        blood_pressure_sys=135.0,
        blood_pressure_dia=85.0,
        temperature_c=37.1,
        respiratory_rate=22.0,
        spo2_percent=91.0
    )

    initial_state: ClinicalState = {
        "patient_id": demographics.patient_id,
        "demographics": demographics,
        "raw_notes": ["Patient presents with acute chest pain. cxr_path=data/mock_patients/patient_001_cxr.png"],
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

    # STEP 1: Initial invocation -> Triage detects chest pain with missing HEART parameters -> Pauses at data_request_review
    graph.invoke(initial_state, config=thread_config)
    snapshot1 = graph.get_state(thread_config)

    assert snapshot1.next == ("data_request_review",)
    pending_reqs = get_pending_requests(snapshot1.values)
    assert len(pending_reqs) == 1

    req = pending_reqs[0]
    assert req.requesting_agent == "triage"
    assert req.pathway_name == "HEART Score Assessment"
    assert req.status == "PENDING"

    # Verify HEART score was NOT calculated prematurely
    premature_heart = [s for s in snapshot1.values["risk_scores"] if _get_field(s, "score_name") == "HEART Score"]
    assert len(premature_heart) == 0

    # STEP 2: Clinician submits missing HEART parameters
    clinician_response = {
        "history_score": 2,                 # 2 = Highly suspicious history
        "ecg_score": 1,                     # 1 = Nonspecific repolarization disturbance
        "troponin_score": 0,                # 0 = Normal
        "cardiac_risk_factors_count": 2     # HTN + Hyperlipidemia
    }


    is_valid, errors = validate_response(req, clinician_response)
    assert is_valid is True
    assert len(errors) == 0

    resolved_req = resolve_request(req, clinician_response)
    assert resolved_req.status == "RESOLVED"
    assert resolved_req.resolved_at is not None

    state_updates = apply_response_to_state(snapshot1.values, clinician_response)
    state_updates["pending_data_requests"] = [resolved_req]
    state_updates["resolved_data_requests"] = [resolved_req]

    graph.update_state(thread_config, state_updates, as_node="data_request_review")


    # STEP 3: Resume graph -> Triage re-evaluates with complete data, calculates HEART score, completes pipeline -> Pauses at human_review
    graph.invoke(None, config=thread_config)
    snapshot2 = graph.get_state(thread_config)

    assert snapshot2.next == ("human_review",)
    assert snapshot2.values["imaging_data"] is not None
    assert len(snapshot2.values["differentials"]) > 0

    # Confirm HEART score is now calculated accurately
    heart_scores = [s for s in snapshot2.values["risk_scores"] if _get_field(s, "score_name") == "HEART Score"]
    assert len(heart_scores) == 1
    assert float(_get_field(heart_scores[0], "value")) == 5.0  # History(2) + ECG(1) + Age 58(1) + RF 2(1) + Trop(0) = 5.0

    # Confirm Symbolic Guardrail evaluated rule contraindication (Bradycardia + Metoprolol)
    symbolic_rules = snapshot2.values["symbolic_overrides"]
    assert len(symbolic_rules) > 0
    assert any(_get_field(r, "rule_id") == "RULE_001_BRADYCARDIA_BETA_BLOCKER" for r in symbolic_rules)

    # STEP 4: Attending physician reviews and approves care plan
    doctor = ClinicianIdentity(
        doctor_id="DOC-88204",
        full_name="Dr. Sarah Chen",
        department="Emergency Medicine",
        role="Attending Physician"
    )

    graph.update_state(
        thread_config,
        {
            "authenticated_clinician": doctor,
            "approved_by_clinician": True,
            "re_evaluation_requested": False,
            "clinician_notes": "Approved with Metoprolol hold."
        }
    )

    # STEP 5: Resume graph to EHR export
    graph.invoke(None, config=thread_config)
    final_snapshot = graph.get_state(thread_config)

    assert final_snapshot.next == ()
    assert final_snapshot.values["current_step"] == "ehr_exported"

    # Verify audit trail contains complete end-to-end execution log
    audit_agents = [_get_field(a, "agent_name") for a in final_snapshot.values["audit_trail"]]
    assert "TriageAgent" in audit_agents
    assert "DataRequestReviewNode" in audit_agents
    assert "ImagingAgent" in audit_agents
    assert "DiagnosticAgent" in audit_agents
    assert "EvidenceRAGAgent" in audit_agents
    assert "SafetyAgent" in audit_agents
    assert "SymbolicGuardrailAgent" in audit_agents
    assert "HumanReviewNode" in audit_agents
    assert "EHRExportNode" in audit_agents

