"""Expose symbolic-rule availability without claiming a completed safety check."""
from copy import deepcopy
from src.core.state import ClinicalState, AuditEntry
from src.core.symbolic_rules import evaluate_symbolic_rules, SYMBOLIC_RULE_REVIEW


def symbolic_guardrail_agent_node(state: ClinicalState):
    review = deepcopy(SYMBOLIC_RULE_REVIEW)
    presentation = dict(state.get('presentation') or {})
    presentation['symbolic_review'] = review
    return {
        'symbolic_overrides': evaluate_symbolic_rules(state),
        'presentation': presentation,
        'audit_trail': [AuditEntry(agent_name='SymbolicGuardrailAgent',
            action='SYMBOLIC_RULES_UNAVAILABLE',
            summary='Four legacy treatment overrides disabled pending clinical review; no symbolic safety assessment performed.',
            metadata=review)],
        'current_step': 'symbolic_guardrails_evaluated',
    }
