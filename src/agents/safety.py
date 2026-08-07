import logging
from typing import Dict, Any, List
from src.core.state import ClinicalState, SafetyFlag, AuditEntry
from src.tools.pharmacology import check_drug_safety_profile

logger = logging.getLogger("PulseGraph.SafetyAgent")


def safety_agent_node(state: ClinicalState) -> Dict[str, Any]:
    """
    Safety & Pharmacology Agent Node:
    Audits patient medications against RxNorm interaction databases, checks allergen cross-matching,
    evaluates dosage safety bounds, and flags vital sign threshold violations.
    """
    logger.info("Running SafetyAgent for clinical guardrail & RxNorm auditing...")
    
    demographics = state.get("demographics")
    medications = demographics.current_medications if demographics else []
    allergies = demographics.allergies if demographics else []
    vitals = state.get("vitals")

    # Run comprehensive safety profile check
    safety_flags: List[SafetyFlag] = check_drug_safety_profile(
        medications=medications,
        allergies=allergies,
        vitals=vitals
    )

    audit_entry = AuditEntry(
        agent_name="SafetyAgent",
        action="SAFETY_GUARDRAIL_AUDIT",
        summary=f"Pharmacology & safety audit complete. Identified {len(safety_flags)} clinical flags.",
        metadata={"flags_count": len(safety_flags)}
    )

    return {
        "safety_flags": safety_flags,
        "audit_trail": [audit_entry],
        "current_step": "safety_audited"
    }
