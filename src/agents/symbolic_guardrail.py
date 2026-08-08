import logging
from typing import Dict, Any, List
from src.core.state import ClinicalState, SymbolicOverrideFlag, AuditEntry
from src.core.symbolic_rules import evaluate_symbolic_rules

logger = logging.getLogger("PulseGraph.SymbolicGuardrailAgent")


def symbolic_guardrail_agent_node(state: ClinicalState) -> Dict[str, Any]:
    """
    Deterministic Symbolic Guardrail Node:
    Runs strict code-based clinical rule trees over patient vitals, medications,
    diagnostic differentials, and imaging findings to generate non-negotiable overrides.
    """
    logger.info("Running Symbolic Guardrail Node (Neuro-Symbolic Override Engine)...")
    
    overrides: List[SymbolicOverrideFlag] = evaluate_symbolic_rules(state)

    audit_entry = AuditEntry(
        agent_name="SymbolicGuardrailAgent",
        action="SYMBOLIC_RULE_AUDIT",
        summary=f"Evaluated deterministic decision tree rules. Generated {len(overrides)} symbolic override flags.",
        metadata={"symbolic_overrides_count": len(overrides)}
    )

    return {
        "symbolic_overrides": overrides,
        "audit_trail": [audit_entry],
        "current_step": "symbolic_guardrails_evaluated"
    }
