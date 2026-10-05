"""Bounded differential generation with explicit abstention and failure outcomes."""
import hashlib
from src.core.state import AuditEntry
from src.core.diagnostic import build_diagnostic_context, input_fingerprint
from src.core.differential import prepare_context, validate_proposal, Proposal, PROMPT_VERSION, SYSTEM_PROMPT
from src.tools.differential_provider import configured_provider
from config.settings import settings


def diagnostic_agent_node(state):
    context = build_diagnostic_context(state)
    differentials = []
    generation = {'status': 'ABSTAINED', 'reason': 'provider_not_configured',
                  'prompt_version': PROMPT_VERSION, 'prompt_sha256': hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(), 'backend': settings.diagnostic_backend,
                  'model': settings.diagnostic_model or None}
    try:
        provider = configured_provider()
        if context.presentation.unrecognized_fragments or (context.presentation.routing and context.presentation.routing.requires_clinician_assessment):
            generation['reason'] = 'outside_scope'
        elif provider is not None:
            payload, corpus_hash = prepare_context(context)
            generation['corpus_sha256'] = corpus_hash
            if not payload['documents']:
                generation['reason'] = 'insufficient_evidence'
            elif not any(f['status'] == 'present' for f in payload['findings'].values()):
                generation['reason'] = 'insufficient_information'
            else:
                raw = provider.generate(payload, Proposal.model_json_schema())
                generation['response_sha256'] = hashlib.sha256(raw.encode()).hexdigest()
                differentials, reason = validate_proposal(raw, payload, settings.max_diagnostic_candidates)
                generation.update(status='PROPOSED' if differentials else 'ABSTAINED', reason=reason)
    except Exception:
        # Do not expose provider exceptions, raw output or possible patient data.
        generation.update(status='FAILED', reason='provider_or_output_validation_failed')
    presentation = context.presentation.model_dump(mode='json')
    fingerprint = input_fingerprint({**state, 'presentation': presentation})
    limitations = context.limitations + ['Model reference validation is not clinical entailment or calibrated diagnostic accuracy.']
    if not differentials:
        limitations.append('No automated differential is available. Clinician assessment is required: '+generation['reason'])
    presentation['diagnostic_review'] = {'status': 'CURRENT', 'input_fingerprint': fingerprint,
                                         'limitations': limitations, 'generation': generation}
    return {'diagnostic_fingerprint': fingerprint, 'presentation': presentation,
        'approved_by_clinician': False, 'differentials': differentials,
        'audit_trail': [AuditEntry(agent_name='DiagnosticAgent', action='DIFFERENTIAL_GENERATION',
            summary=f"Differential generation: {generation['status']}; {len(differentials)} proposals.",
            metadata={'differentials_count': len(differentials), 'generation': generation,
                      'diagnostic_context': context.model_dump(mode='json')})],
        'current_step': 'diagnostic_completed'}
