import pytest
from src.core.state import ClinicalState, PatientDemographics, VitalSigns
from src.core.graph import build_clinical_graph


def test_clinical_graph_execution():
    graph = build_clinical_graph()
    
    demographics = PatientDemographics(
        patient_id="TEST-PAT-100",
        age=60,
        gender="Male",
        allergies=["Penicillin"],
        chronic_conditions=[],
        current_medications=["Warfarin 5mg", "Ibuprofen 400mg"]
    )
    
    vitals = VitalSigns(
        heart_rate_bpm=110.0,
        spo2_percent=89.0
    )

    initial_state: ClinicalState = {
        "patient_id": demographics.patient_id,
        "demographics": demographics,
        "raw_notes": ["Patient complains of severe chest pain and leg swelling."],
        "vitals": vitals,
        "risk_scores": [],
        "differentials": [],
        "safety_flags": [],
        "evidence": [],
        "audit_trail": [],
        "current_step": "init",
        "error_logs": []
    }

    final_state = graph.invoke(initial_state)

    assert len(final_state["differentials"]) > 0
    assert len(final_state["evidence"]) > 0
    assert len(final_state["safety_flags"]) > 0
    assert len(final_state["audit_trail"]) == 4  # 4 agent steps
    assert final_state["current_step"] == "safety_audited"
