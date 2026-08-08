import pytest
from src.core.state import (
    ClinicalState,
    PatientDemographics,
    VitalSigns,
    ImagingData,
    ImagingFinding,
    DiagnosticDifferential
)
from src.core.symbolic_rules import evaluate_symbolic_rules


def test_symbolic_rule_bradycardia_beta_blocker():
    demographics = PatientDemographics(
        patient_id="TEST-SYM-001",
        age=65,
        gender="Male",
        current_medications=["Metoprolol Tartrate 50mg"]
    )
    vitals = VitalSigns(heart_rate_bpm=45.0)

    state: ClinicalState = {
        "patient_id": "TEST-SYM-001",
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
        "current_step": "test",
        "error_logs": []
    }

    overrides = evaluate_symbolic_rules(state)
    assert len(overrides) > 0
    assert any(r.rule_id == "RULE_001_BRADYCARDIA_BETA_BLOCKER" for r in overrides)


def test_symbolic_rule_pneumothorax_emergency():
    imaging = ImagingData(
        image_path="scan.png",
        findings=[
            ImagingFinding(
                finding_name="Pneumothorax",
                confidence=0.92,
                clinical_significance="CRITICAL"
            )
        ]
    )

    state: ClinicalState = {
        "patient_id": "TEST-SYM-002",
        "demographics": None,
        "raw_notes": [],
        "vitals": None,
        "risk_scores": [],
        "differentials": [],
        "imaging_data": imaging,
        "safety_flags": [],
        "symbolic_overrides": [],
        "evidence": [],
        "audit_trail": [],
        "current_step": "test",
        "error_logs": []
    }

    overrides = evaluate_symbolic_rules(state)
    assert len(overrides) > 0
    assert any(r.rule_id == "RULE_002_TENSION_PNEUMOTHORAX" for r in overrides)
