import logging
from uuid import uuid4
from src.core.routing import UNAVAILABLE
from src.core.clinical_parsing import parse_boolean, parse_enum_score, parse_number
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from src.core.state import (
    ClinicalState,
    VitalSigns,
    PatientDemographics,
    ClinicalDataRequest,
    ClinicalFieldRequirement,
    AuditEntry
)


logger = logging.getLogger("PulseGraph.DataRequests")


def create_data_request(
    requesting_agent: str,
    pathway_name: str,
    reason: str,
    required_fields: List[ClinicalFieldRequirement],
    optional_fields: Optional[List[ClinicalFieldRequirement]] = None,
    priority: str = "HIGH"
) -> ClinicalDataRequest:
    """
    Creates a structured ClinicalDataRequest object to ask for missing patient information.
    """
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    clean_agent = requesting_agent.upper().replace("_AGENT", "").replace("_NODE", "")
    request_id = f"REQ-{clean_agent}-{timestamp_str}-{uuid4().hex[:8]}"

    request = ClinicalDataRequest(
        request_id=request_id,
        requesting_agent=requesting_agent,
        pathway_name=pathway_name,
        reason=reason,
        priority=priority,
        required_fields=required_fields,
        optional_fields=optional_fields or [],
        status="PENDING",
        created_at=datetime.now(timezone.utc)
    )
    logger.info(f"Created ClinicalDataRequest [{request_id}] for agent '{requesting_agent}' (Pathway: {pathway_name})")
    return request


def get_pending_requests(state: ClinicalState) -> List[ClinicalDataRequest]:
    """Retrieve all pending data requests from clinical state."""
    all_requests = state.get("pending_data_requests", [])
    return [r for r in all_requests if r.status == "PENDING"]


