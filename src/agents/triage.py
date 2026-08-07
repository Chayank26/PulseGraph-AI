import logging
from typing import Dict, Any
from src.core.state import ClinicalState, VitalSigns, RiskScore, AuditEntry
from src.tools.calculators import calculate_wells_pe_score

logger = logging.getLogger("PulseGraph.TriageAgent")


def triage_agent_node(state: ClinicalState) -> Dict[str, Any]:
    """
    Triage Agent Node:
    Ingests patient data, parses vitals/notes, and performs baseline clinical risk calculations.
    """
    logger.info(f"Running TriageAgent for Patient ID: {state.get('patient_id')}")
    
    # Simple extraction logic from raw notes for demonstration/baseline
    raw_notes = state.get("raw_notes", [])
    combined_notes = " ".join(raw_notes).lower()
    
    # Detect tachycardia or DVT signs in notes
    hr_gt_100 = "tachycardia" in combined_notes or "hr > 100" in combined_notes or "chest pain" in combined_notes
    dvt_signs = "leg swelling" in combined_notes or "dvt" in combined_notes
    
    new_risk_scores = []
    if hr_gt_100 or dvt_signs:
        wells_score = calculate_wells_pe_score(
            clinical_signs_dvt=dvt_signs,
            pe_most_likely=True,
            heart_rate_gt_100=hr_gt_100
        )
        new_risk_scores.append(wells_score)
        
    audit_entry = AuditEntry(
        agent_name="TriageAgent",
        action="INTAKE_TRIAGE",
        summary="Ingested patient notes, extracted initial vitals, and evaluated baseline risk scores.",
        metadata={"risk_scores_calculated": len(new_risk_scores)}
    )

    return {
        "risk_scores": new_risk_scores,
        "audit_trail": [audit_entry],
        "current_step": "triage_completed"
    }
