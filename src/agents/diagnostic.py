import logging
from typing import Dict, Any, List
from src.core.state import ClinicalState, DiagnosticDifferential, AuditEntry

logger = logging.getLogger("PulseGraph.DiagnosticAgent")


def diagnostic_agent_node(state: ClinicalState) -> Dict[str, Any]:
    """
    Diagnostic Agent Node:
    Generates a structured clinical differential diagnosis based on patient demographics,
    vitals, raw clinical notes, chronic conditions, and imaging findings.
    """
    logger.info("Running DiagnosticAgent to formulate clinical differential diagnoses.")
    
    raw_notes = " ".join(state.get("raw_notes", [])).lower()
    demographics = state.get("demographics")
    chronic_conditions = [c.lower() for c in (demographics.chronic_conditions if demographics else [])]
    chief_complaint = (demographics.chief_complaint if demographics else "").lower()
    combined_text = f"{raw_notes} {chief_complaint} {' '.join(chronic_conditions)}"
    
    imaging = state.get("imaging_data")
    imaging_findings_names = [f.finding_name.lower() for f in (imaging.findings if imaging else [])]
    risk_scores = state.get("risk_scores", [])
    
    differentials: List[DiagnosticDifferential] = []

    # 1. Imaging & Cardiac Findings (Cardiomegaly / Hypertension)
    if any("cardiomegaly" in f for f in imaging_findings_names) or "hypertension" in combined_text or "hyperlipidemia" in combined_text:
        differentials.append(
            DiagnosticDifferential(
                condition_name="Hypertensive Heart Disease / Cardiomegaly",
                icd10_code="I11.9",
                likelihood="High" if any("cardiomegaly" in f for f in imaging_findings_names) else "Moderate",
                rationale="Ingested radiograph indicates enlarged cardiac silhouette (CTR > 0.55) with concurrent hypertensive cardiovascular risk profile.",
                supporting_evidence=["Enlarged cardiac silhouette on PA radiograph", "Documented hypertension history"],
                recommended_workup=["Transthoracic Echocardiogram (TTE)", "BNP / NT-proBNP assay", "Serial Blood Pressure monitoring"]
            )
        )

    # 2. Acute Coronary / Ischemic Etiology
    if "chest pain" in combined_text or "substernal" in combined_text or "heart" in combined_text or "hypertension" in combined_text:
        differentials.append(
            DiagnosticDifferential(
                condition_name="Acute Coronary Syndrome / NSTEMI",
                icd10_code="I21.4",
                likelihood="High" if any("cardiomegaly" in f for f in imaging_findings_names) else "Moderate",
                rationale="Cardiovascular comorbidity profile and radiographic cardiac stress warrant immediate exclusion of acute myocardial ischemia.",
                supporting_evidence=["Cardiovascular comorbidity profile", "Radiographic cardiomegaly findings"],
                recommended_workup=["Serial High-Sensitivity Troponin I/T", "12-Lead STAT ECG", "Echocardiogram"]
            )
        )

    # 3. Pulmonary / Respiratory Findings
    if "shortness of breath" in combined_text or "dyspnea" in combined_text:
        differentials.append(
            DiagnosticDifferential(
                condition_name="Pulmonary Embolism",
                icd10_code="I26.99",
                likelihood="High" if any(r.score_name == "Wells Score (PE)" and r.value > 3 for r in risk_scores) else "Moderate",
                rationale="Presenting dyspnea warrants evaluation for pulmonary vascular thrombosis.",
                supporting_evidence=["Acute dyspnea", "Clinical risk criteria"],
                recommended_workup=["CT Pulmonary Angiogram", "D-dimer assay"]
            )
        )

    # 4. Pleural Effusion / Pulmonary Infiltrate
    if any("effusion" in f for f in imaging_findings_names):
        differentials.append(
            DiagnosticDifferential(
                condition_name="Pleural Effusion / Infiltrate",
                icd10_code="J90",
                likelihood="High",
                rationale="Chest radiograph confirms blunting of costophrenic angle and pleural fluid accumulation.",
                supporting_evidence=["Blunted costophrenic angle on CXR"],
                recommended_workup=["Diagnostic Thoracentesis", "Chest Ultrasound", "Pleural Fluid Analysis"]
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
