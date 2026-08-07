import logging
from typing import Dict, Any, List
from src.core.state import ClinicalState, SafetyFlag, AuditEntry
from src.tools.pharmacology import check_drug_interactions

logger = logging.getLogger("PulseGraph.SafetyAgent")


def safety_agent_node(state: ClinicalState) -> Dict[str, Any]:
    """
    Safety & Pharmacology Agent Node:
    Performs critical guardrail auditing, allergy verification, drug-drug interaction checks,
    and flags contraindications in recommended therapies.
    """
    logger.info("Running SafetyAgent to enforce clinical safety guardrails.")
    
    demographics = state.get("demographics")
    medications = demographics.current_medications if demographics else []
    allergies = demographics.allergies if demographics else []
    
    # Perform pharmacology safety check
    safety_flags: List[SafetyFlag] = check_drug_interactions(medications, allergies)

    # Perform vitals-based clinical safety alerts
    vitals = state.get("vitals")
    if vitals:
        if vitals.spo2_percent and vitals.spo2_percent < 90.0:
            safety_flags.append(
                SafetyFlag(
                    severity="CRITICAL",
                    category="VITAL_ALERT",
                    title="Hypoxia Warning",
                    description=f"Oxygen saturation is critically low ({vitals.spo2_percent}%). Immediate O2 supplementation recommended.",
                    source_agent="SafetyAgent"
                )
            )

    audit_entry = AuditEntry(
        agent_name="SafetyAgent",
        action="SAFETY_GUARDRAIL_AUDIT",
        summary=f"Safety audit complete. Flagged {len(safety_flags)} clinical alerts.",
        metadata={"flags_count": len(safety_flags)}
    )

    return {
        "safety_flags": safety_flags,
        "audit_trail": [audit_entry],
        "current_step": "safety_audited"
    }
