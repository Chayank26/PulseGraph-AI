import logging
from typing import Dict, Any, List, Optional
from src.core.state import ClinicalState, VitalSigns, RiskScore, AuditEntry, ClinicalFieldRequirement

from src.core.data_requests import create_data_request
from src.tools.calculators import calculate_wells_pe_score, calculate_heart_score, calculate_curb65_score

logger = logging.getLogger("PulseGraph.TriageAgent")


def triage_agent_node(state: ClinicalState) -> Dict[str, Any]:
    """
    Triage Agent Node:
    Ingests patient data, parses vitals and notes, and performs baseline clinical risk calculations
    (Wells PE Score, HEART Score for chest pain MACE risk, CURB-65 for respiratory risk).
    
    Conditional Data Acquisition:
    If required clinical parameters for an assessment pathway (e.g. ECG score / Troponin level for HEART Score)
    are missing, creates a structured ClinicalDataRequest instead of assuming false/normal values.
    """
    raw_notes = state.get("raw_notes", [])
    combined_notes = " ".join(raw_notes).lower()
    vitals = state.get("vitals")
    demographics = state.get("demographics")

    
    # Parse any acquired clinical parameters from raw_notes and resolved_data_requests
    acquired_data: Dict[str, Any] = {}
    for note in raw_notes:
        if note.startswith("[ACQUIRED CLINICAL DATA]: "):
            kv = note.replace("[ACQUIRED CLINICAL DATA]: ", "").split(" = ")
            if len(kv) == 2:
                key, val = kv[0].strip(), kv[1].strip()
                if val.lower() == "true":
                    acquired_data[key] = True
                elif val.lower() == "false":
                    acquired_data[key] = False
                else:
                    try:
                        acquired_data[key] = int(val) if val.isdigit() else float(val)
                    except ValueError:
                        acquired_data[key] = val

    all_reqs = state.get("resolved_data_requests", []) + state.get("pending_data_requests", [])
    for r in all_reqs:
        resp = r.clinician_response if hasattr(r, "clinician_response") else (r.get("clinician_response") if isinstance(r, dict) else None)
        if resp and isinstance(resp, dict):
            for k, v in resp.items():
                if k not in acquired_data and v is not None:
                    if isinstance(v, str) and v.lower() == "true":
                        acquired_data[k] = True
                    elif isinstance(v, str) and v.lower() == "false":
                        acquired_data[k] = False
                    else:
                        try:
                            acquired_data[k] = int(v) if str(v).isdigit() else float(v)
                        except (ValueError, TypeError):
                            acquired_data[k] = v


    # Determine age from demographics or acquired data
    age = None
    if demographics and demographics.age is not None:
        try:
            val = int(demographics.age)
            if 0 <= val <= 130:
                age = val
        except (ValueError, TypeError):
            pass

    if age is None and "age" in acquired_data and acquired_data["age"] is not None:
        try:
            val = int(acquired_data["age"])
            if 0 <= val <= 130:
                age = val
        except (ValueError, TypeError):
            pass


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


    # Heart rate gt 100 evaluation without assuming chest pain equals tachycardia
    hr_val = vitals.heart_rate_bpm if (vitals and vitals.heart_rate_bpm is not None) else acquired_data.get("heart_rate_bpm")
    hr_gt_100: Optional[bool] = None
    if hr_val is not None:
        hr_gt_100 = float(hr_val) > 100.0
    elif "tachycardia" in combined_notes:
        hr_gt_100 = True
    elif "heart_rate_gt_100" in acquired_data:
        hr_gt_100 = bool(acquired_data["heart_rate_gt_100"])

    new_risk_scores: List[RiskScore] = []
    pending_requests = []


    # 1. HEART Score for Chest Pain Risk Assessment
    if chest_pain:
        history_score = acquired_data.get("history_score")
        ecg_score = acquired_data.get("ecg_score")
        troponin_score = acquired_data.get("troponin_score")
        cardiac_rf_count = acquired_data.get("cardiac_risk_factors_count")

        heart_missing = []
        if history_score is None:
            heart_missing.append(ClinicalFieldRequirement(
                field_key="history_score",
                label="Clinical History Suspicion Score",
                data_type="enum",
                required=True,
                description="0 = Slightly suspicious, 1 = Moderately suspicious, 2 = Highly suspicious",
                options=["0 (Slightly suspicious)", "1 (Moderately suspicious)", "2 (Highly suspicious)"]
            ))
        if ecg_score is None:
            heart_missing.append(ClinicalFieldRequirement(
                field_key="ecg_score",
                label="ECG Findings Score",
                data_type="enum",
                required=True,
                description="0 = Normal, 1 = Nonspecific repolarization disturbance, 2 = Significant ST depression",
                options=["0 (Normal)", "1 (Nonspecific ST/T changes)", "2 (ST depression)"]
            ))
        if troponin_score is None:
            heart_missing.append(ClinicalFieldRequirement(
                field_key="troponin_score",
                label="Troponin Level Score",
                data_type="enum",
                required=True,
                description="0 = Normal (<1x limit), 1 = 1-3x normal limit, 2 = >3x normal limit",
                options=["0 (<1x normal)", "1 (1-3x normal limit)", "2 (>3x normal limit)"]
            ))
        if cardiac_rf_count is None:
            heart_missing.append(ClinicalFieldRequirement(
                field_key="cardiac_risk_factors_count",
                label="Cardiac Risk Factors Count",
                data_type="int",
                required=True,
                description="Count of risk factors: HTN, Hyperlipidemia, DM, Obesity, Smoking, Family History"
            ))

        if heart_missing:
            logger.info("Chest pain identified but mandatory HEART score parameters missing. Generating ClinicalDataRequest.")
            req = create_data_request(
                requesting_agent="triage",
                pathway_name="HEART Score Assessment",
                reason="Chest pain presentation requires complete HEART score parameters (History, ECG, Troponin, and Risk Factors).",
                required_fields=heart_missing,
                priority="HIGH"
            )
            pending_requests.append(req)
        else:
            history_val = int(str(history_score)[0]) if isinstance(history_score, str) else int(history_score)
            ecg_val = int(str(ecg_score)[0]) if isinstance(ecg_score, str) else int(ecg_score)
            trop_val = int(str(troponin_score)[0]) if isinstance(troponin_score, str) else int(troponin_score)
            rf_val = int(cardiac_rf_count)

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
        confusion = acquired_data.get("confusion")
        bun_val = acquired_data.get("bun_mg_dl")
        rr_val = vitals.respiratory_rate if (vitals and vitals.respiratory_rate is not None) else acquired_data.get("respiratory_rate")
        sys_bp = vitals.blood_pressure_sys if (vitals and vitals.blood_pressure_sys is not None) else acquired_data.get("blood_pressure_sys")
        dia_bp = vitals.blood_pressure_dia if (vitals and vitals.blood_pressure_dia is not None) else acquired_data.get("blood_pressure_dia")

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
            pending_requests.append(req)
        else:
            curb_score = calculate_curb65_score(
                confusion=bool(confusion),
                bun_mg_dl=float(bun_val),
                respiratory_rate=float(rr_val),
                systolic_bp=float(sys_bp),
                diastolic_bp=float(dia_bp),
                age=age
            )
            new_risk_scores.append(curb_score)

    # 3. Wells PE Score (evaluated if DVT signs, tachycardia, or dyspnea present)
    if (hr_gt_100 is True) or dvt_signs or sob:
        pe_most_likely = acquired_data.get("pe_most_likely")
        clinical_dvt = acquired_data.get("clinical_signs_dvt")
        immob = acquired_data.get("immobilization_surgery")
        prev_dvt = acquired_data.get("previous_dvt_pe")
        hemoptysis = acquired_data.get("hemoptysis")
        malignancy = acquired_data.get("malignancy")

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
            pending_requests.append(req)
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
    if pending_requests:
        summary_msg += f" Created {len(pending_requests)} clinical data request(s)."

    audit_entry = AuditEntry(
        agent_name="TriageAgent",
        action="INTAKE_TRIAGE",
        summary=summary_msg,
        metadata={
            "risk_scores_calculated": len(new_risk_scores),
            "pending_requests_count": len(pending_requests)
        }
    )

    result: Dict[str, Any] = {
        "risk_scores": new_risk_scores,
        "audit_trail": [audit_entry],
        "current_step": "triage_completed"
    }

    if pending_requests:
        result["pending_data_requests"] = pending_requests

    return result


