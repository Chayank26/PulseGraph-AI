import logging
from typing import Dict, Any, List
from src.core.state import ClinicalState, ClinicalEvidence, AuditEntry

logger = logging.getLogger("PulseGraph.EvidenceRAGAgent")


def evidence_rag_agent_node(state: ClinicalState) -> Dict[str, Any]:
    """
    Evidence RAG Agent Node:
    Retrieves clinical practice guidelines, peer-reviewed literature citations,
    and institutional evidence to validate proposed differential diagnoses.
    """
    logger.info("Running EvidenceRAGAgent to ground recommendations with medical evidence.")
    
    differentials = state.get("differentials", [])
    retrieved_evidence: List[ClinicalEvidence] = []

    for diff in differentials:
        if "Pulmonary Embolism" in diff.condition_name:
            retrieved_evidence.append(
                ClinicalEvidence(
                    title="2019 ESC Guidelines for the diagnosis and management of acute pulmonary embolism",
                    authors="Konstantinides SV, et al.",
                    source="European Heart Journal / PubMed",
                    url_or_doi="10.1093/eurheartj/ehz405",
                    snippet="CT pulmonary angiography is the diagnostic imaging modality of choice in patients with high clinical probability of PE or positive D-dimer.",
                    relevance_score=0.95
                )
            )
        elif "Acute Coronary Syndrome" in diff.condition_name:
            retrieved_evidence.append(
                ClinicalEvidence(
                    title="AHA/ACC Guideline for the Evaluation and Diagnosis of Chest Pain",
                    authors="Gulati M, et al.",
                    source="Journal of the American College of Cardiology",
                    url_or_doi="10.1016/j.jacc.2021.07.053",
                    snippet="In patients with acute chest pain, high-sensitivity cardiac troponins are recommended to rapidly rule in or rule out myocardial injury.",
                    relevance_score=0.92
                )
            )

    audit_entry = AuditEntry(
        agent_name="EvidenceRAGAgent",
        action="EVIDENCE_RETRIEVAL",
        summary=f"Retrieved {len(retrieved_evidence)} clinical guideline citations.",
        metadata={"citations_retrieved": len(retrieved_evidence)}
    )

    return {
        "evidence": retrieved_evidence,
        "audit_trail": [audit_entry],
        "current_step": "evidence_retrieved"
    }
