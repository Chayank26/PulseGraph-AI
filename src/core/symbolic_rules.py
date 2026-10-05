"""Legacy treatment overrides are disabled pending a sourced clinical specification.

This module deliberately performs no treatment inference. The independent limited
urgency screen remains active; an empty override list is not a safety assessment.
"""
from src.core.state import ClinicalState, SymbolicOverrideFlag

SYMBOLIC_RULE_REVIEW = {
    'version': 'symbolic-audit-v1',
    'status': 'UNAVAILABLE_PENDING_CLINICAL_REVIEW',
    'limitations': [
        'Legacy symbolic treatment overrides are disabled pending clinical review.',
        'No symbolic alerts does not establish safety; clinician assessment remains necessary.',
        'The separate urgency screen is limited and does not replace clinical assessment.',
    ],
    'rules': [
        {'rule_id': 'RULE_001_BRADYCARDIA_BETA_BLOCKER', 'status': 'DISABLED',
         'reason': 'Heart rate and medication-name matching alone do not support a blanket instruction to hold all beta blockers.'},
        {'rule_id': 'RULE_002_TENSION_PNEUMOTHORAX', 'status': 'DISABLED',
         'reason': 'A legacy simulated imaging label and confidence do not establish tension physiology or a procedure indication.'},
        {'rule_id': 'RULE_003_CONTRAST_NEPHROPATHY', 'status': 'DISABLED',
         'reason': 'Kidney-history and CT keywords do not establish contrast exposure, renal function, or a contraindication.'},
        {'rule_id': 'RULE_004_SEPTIC_SHOCK_SOFA', 'status': 'DISABLED',
         'reason': 'The legacy fever-based rule is neither qSOFA nor the Sepsis-3 septic-shock definition.',
         'source': 'https://jamanetwork.com/journals/jama/fullarticle/2492881'},
    ],
}


def evaluate_symbolic_rules(state: ClinicalState) -> list[SymbolicOverrideFlag]:
    """No approved executable symbolic treatment rules are currently available."""
    return []
