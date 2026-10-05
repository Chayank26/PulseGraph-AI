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
    assert overrides == []


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
    assert overrides == []


def test_sepsis_and_contrast_legacy_triggers_cannot_issue_treatment():
    state = {'vitals': VitalSigns(blood_pressure_sys=80, respiratory_rate=24, temperature_c=39),
             'demographics': PatientDemographics(patient_id='P', chronic_conditions=['renal disease']),
             'differentials': [DiagnosticDifferential(condition_name='Example', likelihood='Not estimated',
                rationale='test', recommended_workup=['CT angiogram'])]}
    assert evaluate_symbolic_rules(state) == []


def test_node_exposes_unavailable_status_without_mutating_input():
    from src.agents.symbolic_guardrail import symbolic_guardrail_agent_node
    from src.core.presentation import extract_presentation, ClinicalPresentation
    from src.core.diagnostic import input_fingerprint
    state = {'presentation': extract_presentation('chest pain', []).model_dump(mode='json')}
    result = symbolic_guardrail_agent_node(state)
    assert result['symbolic_overrides'] == []
    assert result['audit_trail'][0].action == 'SYMBOLIC_RULES_UNAVAILABLE'
    review = result['presentation']['symbolic_review']
    assert review['status'] == 'UNAVAILABLE_PENDING_CLINICAL_REVIEW'
    assert len(review['rules']) == 4
    assert all(rule['status'] == 'DISABLED' for rule in review['rules'])
    assert not state['presentation']['symbolic_review']
    ClinicalPresentation.model_validate(result['presentation'])
    assert input_fingerprint(state) == input_fingerprint({**state, 'presentation': result['presentation']})


from test_triage_foundation import client


def test_api_persists_unavailable_symbolic_review(client):
    from test_optional_imaging import start, decision
    path = start(client, decision('no_imaging'))
    result = client.get(path + '/results').json()
    assert result['symbolic_overrides'] == []
    assert result['presentation']['symbolic_review']['status'] == 'UNAVAILABLE_PENDING_CLINICAL_REVIEW'
    # Downstream availability metadata must not invalidate current diagnostic inputs.
    assert client.post(path + '/approve', json={}).status_code == 200
