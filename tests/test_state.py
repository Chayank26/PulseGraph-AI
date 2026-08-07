import pytest
from src.core.state import (
    ClinicalState,
    PatientDemographics,
    VitalSigns,
    RiskScore,
    DiagnosticDifferential,
    SafetyFlag,
    ClinicalEvidence,
    AuditEntry
)


def test_patient_demographics_validation():
    demographics = PatientDemographics(
        patient_id="TEST-001",
        age=45,
        gender="Female",
        allergies=["Aspirin"],
        chronic_conditions=["Asthma"],
        current_medications=["Albuterol"]
    )
    assert demographics.patient_id == "TEST-001"
    assert demographics.age == 45
    assert demographics.allergies == ["Aspirin"]


def test_risk_score_instantiation():
    score = RiskScore(
        score_name="BMI",
        value=24.5,
        unit="kg/m²",
        interpretation="Normal weight"
    )
    assert score.score_name == "BMI"
    assert score.value == 24.5


def test_clinical_state_structure():
    state: ClinicalState = {
        "patient_id": "TEST-001",
        "demographics": None,
        "raw_notes": ["Note 1"],
        "vitals": None,
        "risk_scores": [],
        "differentials": [],
        "safety_flags": [],
        "evidence": [],
        "audit_trail": [],
        "current_step": "init",
        "error_logs": []
    }
    assert state["patient_id"] == "TEST-001"
    assert state["current_step"] == "init"
