import logging
from typing import Dict, Any, List
from src.core.state import ClinicalState, SafetyFlag, AuditEntry, ClinicalFieldRequirement
from src.core.data_requests import create_data_request
from src.tools.pharmacology import check_drug_safety_profile

logger = logging.getLogger("PulseGraph.SafetyAgent")


def safety_agent_node(state: ClinicalState) -> Dict[str, Any]:
    """
    Safety & Pharmacology Agent Node:
    Audits patient medications against RxNorm interaction databases, checks allergen cross-matching,
    evaluates dosage safety bounds, and flags vital sign threshold violations.
    
    Conditional Data Acquisition:
    If medication profile or allergy history is unrecorded when required for pharmacology auditing,
    generates a ClinicalDataRequest.
    """
    logger.info("Running SafetyAgent for clinical guardrail & RxNorm auditing...")
    
    notes = state.get("raw_notes", [])
    combined_notes = " ".join(notes).lower()
    
    demographics = state.get("demographics")
    medications = demographics.current_medications if demographics else []
    allergies = demographics.allergies if demographics else []
    vitals = state.get("vitals")

    # Check if medications are unrecorded when explicitly required for safety auditing
    if "meds_unrecorded" in combined_notes or "medications_missing" in combined_notes:
        logger.info("Medication history unrecorded for safety audit. Generating ClinicalDataRequest.")
        req = create_data_request(
            requesting_agent="safety",
            pathway_name="RxNorm Medication & Allergy Safety Audit",
            reason="Pharmacology safety auditing requires active medication history and document allergy records.",
            required_fields=[
                ClinicalFieldRequirement(
                    field_key="current_medications_list",
                    label="Current Active Medications",
                    data_type="str",
                    required=True,
                    description="Comma-separated list of active prescription and OTC medications"
                ),
                ClinicalFieldRequirement(
                    field_key="allergies_list",
                    label="Documented Allergies",
                    data_type="str",
                    required=False,
                    description="Documented drug or food allergies"
                )
            ],
            priority="HIGH"
        )
        audit_entry = AuditEntry(
            agent_name="SafetyAgent",
            action="DATA_REQUEST_CREATED",
            summary="Medication record unrecorded. Created ClinicalDataRequest.",
            metadata={"request_id": req.request_id}
        )
        return {
            "pending_data_requests": [req],
            "audit_trail": [audit_entry],
            "current_step": "safety_data_requested"
        }

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

