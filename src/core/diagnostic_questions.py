"""Bounded optional clarification of model-selected missing observations."""
from src.core.state import ClinicalFieldRequirement, VitalSigns
from src.core.data_requests import create_data_request

MAX_ROUNDS = 2
MAX_FIELDS = 3
LABELS = {'heart_rate_bpm':'Heart rate (bpm)', 'blood_pressure_sys':'Systolic blood pressure (mmHg)',
          'blood_pressure_dia':'Diastolic blood pressure (mmHg)', 'temperature_c':'Temperature (°C)',
          'respiratory_rate':'Respiratory rate (breaths/min)', 'spo2_percent':'Oxygen saturation (%)', 'bmi':'BMI (kg/m²)'}


def plan_questions(state, candidates):
    if any(r.requesting_agent == 'diagnostic' and r.status == 'PENDING' for r in state.get('pending_data_requests', [])):
        return None, 'awaiting_existing_clarification'
    rounds = state.get('diagnostic_followup_rounds', 0)
    answered = set()
    for request in state.get('resolved_data_requests', []):
        response = request.clinician_response or {}
        answered.update(key for key in response if key in VitalSigns.model_fields)
    if state.get('diagnostic_followup_disposition') == 'proceed_to_review':
        return None, 'clinician_directed_review'
    if rounds >= MAX_ROUNDS:
        return None, 'clarification_limit_reached'
    purposes = {}
    for candidate in candidates:
        for key in candidate.missing_information:
            if key in LABELS and key not in answered and getattr(state.get('vitals'),key,None) is None:
                purposes.setdefault(key, []).append(candidate.condition_name)
    if not purposes:
        return None, 'no_unanswered_supported_questions'
    fields = [ClinicalFieldRequirement(field_key=key, label=LABELS[key],data_type='float',required=False,
        allow_unavailable=True, description='Optional clarification selected for candidate review: '+', '.join(purposes[key])+
        '. Relevance is model-proposed, not independently established.') for key in sorted(purposes)[:MAX_FIELDS]]
    return create_data_request('diagnostic','Diagnostic clarification',
        'Provide each requested value, mark it unknown/unavailable, or continue to clinician review without further questions. No treatment should wait for this form.',
        [ClinicalFieldRequirement(field_key='diagnostic_followup_action',label='How should assessment continue?',data_type='enum',
            options=['provide_values','proceed_to_review'],required=True)], optional_fields=fields,priority='ROUTINE'), 'clarification_requested'
