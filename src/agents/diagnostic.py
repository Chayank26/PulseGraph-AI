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
    from src.core.diagnostic_questions import plan_questions
    request, clarification_status = plan_questions(state, differentials)
    generation['clarification_status'] = clarification_status
    presentation = context.presentation.model_dump(mode='json')
    fingerprint = input_fingerprint({**state, 'presentation': presentation})
    limitations = context.limitations + ['Model reference validation is not clinical entailment or calibrated diagnostic accuracy.']
    if request:
        limitations.append('Optional diagnostic clarification is pending; these candidates are provisional.')
    elif clarification_status in ('clinician_directed_review', 'clarification_limit_reached'):
        limitations.append('Further clarification stopped: '+clarification_status+'. Remaining missing information requires clinician review.')
    if not differentials:
        limitations.append('No automated differential is available. Clinician assessment is required: '+generation['reason'])
    presentation['diagnostic_review'] = {'status': 'CURRENT', 'input_fingerprint': fingerprint,
                                         'limitations': limitations, 'generation': generation}
    result = {'diagnostic_fingerprint': fingerprint, 'presentation': presentation,
        'approved_by_clinician': False, 'differentials': differentials,
        'audit_trail': [AuditEntry(agent_name='DiagnosticAgent', action='DIFFERENTIAL_GENERATION',
            summary=f"Differential generation: {generation['status']}; {len(differentials)} proposals.",
            metadata={'differentials_count': len(differentials), 'generation': generation,
                      'diagnostic_context': context.model_dump(mode='json')})],
        'current_step': 'diagnostic_completed'}

    if request:
        result.update(pending_data_requests=[request], current_step='waiting_for_clinical_data',
                      diagnostic_followup_rounds=state.get('diagnostic_followup_rounds', 0) + 1)
        result['audit_trail'].append(AuditEntry(agent_name='DiagnosticAgent', action='DIAGNOSTIC_CLARIFICATION_REQUESTED',
            summary=request.reason, metadata={'request_id':request.request_id,
                'round':result['diagnostic_followup_rounds'], 'fields':[f.model_dump() for f in request.optional_fields]}))
    return result
