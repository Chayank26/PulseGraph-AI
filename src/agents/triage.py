import logging
from typing import Dict, Any, List, Optional
from src.core.state import ClinicalState, VitalSigns, RiskScore, AuditEntry, ClinicalFieldRequirement

from src.core.data_requests import create_data_request
from src.tools.calculators import calculate_wells_pe_score, calculate_heart_score, calculate_curb65_score

logger = logging.getLogger("PulseGraph.TriageAgent")


def parse_boolean(val: Any) -> Optional[bool]:
    """
    Safely parses a clinical boolean value.
    Returns True/False if valid, or None if missing or invalid.
    """
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        if val == 1:
            return True
        elif val == 0:
            return False
        return None
    val_str = str(val).strip().lower()
    if val_str in ("true", "1", "yes"):
        return True
    if val_str in ("false", "0", "no"):
        return False
    return None


def parse_enum_score(val: Any) -> Optional[int]:
    """
    Safely parses an enum score (e.g. history_score, ecg_score, troponin_score).
    Returns int 0, 1, or 2 if valid, or None if missing or invalid.
    """
    if val is None:
        return None
    if isinstance(val, int) and val in (0, 1, 2):
        return val
    val_str = str(val).strip()
    if not val_str:
        return None
    first_char = val_str[0]
    if first_char in ("0", "1", "2"):
        return int(first_char)
    return None


