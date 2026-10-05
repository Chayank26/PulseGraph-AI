"""One model imaging review per session; no automatic study orders."""
from src.core.state import ClinicalFieldRequirement
from src.core.data_requests import create_data_request


def suggestion_request(suggestion):
    return create_data_request('imaging', 'Model imaging suggestion',
        f'Unvalidated model suggestion for {suggestion.candidate_name}: '
        f'{suggestion.modality}, {suggestion.anatomy}. '
        f'Question: {suggestion.assessment_question}. '
        f'Source references: {", ".join(suggestion.evidence_ids)}. '
        'References do not establish an imaging indication. Review explicitly; urgent care must not wait.',
        [ClinicalFieldRequirement(field_key='imaging_suggestion_action',
            label='Clinician decision on suggested study', data_type='enum', required=True,
            options=['reject', 'optional', 'required', 'uncertain']),
         ClinicalFieldRequirement(field_key='imaging_suggestion_reason',
            label='Reason for your decision', data_type='str', required=True)])
