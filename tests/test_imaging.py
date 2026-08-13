import pytest
from src.agents.imaging import analyze_chest_xray
from src.core.state import ClinicalState


def test_analyze_chest_xray_effusion():
    data = analyze_chest_xray("data/mock_patients/patient_001_cxr.png")
    assert data.modality == "CHEST_XRAY_PA"
    assert len(data.findings) > 0
    assert any(f.finding_name == "Pleural Effusion" for f in data.findings)


def test_analyze_chest_xray_pneumothorax():
    data = analyze_chest_xray("data/mock_patients/pneumothorax_scan.png")
    assert len(data.findings) > 0
    assert any(f.finding_name == "Pneumothorax" and f.clinical_significance == "CRITICAL" for f in data.findings)


def test_analyze_chest_xray_normal():
    data = analyze_chest_xray("data/mock_patients/normal_scan.png")
    assert len(data.findings) == 0
    assert "Clear lung fields" in data.impression


def test_imaging_missing_path_creates_request():
    from src.agents.imaging import imaging_agent_node
    state: ClinicalState = {
        "patient_id": "TEST-IMG-001",
        "demographics": None,
        "raw_notes": ["Chest X-Ray required. cxr_path=missing cxr_required=true"],
        "vitals": None,
        "risk_scores": [],
        "differentials": [],
        "imaging_data": None,
        "safety_flags": [],
        "symbolic_overrides": [],
        "evidence": [],
        "audit_trail": [],
        "current_step": "init",
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
    result = imaging_agent_node(state)
    assert "pending_data_requests" in result
    assert len(result["pending_data_requests"]) == 1
    req = result["pending_data_requests"][0]
    assert req.requesting_agent == "imaging"
    assert req.required_fields[0].field_key == "cxr_path"

