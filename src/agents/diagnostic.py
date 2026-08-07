import logging
from typing import Dict, Any, List
from src.core.state import ClinicalState, DiagnosticDifferential, AuditEntry

logger = logging.getLogger("PulseGraph.DiagnosticAgent")


def diagnostic_agent_node(state: ClinicalState) -> Dict[str, Any]:
    """
    Diagnostic Agent Node:
    Generates a structured clinical differential diagnosis based on patient demographics,
    vitals, raw clinical notes, and calculated risk scores.
    """
    logger.info("Running DiagnosticAgent to formulate clinical differential diagnoses.")
    
    raw_notes = " ".join(state.get("raw_notes", [])).lower()
    risk_scores = state.get("risk_scores", [])
    
    differentials: List[DiagnosticDifferential] = []

    # Simple heuristic/rule engine logic for baseline setup
    if "chest pain" in raw_notes or "shortness of breath" in raw_notes:
        differentials.append(
            DiagnosticDifferential(
                condition_name="Pulmonary Embolism",
                icd10_code="I26.99",
                likelihood="High" if any(r.score_name == "Wells Score (PE)" and r.value > 3 for r in risk_scores) else "Moderate",
                rationale="Patient presenting with acute chest discomfort and dyspnea with elevated clinical risk factors.",
                supporting_evidence=["Acute dyspnea", "Tachycardia", "Elevated Wells Score"],
                recommended_workup=["CT Pulmonary Angiogram", "D-dimer assay", "STAT ECG"]
            )
        )
        differentials.append(
            DiagnosticDifferential(
                condition_name="Acute Coronary Syndrome",
                icd10_code="I24.9",
                likelihood="Moderate",
                rationale="Acute chest pain warrants immediate exclusion of ischemic cardiac etiology.",
                supporting_evidence=["Chest pain on presentation"],
                recommended_workup=["Serial Troponin I/T", "12-Lead ECG", "Echocardiogram"]
            )
        )

    audit_entry = AuditEntry(
        agent_name="DiagnosticAgent",
        action="DIFFERENTIAL_GENERATION",
        summary=f"Generated {len(differentials)} candidate differential diagnoses.",
        metadata={"differentials_count": len(differentials)}
    )

    return {
        "differentials": differentials,
        "audit_trail": [audit_entry],
        "current_step": "diagnostic_completed"
    }
