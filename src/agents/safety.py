import logging
from typing import Dict, Any, List
from src.core.state import ClinicalState, SafetyFlag, AuditEntry, ClinicalFieldRequirement
from src.core.data_requests import create_data_request
from src.tools.pharmacology import check_drug_safety_profile, medication_coverage

logger = logging.getLogger("PulseGraph.SafetyAgent")


def safety_agent_node(state: ClinicalState) -> Dict[str, Any]:
    """Run limited local alerts and expose unavailable medication coverage."""
    notes = state.get("raw_notes", [])
    combined_notes = " ".join(notes).lower()
    
    demographics = state.get("demographics")
    medications = demographics.current_medications if demographics else []
    allergies = demographics.allergies if demographics else []
    vitals = state.get("vitals")

    from src.core.medication_review import history_fingerprint, reconciliation_request
    from src.tools.medication_provider import configured_provider, assess_interactions
    reconciliation = state.get('medication_reconciliation')
    current = bool(reconciliation and demographics and reconciliation.get('input_fingerprint') == history_fingerprint(demographics))
    needs_history = bool(medications or allergies or 'meds_unrecorded' in combined_notes or 'medications_missing' in combined_notes)
    if needs_history and not current:
        req = reconciliation_request()
        return {'pending_data_requests': [req], 'current_step': 'safety_data_requested',
            'audit_trail': [AuditEntry(agent_name='SafetyAgent', action='DATA_REQUEST_CREATED',
                summary='Explicit medication and allergy reconciliation requested.', metadata={'request_id':req.request_id})]}

    # Limited local checks; coverage is independent of the number of flags.
    safety_flags: List[SafetyFlag] = check_drug_safety_profile(
        medications=medications,
        allergies=allergies,
        vitals=vitals
    )

    coverage = medication_coverage(medications, allergies)
    if current:
        coverage['medication_history'] = reconciliation['medications']['status'].upper()
        coverage['allergy_history'] = reconciliation['allergies']['status'].upper()
    if current and any(reconciliation[name]['status'] in ('unknown', 'unavailable') for name in ('medications', 'allergies')):
        coverage['limitations'].append('History remains incomplete; checks use previously recorded entries, if any, without confirming completeness.')
    interaction = assess_interactions(medications, configured_provider())
    coverage['interaction_provider'] = interaction['status']
    coverage['provider_assessment'] = interaction['result']
    coverage['limitations'][0] = ('No replacement interaction provider is configured.' if interaction['status'] == 'NOT_CONFIGURED'
        else 'Provider coverage is limited to its reported scope. Failure or missing pairs do not establish safety.')
    if interaction['result']:
        for pair in interaction['result']['pairs']:
            if pair['status'] == 'alert':
                safety_flags.append(SafetyFlag(severity=pair['severity'], category='DRUG_INTERACTION',
                    title='Provider-reported interaction requires review', description=pair['description'],
                    source_agent=interaction['result']['provider']))
    presentation = dict(state.get('presentation') or {})
    presentation['safety_review'] = coverage
    audit_entry = AuditEntry(
        agent_name="SafetyAgent",
        action="SAFETY_GUARDRAIL_AUDIT",
        summary=f"Limited local medication checks ran. Identified {len(safety_flags)} clinical flags.",
        metadata={"flags_count": len(safety_flags), "coverage": coverage}
    )

    return {
        "safety_flags": safety_flags,
        "presentation": presentation,
        "audit_trail": [audit_entry],
        "current_step": "safety_audited"
    }

