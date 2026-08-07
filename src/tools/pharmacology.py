from typing import List, Dict, Any
from src.core.state import SafetyFlag


def check_drug_interactions(medications: List[str], allergies: List[str]) -> List[SafetyFlag]:
    """
    Check active medication list against allergies and drug-drug interactions.
    """
    flags: List[SafetyFlag] = []
    meds_lower = [m.lower() for m in medications]
    allergies_lower = [a.lower() for a in allergies]

    # Check allergy contraindications
    for med in medications:
        med_l = med.lower()
        for allergy in allergies_lower:
            if allergy in med_l or med_l in allergy:
                flags.append(
                    SafetyFlag(
                        severity="CRITICAL",
                        category="ALLERGY_ALERT",
                        title=f"Direct Allergy Warning: {med}",
                        description=f"Patient has a documented allergy to '{allergy}', but was prescribed/taking '{med}'.",
                        source_agent="PharmacologyTool"
                    )
                )

    # Check known high-risk drug pairs (e.g. Warfarin + NSAID, ACEi + Potassium)
    has_warfarin = any("warfarin" in m or "coumadin" in m for m in meds_lower)
    has_nsaid = any(n in m for m in meds_lower for n in ["ibuprofen", "naproxen", "aspirin", "ketorolac"])
    
    if has_warfarin and has_nsaid:
        flags.append(
            SafetyFlag(
                severity="HIGH",
                category="DRUG_INTERACTION",
                title="Major Interaction: Anticoagulant + NSAID",
                description="Concurrent use of Warfarin and NSAIDs significantly elevates gastrointestinal bleeding risk.",
                source_agent="PharmacologyTool"
            )
        )

    return flags
