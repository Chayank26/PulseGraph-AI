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
    clinical_signs_dvt: bool,
    pe_most_likely: bool,
    heart_rate_gt_100: bool,
    immobilization_surgery: bool,
    previous_dvt_pe: bool,
    hemoptysis: bool,
    malignancy: bool
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


def calculate_heart_score(
    history_score: int,
    ecg_score: int,
    age: int,
    risk_factors_count: int,
    troponin_score: int
) -> RiskScore:
    """
    Calculate HEART Score for Major Adverse Cardiac Events (MACE) in Emergency Department Chest Pain.
    
    Parameters:
    - history_score: 0 (slight), 1 (moderate), 2 (highly suspicious)
    - ecg_score: 0 (normal), 1 (non-specific repolarization), 2 (ST depression)
    - age: age in years (<45 -> 0, 45-64 -> 1, >=65 -> 2)
    - risk_factors_count: count of cardiac risk factors (0 -> 0, 1-2 -> 1, >=3 or CAD history -> 2)
    - troponin_score: 0 (<=normal), 1 (1-3x normal), 2 (>3x normal)
    """
    age_pts = 0 if age < 45 else (1 if age < 65 else 2)
    rf_pts = 0 if risk_factors_count == 0 else (1 if risk_factors_count <= 2 else 2)
    
    total_score = float(
        max(0, min(2, history_score)) +
        max(0, min(2, ecg_score)) +
        age_pts +
        rf_pts +
        max(0, min(2, troponin_score))
    )

    if total_score <= 3:
        risk = "Low Risk (0.9-1.7% MACE risk - Discharge Candidate)"
    elif total_score <= 6:
        risk = "Moderate Risk (12-16.6% MACE risk - Observation Unit / Inpatient)"
    else:
        risk = "High Risk (50-65% MACE risk - Immediate Invasive Intervention)"

    return RiskScore(
        score_name="HEART Score",
        value=total_score,
        unit="points",
        interpretation=risk,
        details={
            "history": history_score,
            "ecg": ecg_score,
            "age": age,
            "risk_factors": risk_factors_count,
            "troponin": troponin_score
        }
    )


def calculate_curb65_score(
    confusion: bool,
    bun_mg_dl: float,
    respiratory_rate: float,
    systolic_bp: float,
    diastolic_bp: float,
    age: int
) -> RiskScore:
    """
    Calculate CURB-65 Pneumonia Severity Score.
    
    Criteria (1 point each):
    - C: Confusion (abbreviated mental test score <= 8 or new disorientation)
    - U: Urea > 19 mg/dL (BUN > 19 mg/dL / 7 mmol/L)
    - R: Respiratory rate >= 30 breaths/min
    - B: Blood pressure (Systolic < 90 mmHg or Diastolic <= 60 mmHg)
    - 65: Age >= 65 years
    """
    score = 0.0
    if confusion:
        score += 1.0
    if bun_mg_dl > 19.0:
        score += 1.0
    if respiratory_rate >= 30.0:
        score += 1.0
    if systolic_bp < 90.0 or diastolic_bp <= 60.0:
        score += 1.0
    if age >= 65:
        score += 1.0

    if score <= 1.0:
        risk = "Low Mortality Risk (<1.5% - Outpatient Treatment)"
    elif score == 2.0:
        risk = "Moderate Mortality Risk (9.2% - Consider Hospital Admission)"
    else:
        risk = "High Mortality Risk (22-30% - Severe Pneumonia / ICU Consideration)"

    return RiskScore(
        score_name="CURB-65 Score",
        value=score,
        unit="points",
        interpretation=risk,
        details={
            "confusion": confusion,
            "bun_mg_dl": bun_mg_dl,
            "respiratory_rate": respiratory_rate,
            "low_bp": (systolic_bp < 90.0 or diastolic_bp <= 60.0),
            "age_ge_65": (age >= 65)
        }
    )
