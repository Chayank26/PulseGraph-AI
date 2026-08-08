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
