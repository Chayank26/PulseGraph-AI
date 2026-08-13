import logging
from typing import Dict, Any, List
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
    logger.info(f"Running TriageAgent for Patient ID: {state.get('patient_id')}")
    
    raw_notes = state.get("raw_notes", [])
    combined_notes = " ".join(raw_notes).lower()
    vitals = state.get("vitals")
    demographics = state.get("demographics")
    age = demographics.age if demographics else None
    
    # Parse any acquired clinical parameters from notes
    acquired_data: Dict[str, Any] = {}
    for note in raw_notes:
        if note.startswith("[ACQUIRED CLINICAL DATA]: "):
            kv = note.replace("[ACQUIRED CLINICAL DATA]: ", "").split(" = ")
            if len(kv) == 2:
                key, val = kv[0].strip(), kv[1].strip()
                try:
                    acquired_data[key] = int(val) if val.isdigit() else float(val)
                except ValueError:
                    acquired_data[key] = val

    # Baseline symptom indicators
    chest_pain = "chest pain" in combined_notes or "chest discomfort" in combined_notes
    sob = "shortness of breath" in combined_notes or "dyspnea" in combined_notes
    dvt_signs = "leg swelling" in combined_notes or "dvt" in combined_notes

    # Heart rate gt 100 evaluation without assuming chest pain equals tachycardia
    hr_val = vitals.heart_rate_bpm if (vitals and vitals.heart_rate_bpm is not None) else None
    hr_gt_100 = False
    if hr_val is not None:
        hr_gt_100 = hr_val > 100.0
    elif "tachycardia" in combined_notes:
        hr_gt_100 = True

    new_risk_scores: List[RiskScore] = []
    pending_requests = []

    # 1. Wells PE Score (evaluated if DVT signs, tachycardia, or dyspnea present)
    if hr_gt_100 or dvt_signs or sob:
        wells_score = calculate_wells_pe_score(
            clinical_signs_dvt=dvt_signs,
            pe_most_likely=True,
            heart_rate_gt_100=hr_gt_100
        )
        new_risk_scores.append(wells_score)

    # 2. HEART Score for Chest Pain Risk Assessment
    if chest_pain:
        ecg_score = acquired_data.get("ecg_score")
        troponin_score = acquired_data.get("troponin_score")

        # Check if ECG score or Troponin score is missing
        if ecg_score is None or troponin_score is None:
            logger.info("Chest pain identified but mandatory ECG/Troponin scores missing. Generating ClinicalDataRequest.")
            req = create_data_request(
                requesting_agent="triage",
                pathway_name="HEART Score Assessment",
                reason="Chest pain presentation requires ECG classification and Troponin lab levels to calculate HEART MACE risk score.",
                required_fields=[
                    ClinicalFieldRequirement(
                        field_key="ecg_score",
                        label="ECG Findings Score",
                        data_type="enum",
                        required=True,
                        description="0 = Normal, 1 = Nonspecific repolarization disturbance, 2 = Significant ST depression",
                        options=["0 (Normal)", "1 (Nonspecific ST/T changes)", "2 (ST depression)"]
                    ),
                    ClinicalFieldRequirement(
                        field_key="troponin_score",
                        label="Troponin Level Score",
                        data_type="enum",
                        required=True,
                        description="0 = Normal (<1x limit), 1 = 1-3x normal limit, 2 = >3x normal limit",
                        options=["0 (<1x normal)", "1 (1-3x normal limit)", "2 (>3x normal limit)"]
                    )
                ],
                optional_fields=[
                    ClinicalFieldRequirement(
                        field_key="cardiac_risk_factors_count",
                        label="Cardiac Risk Factors Count",
                        data_type="int",
                        required=False,
                        description="Count of risk factors: HTN, Hyperlipidemia, DM, Obesity, Smoking, Family History"
                    )
                ],
                priority="HIGH"
            )
            pending_requests.append(req)
        else:
            # Complete data present -> Calculate deterministic HEART score
            patient_age = age if age is not None else 50
            risk_factors = acquired_data.get("cardiac_risk_factors_count", 2)
            heart_score = calculate_heart_score(
                history_score=2,  # Suspicious clinical history
                ecg_score=int(ecg_score),
                age=patient_age,
                risk_factors_count=int(risk_factors),
                troponin_score=int(troponin_score)
            )
            new_risk_scores.append(heart_score)

    # 3. CURB-65 Score for Pneumonia / Respiratory Distress
    if sob:
        sys_bp = vitals.blood_pressure_sys if (vitals and vitals.blood_pressure_sys is not None) else 120.0
        dia_bp = vitals.blood_pressure_dia if (vitals and vitals.blood_pressure_dia is not None) else 80.0
        rr_val = vitals.respiratory_rate if (vitals and vitals.respiratory_rate is not None) else 20.0
        patient_age = age if age is not None else 50
        
        curb_score = calculate_curb65_score(
            confusion=False,
            bun_mg_dl=14.0,
            respiratory_rate=rr_val,
            systolic_bp=sys_bp,
            diastolic_bp=dia_bp,
            age=patient_age
        )
        new_risk_scores.append(curb_score)
        
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

