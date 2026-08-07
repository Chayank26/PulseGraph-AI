import pytest
from src.tools.calculators import calculate_heart_score, calculate_curb65_score
from src.tools.pharmacology import check_drug_safety_profile


def test_heart_score_low_risk():
    # Low risk parameters: History 0, ECG 0, Age 30 (<45 -> 0), RF 0, Troponin 0 -> Score 0
    score = calculate_heart_score(
        history_score=0,
        ecg_score=0,
        age=30,
        risk_factors_count=0,
        troponin_score=0
    )
    assert score.value == 0.0
    assert "Low Risk" in score.interpretation


def test_heart_score_high_risk():
    # High risk parameters: History 2, ECG 2, Age 70 (>=65 -> 2), RF 3 (>=3 -> 2), Troponin 2 -> Score 10
    score = calculate_heart_score(
        history_score=2,
        ecg_score=2,
        age=70,
        risk_factors_count=3,
        troponin_score=2
    )
    assert score.value == 10.0
    assert "High Risk" in score.interpretation


def test_curb65_score_severe():
    # Severe pneumonia: Confusion True, BUN 25 (>19), RR 32 (>=30), BP 85/50 (Sys <90), Age 68 (>=65) -> Score 5
    score = calculate_curb65_score(
        confusion=True,
        bun_mg_dl=25.0,
        respiratory_rate=32.0,
        systolic_bp=85.0,
        diastolic_bp=50.0,
        age=68
    )
    assert score.value == 5.0
    assert "High Mortality Risk" in score.interpretation


def test_drug_safety_allergy_alert():
    medications = ["Amoxicillin 500mg"]
    allergies = ["Penicillin"]
    flags = check_drug_safety_profile(medications, allergies)
    
    assert len(flags) > 0
    assert any(f.category == "ALLERGY_ALERT" for f in flags)
