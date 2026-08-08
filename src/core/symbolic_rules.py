import logging
from typing import List
from src.core.state import ClinicalState, SymbolicOverrideFlag

logger = logging.getLogger("PulseGraph.SymbolicRules")


def evaluate_symbolic_rules(state: ClinicalState) -> List[SymbolicOverrideFlag]:
    """
    Deterministic Neuro-Symbolic Decision Engine:
    Evaluates hardcoded, non-negotiable clinical decision tree rules against patient vitals,
    medications, diagnostic differentials, and multimodal imaging findings.
    
    These symbolic overrides bypass/supersede probabilistic LLM recommendations.
    """
    overrides: List[SymbolicOverrideFlag] = []
    
    demographics = state.get("demographics")
    vitals = state.get("vitals")
    meds = [m.lower() for m in (demographics.current_medications if demographics else [])]
    differentials = state.get("differentials", [])
    imaging = state.get("imaging_data")

    # RULE 1: Severe Bradycardia + Beta-Blocker Contraindication
    if vitals and vitals.heart_rate_bpm and vitals.heart_rate_bpm < 50.0:
        beta_blockers = ["metoprolol", "atenolol", "propranolol", "bisoprolol", "carvedilol", "labetalol"]
        has_bb = any(any(bb in m for bb in beta_blockers) for m in meds)
        if has_bb:
            overrides.append(
                SymbolicOverrideFlag(
                    rule_id="RULE_001_BRADYCARDIA_BETA_BLOCKER",
                    severity="CRITICAL_OVERRIDE",
                    message="HARD CONTRAINDICATION: Patient has severe bradycardia (HR < 50 bpm) while taking Beta-Blocker therapy.",
                    deterministic_rule="IF HR < 50 THEN CONTRAINDICATE BetaBlocker",
                    action_required="HOLD all Beta-Blocker doses immediately and obtain STAT ECG."
                )
            )

    # RULE 2: Critical Tension Pneumothorax Imaging Escalation
    if imaging and imaging.findings:
        for finding in imaging.findings:
            if finding.finding_name.lower() == "pneumothorax" and finding.confidence >= 0.85:
                overrides.append(
                    SymbolicOverrideFlag(
                        rule_id="RULE_002_TENSION_PNEUMOTHORAX",
                        severity="CRITICAL_OVERRIDE",
                        message="EMERGENCY ALERT: Radiographic evidence of Pneumothorax detected on Chest X-Ray.",
                        deterministic_rule="IF Imaging.Pneumothorax == TRUE THEN STAT Chest Tube Decompression",
                        action_required="Notify attending physician STAT for emergency needle decompression / chest tube placement."
                    )
                )

    # RULE 3: Renal Failure / CIN Risk with IV Contrast Workup
    if vitals and vitals.blood_pressure_sys:
        # Check if recommended workup includes IV Contrast CT while patient has severe renal impairment risk
        for diff in differentials:
            for workup in diff.recommended_workup:
                if "ct" in workup.lower() or "angiogram" in workup.lower():
                    # Check BUN or known chronic renal conditions
                    if demographics and any("kidney" in c.lower() or "renal" in c.lower() for c in demographics.chronic_conditions):
                        overrides.append(
                            SymbolicOverrideFlag(
                                rule_id="RULE_003_CONTRAST_NEPHROPATHY",
                                severity="HARD_CONTRAINDICATION",
                                message="NEPHROTOXICITY ALERT: Recommended CT Angiography carries high risk of Contrast-Induced Nephropathy.",
                                deterministic_rule="IF RenalImpairment == TRUE AND Workup == ContrastCT THEN Require Hydration/Pre-med",
                                action_required="Verify eGFR/Creatinine prior to IV contrast administration; consider non-contrast V/Q scan or MRI."
                            )
                        )

    # RULE 4: Sepsis / Septic Shock Emergency Escalation
    if vitals and vitals.blood_pressure_sys and vitals.respiratory_rate and vitals.temperature_c:
        if vitals.blood_pressure_sys < 90.0 and vitals.respiratory_rate >= 22.0 and vitals.temperature_c > 38.0:
            overrides.append(
                SymbolicOverrideFlag(
                    rule_id="RULE_004_SEPTIC_SHOCK_SOFA",
                    severity="CRITICAL_OVERRIDE",
                    message="SEPSIS ALERT: Patient meets qSOFA criteria for Septic Shock (Hypotension + Tachypnea + Hyperthermia).",
                    deterministic_rule="IF SBP < 90 AND RR >= 22 AND Temp > 38.0 THEN STAT Sepsis 3 Bundle",
                    action_required="Initiate 1-hour Sepsis Bundle: IV fluid resuscitation (30mL/kg), blood cultures, and broad-spectrum IV antibiotics."
                )
            )

    logger.info(f"Symbolic decision engine evaluated rules. Generated {len(overrides)} deterministic overrides.")
    return overrides
