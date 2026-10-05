"""Limited legacy local checks. No comprehensive interaction provider is configured."""
from typing import List, Optional
from src.core.state import SafetyFlag, VitalSigns


ALLERGY_CROSS_REACTIVITY = {
    "penicillin": ["amoxicillin", "ampicillin", "piperacillin", "augmentin", "penicillin"],
    "sulfa": ["bactrim", "sulfamethoxazole", "sulfasalazine"],
    "aspirin": ["ibuprofen", "naproxen", "ketorolac", "aspirin"]
}


def check_drug_safety_profile(
    medications: List[str],
    allergies: List[str],
    vitals: Optional[VitalSigns] = None
) -> List[SafetyFlag]:
    """
    Legacy local alerts only; absence of alerts cannot establish medication safety.
    Rules require separate clinical review and do not cover dosing or organ function.
    """
    flags: List[SafetyFlag] = []
    medications = [m.strip() for m in medications if m.strip()]
    meds_lower = [m.lower() for m in medications]
    allergies_lower = [a.strip().lower() for a in allergies if a.strip()]

    # 1. Check Allergy Contraindications & Class Cross-Reactivity
    for med in medications:
        med_l = med.lower()
        for allergy in allergies_lower:
            # Check direct match
            is_match = allergy in med_l or med_l in allergy
            # Check class cross-reactivity mapping
            if not is_match and allergy in ALLERGY_CROSS_REACTIVITY:
                cross_meds = ALLERGY_CROSS_REACTIVITY[allergy]
                is_match = any(c_med in med_l for c_med in cross_meds)

            if is_match:
                flags.append(
                    SafetyFlag(
                        severity="CRITICAL",
                        category="ALLERGY_ALERT",
                        title=f"Allergy Warning: {med}",
                        description=f"Patient has documented allergy to '{allergy}', which matched a limited local rule for '{med}'. Confirm the allergy and medication clinically.",
                        source_agent="SafetyGuardrail"
                    )
                )

    # Limited legacy interaction rule; never a fallback for a successful provider.
    has_warfarin = any("warfarin" in m or "coumadin" in m for m in meds_lower)
    has_nsaid = any(n in m for m in meds_lower for n in ["ibuprofen", "naproxen", "aspirin", "ketorolac"])
    if has_warfarin and has_nsaid:
        flags.append(
            SafetyFlag(
                severity="HIGH",
                category="DRUG_INTERACTION",
                title="Major Interaction: Anticoagulant + NSAID",
                description="Concurrent use of Warfarin and NSAIDs significantly elevates GI bleeding risk.",
                source_agent="PharmacologyRuleEngine"
            )
        )

    # Vital observations are assessed by the scoped urgency node, not duplicate
    # treatment rules with different thresholds and no applicability checks.
    return flags


def medication_coverage(medications, allergies):
    return {
        'status': 'LIMITED_LOCAL_CHECKS',
        'interaction_provider': 'NOT_CONFIGURED',
        'rule_version': 'legacy-local-v1',
        'medication_history': 'RECORDED_UNVERIFIED' if any(m.strip() for m in medications) else 'NOT_RECORDED',
        'allergy_history': 'RECORDED_UNVERIFIED' if any(a.strip() for a in allergies) else 'NOT_RECORDED',
        'limitations': [
            'Comprehensive drug interaction checking is unavailable; no replacement provider is configured.',
            'Local text-match rules have limited coverage and require clinical review. No alerts does not establish safety.',
            'Empty lists do not establish no current medications or no known allergies.',
            'Dose, route, timing, ingredient normalization, renal and hepatic dosing are not assessed.'
        ]
    }