def validate_response(
    request: ClinicalDataRequest,
    response_data: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Validates a clinician's response dictionary against the request's required_fields.
    Returns (is_valid, list_of_error_messages).
    """
    errors: List[str] = []
    if not response_data:
        return False, ["Response data cannot be empty."]

    if request.requesting_agent != "imaging" and any(k.startswith("imaging_") for k in response_data):
        return False, ["Imaging decisions must use the imaging review request."]
    if request.requesting_agent == "imaging":
        allowed = {f.field_key for f in request.required_fields + request.optional_fields}
        if set(response_data) - allowed:
            return False, ["Unexpected fields in imaging response."]
        try:
            if request.pathway_name == 'Model imaging suggestion':
                value = response_data.get('imaging_suggestion_reason')
                if not isinstance(value, str) or not value.strip() or len(value) > 2000 or value.strip() in ('__unknown__', '__unavailable__'):
                    return False, ['A written clinician reason is required.']
            elif request.pathway_name == "Imaging decision":
                from src.core.imaging import decision_from_response
                decision_from_response(response_data)
            elif request.pathway_name == 'Imaging assessment question':
                value = response_data.get('imaging_assessment_question')
                if not isinstance(value, str) or not value.strip() or len(value) > 2000 or value == '__unknown__':
                    return False, ['A written assessment question is required.']
            elif request.pathway_name == "Required imaging report":
                action = response_data.get("imaging_action")
                key = "imaging_report" if action == "submit_report" else "imaging_override_reason"
                value = response_data.get(key)
                if not isinstance(value, str) or not value.strip() or len(value) > 20000:
                    return False, ["Supply a report or an explicit reason for the selected action."]
                if action != "submit_report" and value == UNAVAILABLE:
                    return False, ["An override or handoff requires a written reason."]
        except ValueError as exc:
            return False, [str(exc)]

    if request.requesting_agent == 'diagnostic':
        allowed = {f.field_key for f in request.required_fields + request.optional_fields}
        if set(response_data) - allowed:
            return False, ['Unexpected diagnostic response fields.']
        action = response_data.get('diagnostic_followup_action')
        if action == 'proceed_to_review':
            if any(v not in (None, '') for k, v in response_data.items() if k != 'diagnostic_followup_action'):
                return False, ['Continuing without clarification cannot also submit measurements.']
        elif action == 'provide_values':
            for field in request.optional_fields:
                value = response_data.get(field.field_key)
                if value in ('__unknown__', '__unavailable__'):
                    continue
                number = parse_number(value)
                if number is None:
                    return False, ['Provide every requested observation or mark it unknown/unavailable.']
                try:
                    VitalSigns(**{field.field_key: number})
                except ValueError:
                    return False, ['Invalid diagnostic observation.']
        else:
            return False, ['Select how diagnostic assessment should continue.']
    elif any(key.startswith('diagnostic_followup_') for key in response_data):
        return False, ['Diagnostic controls require a diagnostic clarification request.']

    for req_field in request.required_fields:
        val = response_data.get(req_field.field_key)
        if val == UNAVAILABLE and req_field.allow_unavailable:
            continue
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"Missing required field '{req_field.label}' ({req_field.field_key}).")
        else:
            key = req_field.field_key
            if key.startswith("urgency_review_"):
                if val is not True:
                    errors.append("Urgent review must be explicitly acknowledged by the clinician before continuing.")
            elif key in ("history_score", "ecg_score", "troponin_score"):
                if parse_enum_score(val) is None:
                    errors.append(f"Invalid {req_field.label}: value must be 0, 1, or 2.")
            elif req_field.data_type == "enum":
                if val not in (req_field.options or []):
                    errors.append(f"Invalid choice for {req_field.label}.")
            elif req_field.data_type in ("int", "float"):
                number = parse_number(val)
                if number is None or (req_field.data_type == "int" and not number.is_integer()):
                    errors.append(f"Invalid {req_field.label}: a finite {req_field.data_type} is required.")
                elif key == "age" and not 0 <= number <= 130:
                    errors.append("Age must be an integer between 0 and 130.")
                elif number < 0:
                    errors.append(f"Invalid {req_field.label}: value must be non-negative.")
                elif key == "spo2_percent" and number > 100:
                    errors.append("Oxygen saturation must be between 0 and 100.")
            elif req_field.data_type == "bool" and parse_boolean(val) is None:
                errors.append(f"Invalid boolean value for field '{req_field.label}'.")

    return len(errors) == 0, errors





def resolve_request(
    request: ClinicalDataRequest,
    response_data: Dict[str, Any]
) -> ClinicalDataRequest:
    """
    Marks a request as RESOLVED and attaches the clinician response.
    Raises ValueError if response_data is incomplete or invalid.
    """
    is_valid, errors = validate_response(request, response_data)
    if not is_valid:
        raise ValueError(f"Cannot resolve ClinicalDataRequest [{request.request_id}]: {'; '.join(errors)}")
    request.status = "RESOLVED"
    request.resolved_at = datetime.now(timezone.utc)
    request.clinician_response = response_data
    logger.info(f"ClinicalDataRequest [{request.request_id}] resolved successfully.")
    return request



def has_resolved_request_for_pathway(
    state: ClinicalState,
    requesting_agent: str,
    pathway_name: str
) -> bool:
    """
    Checks if a request for a specific clinical pathway was already resolved or processed.
    Used by agents to avoid duplicate data requests.
    """
    resolved = state.get("resolved_data_requests", [])
    for r in resolved:
        if r.requesting_agent == requesting_agent and r.pathway_name == pathway_name:
            return True
    return False


def apply_response_to_state(
    state: ClinicalState,
    response_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Applies validated clinician responses to state vitals, demographics, and clinical notes.
    """
    imaging_updates = {}
    if 'diagnostic_followup_action' in response_data:
        imaging_updates['diagnostic_followup_disposition'] = response_data['diagnostic_followup_action']
        imaging_updates['diagnostic_followup_answers'] = {**(state.get('diagnostic_followup_answers') or {}),
            **{k:v for k,v in response_data.items() if k in VitalSigns.model_fields and v not in (None, '')}}
        response_data = {k:v for k,v in response_data.items() if k != 'diagnostic_followup_action'}
        # Preserve unknown separately in resolved requests; do not coerce to a measurement.
        response_data = {k:v for k,v in response_data.items() if v != '__unknown__' and v not in (None, '')}

    if 'imaging_suggestion_action' in response_data:
        from src.core.imaging import ImagingDecision
        proposal = state.get('imaging_model_suggestion')
        if not proposal:
            raise ValueError('No imaging suggestion is available for review.')
        action = response_data['imaging_suggestion_action']
        imaging_updates['imaging_suggestion_reviewed'] = True
        if action != 'reject':
            imaging_updates['imaging_decision'] = ImagingDecision(
                decision=action, reason=response_data['imaging_suggestion_reason'],
                modality=proposal['modality'], anatomy=proposal['anatomy'],
                assessment_question=proposal['assessment_question']).model_dump()
            imaging_updates['imaging_response'] = None
            imaging_updates['imaging_assessment_fingerprint'] = None
    elif "imaging_decision" in response_data:
        from src.core.imaging import decision_from_response
        imaging_updates["imaging_decision"] = decision_from_response(response_data).model_dump()
        imaging_updates['imaging_response'] = None
        imaging_updates['imaging_assessment_fingerprint'] = None
    elif 'imaging_assessment_question' in response_data:
        from src.core.imaging import ImagingDecision
        decision = dict(state.get('imaging_decision') or {})
        question = response_data['imaging_assessment_question']
        if question == '__unavailable__':
            decision.update(decision='uncertain', assessment_question=None, report=None, reason='Assessment question unavailable; clinician assessment required.')
        else:
            decision['assessment_question'] = question
        imaging_updates['imaging_decision'] = ImagingDecision.model_validate(decision).model_dump()
    elif "imaging_action" in response_data:
        imaging_updates["imaging_response"] = dict(response_data)
    # Keep reports and decisions structured; do not feed them to keyword diagnosis.
    response_data = {k: v for k, v in response_data.items() if not k.startswith("imaging_")}
    # Unavailable is an explicit answer, not a numeric measurement.
    unavailable = {k: v for k, v in response_data.items() if v == UNAVAILABLE}
    response_data = {k: v for k, v in response_data.items() if v != UNAVAILABLE}
    vitals = state.get("vitals")
    notes_to_add = [f"[ACQUIRED CLINICAL DATA]: {k} = {v}" for k, v in unavailable.items()]

    vital_keys = set(VitalSigns.model_fields)
    supplied_vitals = {key: value for key, value in response_data.items()
                       if key in vital_keys and value is not None}
    if supplied_vitals:
        existing = vitals.model_dump() if vitals else {}
        vitals = VitalSigns(**{**existing, **supplied_vitals})

    # Append structured clinical observations to raw_notes for downstream context
    for key, val in response_data.items():
        if key not in ["heart_rate_bpm", "blood_pressure_sys", "blood_pressure_dia", "spo2_percent", "respiratory_rate"]:
            notes_to_add.append(f"[ACQUIRED CLINICAL DATA]: {key} = {val}")

    updates: Dict[str, Any] = dict(imaging_updates)
    context = dict(state.get('urgency_context') or {})
    confusion_changed = 'confusion' in response_data and parse_boolean(response_data['confusion']) != context.get('new_confusion')
    if supplied_vitals or confusion_changed:
        updates['urgency_observation_revision'] = state.get('urgency_observation_revision', 0) + 1
    if 'confusion' in response_data:
        context = dict(state.get('urgency_context') or {})
        context['new_confusion'] = parse_boolean(response_data['confusion'])
        updates['urgency_context'] = context
    demographics = state.get("demographics")



    # Map demographics (e.g. age) if provided in response
    if "age" in response_data and response_data["age"] is not None:
        try:
            age_val = int(response_data["age"])
            if 0 <= age_val <= 130:
                if demographics:
                    demographics.age = age_val
                else:
                    demographics = PatientDemographics(
                        patient_id=state.get("patient_id", "PAT-UNKNOWN"),
                        age=age_val,
                        gender="Unknown"
                    )
                updates["demographics"] = demographics
        except (ValueError, TypeError):
            pass

    if vitals:
        updates["vitals"] = vitals
    if notes_to_add:
        updates["raw_notes"] = notes_to_add


    audit_entry = AuditEntry(
        agent_name="DataRequestReviewNode",
        action="CLINICAL_DATA_ACQUISITION",
        summary=f"Acquired missing clinical parameters ({len(response_data)} items).",
        metadata={"response_keys": list(response_data.keys())}
    )
    updates["audit_trail"] = [audit_entry]

    return updates

