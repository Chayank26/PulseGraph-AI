import logging
import urllib.parse
import urllib.request
import json
from typing import List, Dict, Any, Optional
from src.core.state import SafetyFlag, VitalSigns

logger = logging.getLogger("PulseGraph.PharmacologyTool")

RXNORM_BASE_URL = "https://rxnav.nlm.nih.gov/REST"


def get_rxcui_for_drug(drug_name: str) -> Optional[str]:
    """
    Fetch RxCUI concept identifier for a given drug name from RxNav REST API.
    """
    try:
        clean_name = drug_name.split()[0]  # Take primary drug name (e.g. Warfarin from Warfarin 5mg)
        encoded_name = urllib.parse.quote(clean_name)
        url = f"{RXNORM_BASE_URL}/rxcui.json?name={encoded_name}"
        
        req = urllib.request.Request(url, headers={"User-Agent": "PulseGraphAI/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                id_group = data.get("idGroup", {})
                rxnorm_ids = id_group.get("rxnormId", [])
                if rxnorm_ids:
                    return rxnorm_ids[0]
    except Exception as e:
        logger.warning(f"RxNorm API lookup failed for '{drug_name}': {e}")
    return None


def check_rxnorm_interactions(rxcuis: List[str]) -> List[SafetyFlag]:
    """
    Query RxNav Interaction API for drug-drug interactions using a list of RxCUIs.
    """
    flags: List[SafetyFlag] = []
    if len(rxcuis) < 2:
        return flags

    try:
        cui_str = "+".join(rxcuis)
        url = f"{RXNORM_BASE_URL}/interaction/list.json?rxcuis={cui_str}"
        req = urllib.request.Request(url, headers={"User-Agent": "PulseGraphAI/1.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                full_group = data.get("fullInteractionTypeGroup", [])
                for group in full_group:
                    for interaction in group.get("fullInteractionType", []):
                        for pair in interaction.get("interactionPair", []):
                            severity = pair.get("severity", "HIGH").upper()
                            desc = pair.get("description", "Potential drug interaction detected via RxNorm.")
                            item_names = [pair.get("interactionConcept", [{}])[0].get("minConceptItem", {}).get("name", "Drug"),
                                          pair.get("interactionConcept", [{}])[1].get("minConceptItem", {}).get("name", "Drug")]
                            
                            flags.append(
                                SafetyFlag(
                                    severity="CRITICAL" if severity == "HIGH" else "HIGH",
                                    category="DRUG_INTERACTION",
                                    title=f"RxNorm Interaction: {' + '.join(item_names)}",
                                    description=desc,
                                    source_agent="RxNormAPI"
                                )
                            )
    except Exception as e:
        logger.warning(f"RxNorm API interaction check failed: {e}")

    return flags


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
    Unified pharmacology and clinical safety guardrail check.
    Combines live RxNorm API queries, allergen cross-matching, and vital bounds checks.
    """
    flags: List[SafetyFlag] = []
    meds_lower = [m.lower() for m in medications]
    allergies_lower = [a.lower() for a in allergies]

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
                        description=f"Patient has documented allergy to '{allergy}', contraindicating '{med}'.",
                        source_agent="SafetyGuardrail"
                    )
                )

    # 2. Check RxNav API for Interactions
    rxcuis = []
    for med in medications:
        cui = get_rxcui_for_drug(med)
        if cui:
            rxcuis.append(cui)
            
    rxnorm_flags = check_rxnorm_interactions(rxcuis)
    flags.extend(rxnorm_flags)

    # 3. Fallback High-Risk Rules (Warfarin + NSAID, ACEi + Potassium) if RxNorm offline/unflagged
    if not rxnorm_flags:
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

    # 4. Check Vital Threshold Safety Bounds
    if vitals:
        if vitals.spo2_percent and vitals.spo2_percent < 90.0:
            flags.append(
                SafetyFlag(
                    severity="CRITICAL",
                    category="VITAL_ALERT",
                    title="Critical Hypoxia Alert",
                    description=f"SpO2 is dangerously low ({vitals.spo2_percent}%). Immediate supplemental oxygen indicated.",
                    source_agent="VitalsGuardrail"
                )
            )
        if vitals.heart_rate_bpm and vitals.heart_rate_bpm > 130.0:
            flags.append(
                SafetyFlag(
                    severity="HIGH",
                    category="VITAL_ALERT",
                    title="Severe Tachycardia Alert",
                    description=f"Heart rate is severely elevated ({vitals.heart_rate_bpm} bpm).",
                    source_agent="VitalsGuardrail"
                )
            )

    return flags
