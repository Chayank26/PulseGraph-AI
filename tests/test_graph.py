import pytest
from src.core.state import ClinicalState, PatientDemographics, VitalSigns
from src.core.graph import build_clinical_graph


def test_clinical_graph_hitl_checkpoint():
    graph = build_clinical_graph()
    thread_config = {"configurable": {"thread_id": "test_session_001"}}

    demographics = PatientDemographics(
        patient_id="TEST-PAT-200",
        age=62,
        gender="Male",
        allergies=["Penicillin"],
        chronic_conditions=["Hypertension"],
        current_medications=["Warfarin 5mg", "Ibuprofen 400mg"]
    )
    
    vitals = VitalSigns(
        heart_rate_bpm=110.0,
        spo2_percent=92.0
    )

    initial_state: ClinicalState = {
        "patient_id": demographics.patient_id,
        "demographics": demographics,
        "raw_notes": ["Patient presents with sudden chest pain and leg swelling."],
        "vitals": vitals,
        "risk_scores": [],
        "differentials": [],
        "safety_flags": [],
        "evidence": [],
        "audit_trail": [],
        "current_step": "init",
        "error_logs": []
    }

    # 1. First invocation pauses at 'human_review' breakpoint
    graph.invoke(initial_state, config=thread_config)
    snapshot = graph.get_state(thread_config)

    assert snapshot.next == ("human_review",)
    assert len(snapshot.values["differentials"]) > 0
    assert len(snapshot.values["evidence"]) > 0
    assert len(snapshot.values["safety_flags"]) > 0

    # 2. Resume graph invocation to completion
    graph.invoke(None, config=thread_config)
    final_snapshot = graph.get_state(thread_config)

    assert final_snapshot.next == ()  # Reached END
    assert final_snapshot.values["current_step"] == "clinician_approved"
    assert len(final_snapshot.values["audit_trail"]) == 5  # 4 agents + 1 human_review
