from typing import Dict, Any, Optional
from src.core.state import RiskScore


def calculate_bmi(weight_kg: float, height_m: float) -> RiskScore:
    """Calculate Body Mass Index (BMI)."""
    if height_m <= 0:
        raise ValueError("Height must be positive")
    
    bmi_val = round(weight_kg / (height_m ** 2), 2)
    if bmi_val < 18.5:
        category = "Underweight"
    elif 18.5 <= bmi_val < 25:
        category = "Normal weight"
    elif 25 <= bmi_val < 30:
        category = "Overweight"
    else:
        category = "Obesity"

    return RiskScore(
        score_name="BMI",
        value=bmi_val,
        unit="kg/m²",
        interpretation=category,
        details={"weight_kg": weight_kg, "height_m": height_m}
    )


def calculate_wells_pe_score(
    clinical_signs_dvt: bool = False,
    pe_most_likely: bool = False,
    heart_rate_gt_100: bool = False,
    immobilization_surgery: bool = False,
    previous_dvt_pe: bool = False,
    hemoptysis: bool = False,
    malignancy: bool = False
) -> RiskScore:
    """Calculate Wells' Criteria for Pulmonary Embolism (PE)."""
    score = 0.0
    if clinical_signs_dvt:
        score += 3.0
    if pe_most_likely:
        score += 3.0
    if heart_rate_gt_100:
        score += 1.5
    if immobilization_surgery:
        score += 1.5
    if previous_dvt_pe:
        score += 1.5
    if hemoptysis:
        score += 1.0
    if malignancy:
        score += 1.0

    if score > 6.0:
        risk = "High Risk (>65% PE probability)"
    elif score >= 2.0:
        risk = "Moderate Risk (~30% PE probability)"
    else:
        risk = "Low Risk (~1.3% PE probability)"

    return RiskScore(
        score_name="Wells Score (PE)",
        value=score,
        unit="points",
        interpretation=risk,
        details={
            "clinical_signs_dvt": clinical_signs_dvt,
            "pe_most_likely": pe_most_likely,
            "heart_rate_gt_100": heart_rate_gt_100
        }
    )
