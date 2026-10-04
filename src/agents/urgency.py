"""Pre-triage and post-acquisition urgency screening checkpoint."""
from config.settings import settings
from src.core.urgency import assess_urgency
from src.core.state import AuditEntry, ClinicalFieldRequirement
from src.core.data_requests import create_data_request


def urgency_agent_node(state):
    assessment = assess_urgency(state, settings.urgency_rules)
    result = {'urgency': assessment.model_dump(mode='json'), 'audit_trail': [AuditEntry(
        agent_name='UrgencyScreen', action='URGENCY_ASSESSMENT', summary=assessment.action,
        metadata=assessment.model_dump(mode='json'))]}
    if assessment.status == 'URGENT_REVIEW' and not assessment.acknowledged:
        request = create_data_request('urgency_check', 'Urgent clinician review',
            assessment.action + ' ' + ' '.join(r.explanation for r in assessment.reasons), [
                ClinicalFieldRequirement(field_key=f'urgency_review_{assessment.fingerprint}',
                    label='I have reviewed these findings and decided the assessment may continue',
                    data_type='bool', required=True,
                    description='Acknowledgement does not mark the findings resolved or the patient safe.')], priority='CRITICAL')
        result.update(pending_data_requests=[request], current_step='waiting_for_clinical_data')
    return result
