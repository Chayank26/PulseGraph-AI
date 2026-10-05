"""Bounded legacy candidates using assertion-aware findings, pending clinical audit."""
from typing import Dict, Any
from src.core.state import ClinicalState, DiagnosticDifferential, AuditEntry
from src.core.diagnostic import build_diagnostic_context, input_fingerprint


def diagnostic_agent_node(state: ClinicalState) -> Dict[str, Any]:
    context = build_diagnostic_context(state)
    differentials = []
    # Retain only the existing symptom-driven candidates. History, calculator
    # values and unparsed reports cannot establish a diagnosis or probability.
    candidates = {
        'chest_pain': 'Acute Coronary Syndrome / NSTEMI',
        'breathlessness': 'Pulmonary Embolism',
    }
    for symptom in context.presentation.symptoms:
        if symptom.status != 'present' or symptom.symptom not in candidates:
            continue
        evidence = [f'{m.source_id}[{m.start}:{m.end}]: {m.quote}'
                    for m in symptom.mentions if m.status == 'present']
        if not evidence:
            continue
        differentials.append(DiagnosticDifferential(
            condition_name=candidates[symptom.symptom], likelihood='Not estimated',
            rationale='Legacy symptom-based candidate for clinician review only. '
                      'The recorded symptom does not establish this diagnosis. '
                      'No imaging findings or diagnostic probabilities have been inferred.',
            supporting_evidence=evidence, recommended_workup=[]))
    presentation = context.presentation.model_dump(mode='json')
    fingerprint = input_fingerprint({**state, 'presentation': presentation})
    presentation['diagnostic_review'] = {'status': 'CURRENT', 'input_fingerprint': fingerprint,
                                         'limitations': context.limitations}
    return {
        'diagnostic_fingerprint': fingerprint,
        'presentation': presentation,
        'approved_by_clinician': False,
        'differentials': differentials,
        'audit_trail': [AuditEntry(agent_name='DiagnosticAgent', action='DIFFERENTIAL_GENERATION',
            summary=f'Generated {len(differentials)} unvalidated candidates from current positive findings.',
            metadata={'differentials_count': len(differentials),
                      'diagnostic_context': context.model_dump(mode='json')})],
        'current_step': 'diagnostic_completed',
    }