def parse_number(val: Any) -> Optional[float]:
    """
    Safely parses a numeric clinical measurement.
    Returns float if valid number, or None if missing or invalid.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        val_str = str(val).strip()
        if not val_str:
            return None
        return float(val_str)
    except (ValueError, TypeError):
        return None


def get_acquired_data(raw_notes: List[str], resolved_reqs: List[Any]) -> Dict[str, Any]:
    """
    Extracts acquired clinical parameters from raw_notes tags and resolved ClinicalDataRequests.
    """
    acquired: Dict[str, Any] = {}
    for note in raw_notes:
        if note.startswith("[ACQUIRED CLINICAL DATA]: "):
            kv = note.replace("[ACQUIRED CLINICAL DATA]: ", "").split(" = ")
            if len(kv) == 2:
                k, v = kv[0].strip(), kv[1].strip()
                b_val = parse_boolean(v)
                if b_val is not None:
                    acquired[k] = b_val
                else:
                    num_val = parse_number(v)
                    acquired[k] = num_val if num_val is not None else v

    for r in resolved_reqs:
        resp = r.clinician_response if hasattr(r, "clinician_response") else (r.get("clinician_response") if isinstance(r, dict) else None)
        if resp and isinstance(resp, dict):
            for k, v in resp.items():
                if k not in acquired and v is not None:
                    b_val = parse_boolean(v)
                    if b_val is not None:
                        acquired[k] = b_val
                    else:
                        num_val = parse_number(v)
                        acquired[k] = num_val if num_val is not None else v
    return acquired


def get_validated_age(demographics: Any, acquired_data: Dict[str, Any]) -> Optional[int]:
    """
    Retrieves and validates patient age from demographics or acquired data.
    Must be an integer between 0 and 130. Returns None if invalid or missing.
    """
    raw_age = demographics.age if (demographics and demographics.age is not None) else acquired_data.get("age")
    if raw_age is None:
        return None
    parsed = parse_number(raw_age)
    if parsed is not None and parsed.is_integer():
        age_int = int(parsed)
        if 0 <= age_int <= 130:
            return age_int
    return None


def triage_agent_node(state: ClinicalState) -> Dict[str, Any]:
    """
    Triage Agent Node:
    Ingests patient data, parses vitals and notes, and performs baseline clinical risk calculations
    (Wells PE Score, HEART Score for chest pain MACE risk, CURB-65 for respiratory risk).
    
    Conditional Data Acquisition:
    If required clinical parameters for an assessment pathway are missing, creates a structured
    ClinicalDataRequest instead of assuming false/normal values.
    """
    raw_notes = state.get("raw_notes", [])
    combined_notes = " ".join(raw_notes).lower()
    vitals = state.get("vitals")
    demographics = state.get("demographics")

    resolved_reqs = state.get("resolved_data_requests", [])
    acquired_data = get_acquired_data(raw_notes, resolved_reqs)
    age = get_validated_age(demographics, acquired_data)

    # Global Mandatory Patient Intake Check (Phase 1)
    if age is None:
        logger.warning("Patient age is missing or invalid. Creating mandatory Patient Intake ClinicalDataRequest.")
        req = create_data_request(
            requesting_agent="triage",
            pathway_name="Patient Intake",
            reason="Patient age is mandatory for initial intake, clinical risk assessment pathways, and dosing/safety algorithms.",
            required_fields=[
                ClinicalFieldRequirement(
                    field_key="age",
                    label="Patient Age",
                    data_type="int",
                    required=True,
                    description="Patient age in years (must be an integer between 0 and 130)"
                )
            ],
            priority="CRITICAL"
        )
        audit_entry = AuditEntry(
            agent_name="TriageAgent",
            action="MANDATORY_INTAKE_CHECK",
            summary="Intake paused. Patient age is missing and mandatory before clinical triage analysis.",
            metadata={"pending_requests_count": 1}
        )
        return {
            "risk_scores": [],
            "pending_data_requests": [req],
            "audit_trail": [audit_entry],
            "current_step": "intake_age_required"
        }


    # Baseline symptom indicators
    chest_pain = "chest pain" in combined_notes or "chest discomfort" in combined_notes
    sob = "shortness of breath" in combined_notes or "dyspnea" in combined_notes
    dvt_signs = "leg swelling" in combined_notes or "dvt" in combined_notes


    # Heart rate gt 100 evaluation using only structured vitals or explicit acquired data
    hr_val = vitals.heart_rate_bpm if (vitals and vitals.heart_rate_bpm is not None) else acquired_data.get("heart_rate_bpm")
    hr_gt_100: Optional[bool] = None
    if hr_val is not None:
        hr_gt_100 = float(hr_val) > 100.0
    elif "heart_rate_gt_100" in acquired_data and acquired_data["heart_rate_gt_100"] is not None:
        hr_gt_100 = bool(acquired_data["heart_rate_gt_100"])

    new_risk_scores: List[RiskScore] = []
    pending_requests = []



    # 1. HEART Score for Chest Pain Risk Assessment
    if chest_pain:
        history_val = parse_enum_score(acquired_data.get("history_score"))
        ecg_val = parse_enum_score(acquired_data.get("ecg_score"))
        trop_val = parse_enum_score(acquired_data.get("troponin_score"))
        rf_num = parse_number(acquired_data.get("cardiac_risk_factors_count"))
        rf_val = int(rf_num) if (rf_num is not None and rf_num >= 0 and rf_num.is_integer()) else None

        heart_missing = []
        if history_val is None:
            heart_missing.append(ClinicalFieldRequirement(
                field_key="history_score",
                label="Clinical History Suspicion Score",
                data_type="enum",
                required=True,
                description="0 = Slightly suspicious, 1 = Moderately suspicious, 2 = Highly suspicious",
                options=["0 (Slightly suspicious)", "1 (Moderately suspicious)", "2 (Highly suspicious)"]
            ))
        if ecg_val is None:
            heart_missing.append(ClinicalFieldRequirement(
                field_key="ecg_score",
                label="ECG Findings Score",
                data_type="enum",
                required=True,
                description="0 = Normal, 1 = Nonspecific repolarization disturbance, 2 = Significant ST depression",
                options=["0 (Normal)", "1 (Nonspecific ST/T changes)", "2 (ST depression)"]
            ))
        if trop_val is None:
            heart_missing.append(ClinicalFieldRequirement(
                field_key="troponin_score",
                label="Troponin Level Score",
                data_type="enum",
                required=True,
                description="0 = Normal (<1x limit), 1 = 1-3x normal limit, 2 = >3x normal limit",
                options=["0 (<1x normal)", "1 (1-3x normal limit)", "2 (>3x normal limit)"]
            ))
        if rf_val is None:
            heart_missing.append(ClinicalFieldRequirement(
                field_key="cardiac_risk_factors_count",
                label="Cardiac Risk Factors Count",
                data_type="int",
                required=True,
                description="Count of risk factors: HTN, Hyperlipidemia, DM, Obesity, Smoking, Family History"
            ))

        if heart_missing:
            logger.info("Chest pain identified but mandatory HEART score parameters missing or invalid. Generating ClinicalDataRequest.")
            req = create_data_request(
                requesting_agent="triage",
                pathway_name="HEART Score Assessment",
                reason="Chest pain presentation requires complete HEART score parameters (History, ECG, Troponin, and Risk Factors).",
                required_fields=heart_missing,
                priority="HIGH"
            )
            audit_entry = AuditEntry(
                agent_name="TriageAgent",
                action="DATA_REQUEST_CREATED",
                summary="HEART score pathway blocked waiting for missing parameters. Created ClinicalDataRequest.",
                metadata={"pathway": "HEART Score Assessment", "missing_fields_count": len(heart_missing)}
            )
            return {
                "risk_scores": new_risk_scores,
                "pending_data_requests": [req],
                "audit_trail": [audit_entry],
                "current_step": "waiting_for_clinical_data"
            }
        else:
            heart_score = calculate_heart_score(
                history_score=history_val,
                ecg_score=ecg_val,
                age=age,
                risk_factors_count=rf_val,
                troponin_score=trop_val
            )
            new_risk_scores.append(heart_score)



    # 2. CURB-65 Score for Pneumonia / Respiratory Distress
    if sob:
        confusion = parse_boolean(acquired_data.get("confusion"))
        bun_val = parse_number(acquired_data.get("bun_mg_dl"))
        rr_val = vitals.respiratory_rate if (vitals and vitals.respiratory_rate is not None) else parse_number(acquired_data.get("respiratory_rate"))
        sys_bp = vitals.blood_pressure_sys if (vitals and vitals.blood_pressure_sys is not None) else parse_number(acquired_data.get("blood_pressure_sys"))
        dia_bp = vitals.blood_pressure_dia if (vitals and vitals.blood_pressure_dia is not None) else parse_number(acquired_data.get("blood_pressure_dia"))

        curb_missing = []
        if confusion is None:
            curb_missing.append(ClinicalFieldRequirement(
                field_key="confusion",
                label="New Disorientation / Confusion",
                data_type="bool",
                required=True,
                description="True if acute disorientation or AMT score <= 8, False otherwise"
            ))
        if bun_val is None:
            curb_missing.append(ClinicalFieldRequirement(
                field_key="bun_mg_dl",
                label="Blood Urea Nitrogen (BUN)",
                data_type="float",
                required=True,
                description="BUN level in mg/dL (>19 mg/dL is 1 point)"
            ))
        if rr_val is None:
            curb_missing.append(ClinicalFieldRequirement(
                field_key="respiratory_rate",
                label="Respiratory Rate",
                data_type="float",
                required=True,
                description="Breaths per minute (>= 30 is 1 point)"
            ))
        if sys_bp is None:
            curb_missing.append(ClinicalFieldRequirement(
                field_key="blood_pressure_sys",
                label="Systolic Blood Pressure",
                data_type="float",
                required=True,
                description="Systolic BP in mmHg (<90 mmHg is 1 point)"
            ))
        if dia_bp is None:
            curb_missing.append(ClinicalFieldRequirement(
                field_key="blood_pressure_dia",
                label="Diastolic Blood Pressure",
                data_type="float",
                required=True,
                description="Diastolic BP in mmHg (<=60 mmHg is 1 point)"
            ))

        if curb_missing:
            logger.info("Dyspnea identified but mandatory CURB-65 parameters missing. Generating ClinicalDataRequest.")
            req = create_data_request(
                requesting_agent="triage",
                pathway_name="CURB-65 Pneumonia Assessment",
                reason="Respiratory distress requires complete CURB-65 parameters (Confusion, BUN, Respiratory Rate, BP).",
                required_fields=curb_missing,
                priority="HIGH"
            )
            audit_entry = AuditEntry(
                agent_name="TriageAgent",
                action="DATA_REQUEST_CREATED",
                summary="CURB-65 pneumonia pathway blocked waiting for missing parameters. Created ClinicalDataRequest.",
                metadata={"pathway": "CURB-65 Pneumonia Assessment", "missing_fields_count": len(curb_missing)}
            )
            return {
                "risk_scores": new_risk_scores,
                "pending_data_requests": [req],
                "audit_trail": [audit_entry],
                "current_step": "waiting_for_clinical_data"
            }
        else:
            curb_score = calculate_curb65_score(
                confusion=confusion,
                bun_mg_dl=bun_val,
                respiratory_rate=rr_val,
                systolic_bp=sys_bp,
                diastolic_bp=dia_bp,
                age=age
            )
            new_risk_scores.append(curb_score)

    # 3. Wells PE Score (evaluated if DVT signs, tachycardia, or dyspnea present)
    if (hr_gt_100 is True) or dvt_signs or sob:
        pe_most_likely = parse_boolean(acquired_data.get("pe_most_likely"))
        clinical_dvt = parse_boolean(acquired_data.get("clinical_signs_dvt"))
        immob = parse_boolean(acquired_data.get("immobilization_surgery"))
        prev_dvt = parse_boolean(acquired_data.get("previous_dvt_pe"))
        hemoptysis = parse_boolean(acquired_data.get("hemoptysis"))
        malignancy = parse_boolean(acquired_data.get("malignancy"))


        wells_missing = []
        if hr_gt_100 is None:
            wells_missing.append(ClinicalFieldRequirement(
                field_key="heart_rate_gt_100",
                label="Heart Rate > 100 bpm",
                data_type="bool",
                required=True,
                description="True if heart rate is greater than 100 beats per minute"
            ))
        if pe_most_likely is None:
            wells_missing.append(ClinicalFieldRequirement(
                field_key="pe_most_likely",
                label="Pulmonary Embolism Most Likely Diagnosis",
                data_type="bool",
                required=True,
                description="True if PE is the primary differential or equally likely as alternative diagnosis"
            ))

        if clinical_dvt is None:
            wells_missing.append(ClinicalFieldRequirement(
                field_key="clinical_signs_dvt",
                label="Clinical Signs/Symptoms of DVT",
                data_type="bool",
                required=True,
                description="True if leg swelling or deep pain on palpation is present"
            ))
        if immob is None:
            wells_missing.append(ClinicalFieldRequirement(
                field_key="immobilization_surgery",
                label="Immobilization >= 3 Days or Surgery in Past 4 Weeks",
                data_type="bool",
                required=True,
                description="True if bedridden >=3 days or surgery within 4 weeks"
            ))
        if prev_dvt is None:
            wells_missing.append(ClinicalFieldRequirement(
                field_key="previous_dvt_pe",
                label="Previous Documented DVT or PE",
                data_type="bool",
                required=True,
                description="True if patient has history of DVT or PE"
            ))
        if hemoptysis is None:
            wells_missing.append(ClinicalFieldRequirement(
                field_key="hemoptysis",
                label="Hemoptysis (Coughing Blood)",
                data_type="bool",
                required=True,
                description="True if coughing up blood"
            ))
        if malignancy is None:
            wells_missing.append(ClinicalFieldRequirement(
                field_key="malignancy",
                label="Active Malignancy",
                data_type="bool",
                required=True,
                description="True if active cancer treated within 6 months"
            ))

        if wells_missing:
            logger.info("PE risk pathway active but mandatory Wells criteria missing. Generating ClinicalDataRequest.")
            req = create_data_request(
                requesting_agent="triage",
                pathway_name="Wells PE Assessment",
                reason="Pulmonary Embolism risk assessment requires explicit determination of all Wells criteria.",
                required_fields=wells_missing,
                priority="HIGH"
            )
            audit_entry = AuditEntry(
                agent_name="TriageAgent",
                action="DATA_REQUEST_CREATED",
                summary="Wells PE pathway blocked waiting for missing parameters. Created ClinicalDataRequest.",
                metadata={"pathway": "Wells PE Assessment", "missing_fields_count": len(wells_missing)}
            )
            return {
                "risk_scores": new_risk_scores,
                "pending_data_requests": [req],
                "audit_trail": [audit_entry],
                "current_step": "waiting_for_clinical_data"
            }
        else:
            wells_score = calculate_wells_pe_score(
                clinical_signs_dvt=bool(clinical_dvt),
                pe_most_likely=bool(pe_most_likely),
                heart_rate_gt_100=bool(hr_gt_100),
                immobilization_surgery=bool(immob),
                previous_dvt_pe=bool(prev_dvt),
                hemoptysis=bool(hemoptysis),
                malignancy=bool(malignancy)
            )
            new_risk_scores.append(wells_score)

    summary_msg = f"Triage complete. Evaluated {len(new_risk_scores)} risk scores."
    audit_entry = AuditEntry(
        agent_name="TriageAgent",
        action="INTAKE_TRIAGE",
        summary=summary_msg,
        metadata={
            "risk_scores_calculated": len(new_risk_scores),
            "pending_requests_count": 0
        }
    )

    return {
        "risk_scores": new_risk_scores,
        "audit_trail": [audit_entry],
        "current_step": "triage_completed"
    }




