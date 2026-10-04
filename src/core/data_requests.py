import logging
from uuid import uuid4
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

    for req_field in request.required_fields:
        val = response_data.get(req_field.field_key)
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
    vitals = state.get("vitals")
    notes_to_add = []

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

    updates: Dict[str, Any] = {}
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

