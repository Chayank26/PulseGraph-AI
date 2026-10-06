"""Bounded clinician assessment record, not an autonomous red-flag detector."""
import hashlib
import json
from src.core.data_requests import create_data_request
from src.core.state import ClinicalFieldRequirement

SOURCE = 'https://www.nice.org.uk/guidance/ng59/chapter/recommendations'
VERSION = 'low-back-assessment-v1'
OPTIONS = {
    'back_review_scope': ['confirmed', 'outside_scope', 'unknown'],
    'back_review_serious_cause': ['not_suspected', 'suspected', 'unknown'],
}


def fingerprint(state):
    # Include narrative and observations; never reuse assessment after changed inputs.
    demographics = state.get('demographics')
    vitals = state.get('vitals')
    return hashlib.sha256(json.dumps({'demographics':demographics.model_dump(mode='json') if demographics else None,
        'notes':state.get('raw_notes', []), 'vitals':vitals.model_dump() if vitals else None,
        'urgency':state.get('urgency_context'), 'version':VERSION}, sort_keys=True).encode()).hexdigest()


def validate_answer(data):
    if set(data) != set(OPTIONS):
        raise ValueError('Answer both low-back assessment fields, with no extra fields.')
    for key, options in OPTIONS.items():
        if data[key] not in options + ['__unavailable__']:
            raise ValueError('Invalid low-back assessment choice.')


def assess(state):
    review = state.get('back_pain_review')
    if not review or review.get('input_fingerprint') != fingerprint(state):
        request = create_data_request('triage', 'Low-back clinical assessment',
            'Clinician assessment is required. These answers do not rule out serious disease; urgent concerns must not wait for this form.',
            [ClinicalFieldRequirement(field_key='back_review_scope', label='Confirm pathway scope',
                data_type='enum', options=OPTIONS['back_review_scope'], required=True, allow_unavailable=True,
                description='Confirm age 18 or older, non-pregnant, low-back presentation assessed by a clinician. Other back locations or unassessed eligibility are outside this prototype pathway.'),
             ClinicalFieldRequirement(field_key='back_review_serious_cause', label='Assessment of possible specific or serious cause',
                data_type='enum', options=OPTIONS['back_review_serious_cause'], required=True, allow_unavailable=True,
                description='After history and examination, has the clinician identified suspicion of a specific/serious cause? Consider cancer, infection, trauma, inflammatory disease and serious neurological pathology. This is not an exhaustive red-flag checklist.')])
        return request, None
    complete = review['back_review_scope'] == 'confirmed' and review['back_review_serious_cause'] == 'not_suspected'
    return None, {'status':'CLINICIAN_ASSESSED' if complete else 'REQUIRES_CLINICIAN_ASSESSMENT',
        'rule_version':VERSION, 'source':SOURCE, 'answers':{k:review[k] for k in OPTIONS},
        'limitations':['This records clinician judgment; it does not exclude serious disease or establish low risk.',
            'No diagnosis, treatment recommendation or automatic imaging decision is generated.'],
        'input_fingerprint':review['input_fingerprint']}
