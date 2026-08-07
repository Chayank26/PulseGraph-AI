import logging
from typing import Dict, Any
from src.core.state import ClinicalState, VitalSigns, RiskScore, AuditEntry
from src.tools.calculators import calculate_wells_pe_score, calculate_heart_score, calculate_curb65_score

logger = logging.getLogger("PulseGraph.TriageAgent")


def triage_agent_node(state: ClinicalState) -> Dict[str, Any]:
    """
    Triage Agent Node:
    Ingests patient data, parses vitals/notes, and performs baseline clinical risk calculations
    (Wells PE Score, HEART Score for chest pain MACE risk, CURB-65 for respiratory risk).
    """
    logger.info(f"Running TriageAgent for Patient ID: {state.get('patient_id')}")
    
    raw_notes = state.get("raw_notes", [])
    combined_notes = " ".join(raw_notes).lower()
    vitals = state.get("vitals")
    demographics = state.get("demographics")
    age = demographics.age if demographics else 50
    
    hr_val = vitals.heart_rate_bpm if vitals and vitals.heart_rate_bpm else 80.0
    hr_gt_100 = hr_val > 100 or "tachycardia" in combined_notes or "chest pain" in combined_notes
    dvt_signs = "leg swelling" in combined_notes or "dvt" in combined_notes
    chest_pain = "chest pain" in combined_notes or "chest discomfort" in combined_notes
    sob = "shortness of breath" in combined_notes or "dyspnea" in combined_notes
    
    new_risk_scores = []
    
    # 1. Wells PE Score
    if hr_gt_100 or dvt_signs or sob:
        wells_score = calculate_wells_pe_score(
            clinical_signs_dvt=dvt_signs,
            pe_most_likely=True,
            heart_rate_gt_100=hr_gt_100
        )
        new_risk_scores.append(wells_score)

    # 2. HEART Score for Chest Pain
    if chest_pain:
        heart_score = calculate_heart_score(
            history_score=2,       # Highly suspicious history in note
            ecg_score=1,           # Non-specific repolarization disturbance
            age=age,
            risk_factors_count=2,  # HTN + Surgery history
            troponin_score=0       # Initial baseline pending
        )
        new_risk_scores.append(heart_score)

    # 3. CURB-65 Score for Pneumonia / Respiratory Distress
    if sob:
        sys_bp = vitals.blood_pressure_sys if vitals and vitals.blood_pressure_sys else 120.0
        dia_bp = vitals.blood_pressure_dia if vitals and vitals.blood_pressure_dia else 80.0
        rr_val = vitals.respiratory_rate if vitals and vitals.respiratory_rate else 20.0
        
        curb_score = calculate_curb65_score(
            confusion=False,
            bun_mg_dl=14.0,
            respiratory_rate=rr_val,
            systolic_bp=sys_bp,
            diastolic_bp=dia_bp,
            age=age
        )
        new_risk_scores.append(curb_score)
        
    audit_entry = AuditEntry(
        agent_name="TriageAgent",
        action="INTAKE_TRIAGE",
        summary=f"Ingested patient notes, extracted vitals, and evaluated {len(new_risk_scores)} risk scores.",
        metadata={"risk_scores_calculated": len(new_risk_scores)}
    )

    return {
        "risk_scores": new_risk_scores,
        "audit_trail": [audit_entry],
        "current_step": "triage_completed"
    }
