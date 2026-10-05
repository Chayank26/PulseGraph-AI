import math
from src.core.state import RiskScore


SOURCES = {
    'HEART Score': 'https://www.heartscore.nl/resources/flyer.pdf',
    'CURB-65 Score': 'https://doi.org/10.1136/thorax.58.5.377',
    'Wells Score (PE)': 'https://www.nice.org.uk/guidance/ng158/chapter/Recommendations',
}


def provenance(name):
    return {'rule_version': 'calculator-audit-v1', 'source': SOURCES[name],
            'review_status': 'PENDING_CLINICAL_REVIEW',
            'limitation': 'Score only; no patient-specific probability, treatment or disposition decision.'}


def number(value, name, integer=False, minimum=0, maximum=None):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or
            not math.isfinite(value) or value < minimum or
            (maximum is not None and value > maximum) or
            (integer and int(value) != value)):
        raise ValueError(f'{name} must be a finite valid numeric value')


def boolean(value, name):
    if type(value) is not bool:
        raise ValueError(f'{name} requires an explicit boolean')


def calculate_bmi(weight_kg: float, height_m: float) -> RiskScore:
    """Calculate Body Mass Index (BMI)."""
    number(weight_kg, "weight_kg", minimum=0.000001)
    number(height_m, "height_m")
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
    inputs = dict(clinical_signs_dvt=clinical_signs_dvt, pe_most_likely=pe_most_likely,
                  heart_rate_gt_100=heart_rate_gt_100, immobilization_surgery=immobilization_surgery,
                  previous_dvt_pe=previous_dvt_pe, hemoptysis=hemoptysis, malignancy=malignancy)
    for key, value in inputs.items():
        boolean(value, key)
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

    risk = ('PE likely' if score > 4 else 'PE unlikely') + ' (two-level Wells classification; does not confirm or exclude PE)'

    return RiskScore(
        score_name="Wells Score (PE)",
        value=score,
        unit="points",
        interpretation=risk,
        details={
            **inputs,
            **provenance('Wells Score (PE)')
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
    - risk_factors_count: count of cardiac risk factors (0 -> 0, 1-2 -> 1, >=3 -> 2; atherosclerotic history is not captured)
    - troponin_score: 0 (<=normal), 1 (1-3x normal), 2 (>3x normal)
    """
    for key, value in [('history_score', history_score), ('ecg_score', ecg_score), ('troponin_score', troponin_score)]:
        number(value, key, integer=True, maximum=2)
    number(age, 'age', integer=True, maximum=130)
    number(risk_factors_count, 'risk_factors_count', integer=True)
    age_pts = 0 if age < 45 else (1 if age < 65 else 2)
    rf_pts = 0 if risk_factors_count == 0 else (1 if risk_factors_count <= 2 else 2)
    
    total_score = float(
        history_score +
        ecg_score +
        age_pts +
        rf_pts +
        troponin_score
    )

    if total_score <= 3:
        risk = "HEART score band 0–3; clinician assessment required"
    elif total_score <= 6:
        risk = "HEART score band 4–6; clinician assessment required"
    else:
        risk = "HEART score band 7–10; clinician assessment required"

    return RiskScore(
        score_name="HEART Score",
        value=total_score,
        unit="points",
        interpretation=risk,
        details={
            **provenance('HEART Score'),
            "coverage_limitation": "Count-based risk component; established atherosclerotic disease is not separately captured. Do not treat as a complete HEART implementation.",
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
    - U: Legacy BUN >19 mg/dL; unit-contract correction pending (not urea mg/dL).
    - R: Respiratory rate >= 30 breaths/min
    - B: Blood pressure (Systolic < 90 mmHg or Diastolic <= 60 mmHg)
    - 65: Age >= 65 years
    """
    boolean(confusion, 'confusion')
    for key, value in [('bun_mg_dl', bun_mg_dl), ('respiratory_rate', respiratory_rate),
                       ('systolic_bp', systolic_bp), ('diastolic_bp', diastolic_bp)]:
        number(value, key)
    number(age, 'age', integer=True, maximum=130)
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
        risk = "CURB-65 score band 0–1; clinician assessment required"
    elif score == 2.0:
        risk = "CURB-65 score band 2; clinician assessment required"
    else:
        risk = "CURB-65 score band 3–5; clinician assessment required"

    return RiskScore(
        score_name="CURB-65 Score",
        value=score,
        unit="points",
        interpretation=risk,
        details={
            **provenance('CURB-65 Score'),
            "coverage_limitation": "Legacy BUN threshold >19 mg/dL retained pending explicit urea unit-contract correction.",
            "systolic_bp": systolic_bp, "diastolic_bp": diastolic_bp,
            "confusion": confusion,
            "bun_mg_dl": bun_mg_dl,
            "respiratory_rate": respiratory_rate,
            "low_bp": (systolic_bp < 90.0 or diastolic_bp <= 60.0),
            "age_ge_65": (age >= 65)
        }
    )
