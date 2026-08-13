import pytest
from src.core.state import ClinicalState, PatientDemographics, VitalSigns
from src.core.graph import build_clinical_graph


from src.core.data_requests import resolve_request, apply_response_to_state


def test_clinical_graph_neuro_symbolic_execution():
    graph = build_clinical_graph()
    thread_config = {"configurable": {"thread_id": "test_phase3_session"}}

    demographics = PatientDemographics(
        patient_id="TEST-PAT-300",
        age=62,
        gender="Male",
        allergies=["Penicillin"],
        chronic_conditions=["Chronic Kidney Disease"],
        current_medications=["Warfarin 5mg", "Ibuprofen 400mg", "Metoprolol 25mg"]
    )
    
    vitals = VitalSigns(
        heart_rate_bpm=46.0,  # Bradycardia
        spo2_percent=91.0
    )

    initial_state: ClinicalState = {
        "patient_id": demographics.patient_id,
        "demographics": demographics,
        "raw_notes": ["Patient presents with chest pain, dyspnea, and leg swelling. cxr_path=data/mock_patients/patient_001_cxr.png"],
        "vitals": vitals,
        "risk_scores": [],
        "differentials": [],
        "imaging_data": None,
        "safety_flags": [],
        "symbolic_overrides": [],
        "evidence": [],
        "audit_trail": [],
        "current_step": "init",
        "error_logs": []
    }

    # 1. First invocation detects chest pain with missing ECG/Troponin -> pauses at 'data_request_review'
    graph.invoke(initial_state, config=thread_config)
    snapshot = graph.get_state(thread_config)

    assert snapshot.next == ("data_request_review",)
    assert len(snapshot.values["pending_data_requests"]) == 1
    req = snapshot.values["pending_data_requests"][0]
    assert req.requesting_agent == "triage"

    # 2. Clinician supplies missing ECG & Troponin scores and resolves request
    resp = {"ecg_score": 1, "troponin_score": 0, "cardiac_risk_factors_count": 2}
    resolved = resolve_request(req, resp)
    state_updates = apply_response_to_state(snapshot.values, resp)
    state_updates["pending_data_requests"] = [resolved]
    state_updates["resolved_data_requests"] = [resolved]

    graph.update_state(thread_config, state_updates)
    graph.invoke(None, config=thread_config)
    snapshot2 = graph.get_state(thread_config)

    # Now graph should have executed triage -> imaging -> diagnostic -> evidence -> safety -> symbolic and paused at 'human_review'
    assert snapshot2.next == ("human_review",)
    assert snapshot2.values["imaging_data"] is not None
    assert len(snapshot2.values["differentials"]) > 0
    assert len(snapshot2.values["symbolic_overrides"]) > 0

    # 3. Third invocation: clinician approves and graph resumes to ehr_export
    graph.update_state(thread_config, {"approved_by_clinician": True})
    graph.invoke(None, config=thread_config)
    final_snapshot = graph.get_state(thread_config)

    assert final_snapshot.next == ()
    assert final_snapshot.values["current_step"] == "ehr_exported"


