import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from src.core.state import (
    ClinicalState,
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
    request_id = f"REQ-{clean_agent}-{timestamp_str}"

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
            if req_field.field_key == "age":
                try:
                    age_val = int(val)
                    if age_val < 0 or age_val > 130:
                        errors.append(f"Invalid age '{val}'. Age must be an integer between 0 and 130.")
                except (ValueError, TypeError):
                    errors.append(f"Invalid age '{val}'. Age must be a valid integer between 0 and 130.")
            elif req_field.field_key in ["history_score", "ecg_score", "troponin_score"]:
                try:
                    num_val = int(str(val)[0]) if isinstance(val, str) else int(val)
                    if num_val not in [0, 1, 2]:
                        errors.append(f"Invalid {req_field.label} '{val}'. Value must be 0, 1, or 2.")
                except (ValueError, TypeError, IndexError):
                    errors.append(f"Invalid {req_field.label} '{val}'. Must be 0, 1, or 2.")
            elif req_field.field_key == "cardiac_risk_factors_count":
                try:
                    rf_val = int(val)
                    if rf_val < 0:
                        errors.append(f"Invalid risk factor count '{val}'. Value must be a non-negative integer.")
                except (ValueError, TypeError):
                    errors.append(f"Invalid risk factor count '{val}'. Must be a non-negative integer.")
            elif req_field.data_type == "bool":
                if isinstance(val, str):
                    if val.lower() not in ["true", "false"]:
                        errors.append(f"Invalid boolean value '{val}' for field '{req_field.label}'. Must be True or False.")
                elif not isinstance(val, bool):
                    errors.append(f"Invalid boolean value '{val}' for field '{req_field.label}'. Must be True or False.")

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

    # Map vital signs if provided in response
    if vitals:
        if "heart_rate_bpm" in response_data and response_data["heart_rate_bpm"] is not None:
            vitals.heart_rate_bpm = float(response_data["heart_rate_bpm"])
        if "blood_pressure_sys" in response_data and response_data["blood_pressure_sys"] is not None:
            vitals.blood_pressure_sys = float(response_data["blood_pressure_sys"])
        if "blood_pressure_dia" in response_data and response_data["blood_pressure_dia"] is not None:
            vitals.blood_pressure_dia = float(response_data["blood_pressure_dia"])
        if "spo2_percent" in response_data and response_data["spo2_percent"] is not None:
            vitals.spo2_percent = float(response_data["spo2_percent"])
        if "respiratory_rate" in response_data and response_data["respiratory_rate"] is not None:
            vitals.respiratory_rate = float(response_data["respiratory_rate"])

    # Append structured clinical observations to raw_notes for downstream context
    for key, val in response_data.items():
        if key not in ["heart_rate_bpm", "blood_pressure_sys", "blood_pressure_dia", "spo2_percent", "respiratory_rate"]:
            notes_to_add.append(f"[ACQUIRED CLINICAL DATA]: {key} = {val}")

    updates: Dict[str, Any] = {}
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

