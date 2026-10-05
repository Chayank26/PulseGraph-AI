"""Explicit session history reconciliation; empty lists are not negative history."""
import hashlib
import json
from src.core.state import ClinicalFieldRequirement, AuditEntry
from src.core.data_requests import create_data_request

STATUSES = ['recorded', 'none_confirmed', 'unknown', 'unavailable']


def history_fingerprint(demographics):
    return hashlib.sha256(json.dumps([demographics.current_medications, demographics.allergies]).encode()).hexdigest()


def reconciliation_request():
    fields = [ClinicalFieldRequirement(field_key='medication_review_'+name, label=label,
        data_type='enum', required=True, options=STATUSES) for name, label in
        [('medications', 'Current medication history'), ('allergies', 'Allergy history')]]
    optional = [ClinicalFieldRequirement(field_key='medication_review_'+name+'_list', label=label,
        data_type='str', required=False, description='Comma-separated entries; required only when status is recorded.')
        for name, label in [('medications', 'Reconciled medications'), ('allergies', 'Confirmed allergy entries')]]
    return create_data_request('safety', 'Medication reconciliation',
        'Confirm each history, explicitly confirm none, or mark unknown/unavailable. Missing information does not mean a negative history.',
        fields, optional_fields=optional)


def parse_reconciliation(data):
    allowed = {'medication_review_'+name+suffix for name in ('medications', 'allergies') for suffix in ('', '_list')}
    if set(data) - allowed:
        raise ValueError('Unexpected reconciliation fields.')
    result = {}
    for name in ('medications', 'allergies'):
        status = data.get('medication_review_'+name)
        raw = data.get('medication_review_'+name+'_list', '')
        if status not in STATUSES or not isinstance(raw, str) or len(raw) > 10000:
            raise ValueError('Invalid history status or list.')
        items = [item.strip() for item in raw.split(',') if item.strip()]
        if (status == 'recorded') != bool(items) or len(items) > 100:
            raise ValueError('Recorded history requires entries; other statuses must not include entries.')
        if any(item in ('__unknown__', '__unavailable__') for item in items):
            raise ValueError('Use the history status for unknown or unavailable entries.')
        result[name] = {'status': status, 'entries': items}
    return result


def apply_reconciliation(state, data):
    review = parse_reconciliation(data)
    demographics = state['demographics'].model_copy(deep=True)
    # Unknown/unavailable preserve previously recorded entries as unverified context.
    for name, attr in [('medications', 'current_medications'), ('allergies', 'allergies')]:
        if review[name]['status'] in ('recorded', 'none_confirmed'):
            setattr(demographics, attr, review[name]['entries'])
    review['input_fingerprint'] = history_fingerprint(demographics)
    return {'demographics': demographics, 'medication_reconciliation': review,
        'audit_trail': [AuditEntry(agent_name='SafetyAgent', action='MEDICATION_HISTORY_RECONCILED',
            summary='Clinician supplied explicit medication and allergy history states.', metadata={'history':review})]}
