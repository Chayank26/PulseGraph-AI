import pytest
from src.core.state import (
    ClinicalState,
    PatientDemographics,
    VitalSigns,
    RiskScore,
    DiagnosticDifferential,
    SafetyFlag,
    ClinicalEvidence,
    AuditEntry,
    ClinicalFieldRequirement,
    ClinicalDataRequest
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


def test_clinical_data_request_models():
    req_field = ClinicalFieldRequirement(
        field_key="troponin_score",
        label="Troponin Level",
        data_type="int",
        required=True,
        description="Troponin level score for HEART assessment"
    )
    request = ClinicalDataRequest(
        request_id="REQ-TRIAGE-HEART-001",
        requesting_agent="triage",
        pathway_name="HEART Score Assessment",
        reason="Troponin level is required to calculate HEART score",
        priority="HIGH",
        required_fields=[req_field],
        status="PENDING"
    )
    assert request.request_id == "REQ-TRIAGE-HEART-001"
    assert request.requesting_agent == "triage"
    assert len(request.required_fields) == 1
    assert request.required_fields[0].field_key == "troponin_score"
    assert request.required_fields[0].required is True
    assert request.status == "PENDING"

