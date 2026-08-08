import pytest
from src.core.state import ClinicalState, PatientDemographics, VitalSigns
from src.core.graph import build_clinical_graph


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

    # 1. First invocation pauses before 'human_review'
    graph.invoke(initial_state, config=thread_config)
    snapshot = graph.get_state(thread_config)

    assert snapshot.next == ("human_review",)
    assert snapshot.values["imaging_data"] is not None
    assert len(snapshot.values["differentials"]) > 0
    assert len(snapshot.values["symbolic_overrides"]) > 0

    # 2. Second invocation resumes to END
    graph.invoke(None, config=thread_config)
    final_snapshot = graph.get_state(thread_config)

    assert final_snapshot.next == ()
    assert final_snapshot.values["current_step"] == "clinician_approved"
    assert len(final_snapshot.values["audit_trail"]) == 7  # 6 agent nodes + 1 human_review
