import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from src.core.state import (
    ClinicalState,
    PatientDemographics,
    VitalSigns,
    ClinicianIdentity
)
from src.core.graph import build_clinical_graph
from src.core.data_requests import (
    resolve_request as core_resolve_request,
    apply_response_to_state,
    validate_response
)
from src.db.models import ClinicalSessionModel, PatientModel, DoctorModel
from src.db.repositories.session_repository import SessionRepository
from src.db.repositories.patient_repository import PatientRepository
from src.db.repositories.doctor_repository import DoctorRepository

logger = logging.getLogger("PulseGraph.ClinicalWorkflowService")


def _to_json_serializable(obj: Any) -> Any:
    """Helper to recursively convert Pydantic models and datetimes to JSON dicts."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, list):
        return [_to_json_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _to_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


class ClinicalWorkflowService:
    def __init__(self, db: Session, checkpointer: Optional[Any] = None):
        self.db = db
        self.sess_repo = SessionRepository(db)
        self.patient_repo = PatientRepository(db)
        self.doctor_repo = DoctorRepository(db)
        self.graph = build_clinical_graph(checkpointer=checkpointer)

    def _sync_audit_and_results(self, session: ClinicalSessionModel, state_values: Dict[str, Any]) -> None:
        """Persists audit logs and CDS recommendations from state snapshot into PostgreSQL."""
        # 1. Sync Audit Trail
        audit_trail = state_values.get("audit_trail", [])
        for entry in audit_trail:
            entry_dict = _to_json_serializable(entry)
            self.sess_repo.add_audit_log(
                session_id=session.session_id,
                agent_name=entry_dict.get("agent_name", "WorkflowSystem"),
                action=entry_dict.get("action", "STATE_UPDATE"),
                summary=entry_dict.get("summary", ""),
                metadata_json=entry_dict.get("metadata", {})
            )

        # 2. Sync Pending Data Requests
        pending_reqs = state_values.get("pending_data_requests", [])
        for req in pending_reqs:
            req_dict = _to_json_serializable(req)
            self.sess_repo.create_data_request(
                session_id=session.session_id,
                request_id=req_dict["request_id"],
                requesting_agent=req_dict["requesting_agent"],
                pathway_name=req_dict["pathway_name"],
                reason=req_dict["reason"],
                required_fields=req_dict["required_fields"],
                optional_fields=req_dict.get("optional_fields", []),
                priority=req_dict.get("priority", "HIGH")
            )

        # 3. Sync CDS Recommendations
        self.sess_repo.save_cds_result(
            session_id=session.session_id,
            risk_scores=_to_json_serializable(state_values.get("risk_scores", [])),
            differentials=_to_json_serializable(state_values.get("differentials", [])),
            imaging_findings=_to_json_serializable(state_values.get("imaging_data").findings if state_values.get("imaging_data") else []),
            evidence=_to_json_serializable(state_values.get("evidence", [])),
            safety_flags=_to_json_serializable(state_values.get("safety_flags", [])),
            symbolic_overrides=_to_json_serializable(state_values.get("symbolic_overrides", [])),
            final_status=session.status,
            clinician_approval={"approved": state_values.get("approved_by_clinician"), "notes": state_values.get("clinician_notes")}
        )

    def run_session(
        self,
        session_id: str,
        raw_notes: Optional[List[str]] = None,
        vitals_payload: Optional[Dict[str, Any]] = None,
        image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes or continues the LangGraph workflow for a given session.
        Handles automated node steps up to interrupts (data_request_review or human_review).
        """
        session = self.sess_repo.get_by_session_id(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        patient_model = self.patient_repo.get_by_patient_id(session.patient_id)
        doctor_model = self.doctor_repo.get_by_doctor_id(session.doctor_id)

        demographics = PatientDemographics(
            patient_id=patient_model.patient_id,
            age=patient_model.age,
            gender=patient_model.gender,
            blood_type=patient_model.blood_type,
            allergies=patient_model.allergies or [],
            chronic_conditions=patient_model.chronic_conditions or [],
            current_medications=patient_model.current_medications or []
        )

        vitals = VitalSigns(**vitals_payload) if vitals_payload else None

        notes_list = raw_notes or []
        if image_path:
            notes_list.append(f"cxr_path={image_path}")

        clinician_identity = ClinicianIdentity(
            doctor_id=doctor_model.doctor_id,
            full_name=doctor_model.full_name,
            department=doctor_model.department,
            role=doctor_model.role
        )

        initial_state: ClinicalState = {
            "patient_id": patient_model.patient_id,
            "demographics": demographics,
            "raw_notes": notes_list,
            "vitals": vitals,
            "risk_scores": [],
            "differentials": [],
            "imaging_data": None,
            "safety_flags": [],
            "symbolic_overrides": [],
            "evidence": [],
            "audit_trail": [],
            "current_step": "initialized",
            "error_logs": [],
            "authenticated_clinician": clinician_identity
        }

        thread_config = {"configurable": {"thread_id": session.thread_id}}

        logger.info(f"Invoking LangGraph execution for session [{session_id}] (thread: {session.thread_id}).")
        self.graph.invoke(initial_state, config=thread_config)

        snapshot = self.graph.get_state(thread_config)
        state_values = snapshot.values
        next_step = snapshot.next[0] if snapshot.next else None

        if next_step == "data_request_review":
            session_status = "WAITING_FOR_CLINICAL_DATA"
        elif next_step == "human_review":
            session_status = "WAITING_FOR_CLINICIAN_REVIEW"
        elif snapshot.next == ():
            session_status = "COMPLETED"
        else:
            session_status = "IN_PROGRESS"

        self.sess_repo.update_session_status(
            session_id=session_id,
            status=session_status,
            current_step=state_values.get("current_step", "in_progress")
        )

        self._sync_audit_and_results(session, state_values)

        return {
            "session_id": session_id,
            "status": session_status,
            "current_step": state_values.get("current_step"),
            "next_node": next_step,
            "pending_requests": _to_json_serializable(state_values.get("pending_data_requests", []))
        }

    def resolve_data_request(
        self,
        session_id: str,
        request_id: str,
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolves a pending ClinicalDataRequest with clinician inputs and resumes graph execution
        directly at the requesting agent node.
        """
        session = self.sess_repo.get_by_session_id(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        thread_config = {"configurable": {"thread_id": session.thread_id}}
        snapshot = self.graph.get_state(thread_config)
        if not snapshot.values:
            raise ValueError(f"No active LangGraph checkpoint found for session [{session_id}].")

        pending_requests = snapshot.values.get("pending_data_requests", [])
        target_req = next((r for r in pending_requests if (r.request_id if hasattr(r, "request_id") else r.get("request_id")) == request_id), None)
        if not target_req:
            raise ValueError(f"ClinicalDataRequest [{request_id}] not found in session pending requests.")

        # Validate clinician input against field requirements
        validate_response(target_req, response_data)

        # Mark resolved in core model and DB repository
        resolved_req = core_resolve_request(target_req, response_data)
        self.sess_repo.resolve_data_request(request_id, response_data)

        # Apply response data to state and update checkpoint
        state_updates = apply_response_to_state(snapshot.values, response_data)
        state_updates["pending_data_requests"] = [r for r in pending_requests if (r.request_id if hasattr(r, "request_id") else r.get("request_id")) != request_id]
        
        resolved_list = snapshot.values.get("resolved_data_requests", []) + [resolved_req]
        state_updates["resolved_data_requests"] = resolved_list
        state_updates["active_data_request_id"] = request_id

        self.graph.update_state(thread_config, state_updates)

        # Resume graph execution
        logger.info(f"Resuming graph after resolving data request [{request_id}].")
        self.graph.invoke(None, config=thread_config)

        resumed_snapshot = self.graph.get_state(thread_config)
        resumed_values = resumed_snapshot.values
        next_step = resumed_snapshot.next[0] if resumed_snapshot.next else None

        if next_step == "data_request_review":
            session_status = "WAITING_FOR_CLINICAL_DATA"
        elif next_step == "human_review":
            session_status = "WAITING_FOR_CLINICIAN_REVIEW"
        elif resumed_snapshot.next == ():
            session_status = "COMPLETED"
        else:
            session_status = "IN_PROGRESS"

        self.sess_repo.update_session_status(
            session_id=session_id,
            status=session_status,
            current_step=resumed_values.get("current_step", "in_progress")
        )

        self._sync_audit_and_results(session, resumed_values)

        return {
            "session_id": session_id,
            "status": session_status,
            "current_step": resumed_values.get("current_step"),
            "next_node": next_step,
            "request_id": request_id,
            "resolution": "SUCCESS"
        }

    def approve_session(
        self,
        session_id: str,
        clinician: ClinicianIdentity,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clinician approves CDS recommendations, resuming graph to ehr_export node."""
        session = self.sess_repo.get_by_session_id(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        thread_config = {"configurable": {"thread_id": session.thread_id}}

        self.graph.update_state(
            thread_config,
            {
                "authenticated_clinician": clinician,
                "approved_by_clinician": True,
                "re_evaluation_requested": False,
                "clinician_notes": notes
            }
        )

        self.graph.invoke(None, config=thread_config)

        final_snapshot = self.graph.get_state(thread_config)
        final_values = final_snapshot.values

        self.sess_repo.update_session_status(
            session_id=session_id,
            status="APPROVED",
            current_step="ehr_exported",
            clinician_notes=notes,
            completed=True,
            approved=True
        )

        self._sync_audit_and_results(session, final_values)

        return {
            "session_id": session_id,
            "status": "APPROVED",
            "current_step": "ehr_exported",
            "message": "CDS package successfully approved by clinician and exported to EHR."
        }

    def reevaluate_session(
        self,
        session_id: str,
        clinician: ClinicianIdentity,
        notes: str
    ) -> Dict[str, Any]:
        """Clinician requests re-evaluation loop with feedback notes."""
        session = self.sess_repo.get_by_session_id(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        thread_config = {"configurable": {"thread_id": session.thread_id}}

        self.graph.update_state(
            thread_config,
            {
                "authenticated_clinician": clinician,
                "approved_by_clinician": False,
                "re_evaluation_requested": True,
                "clinician_notes": notes
            }
        )

        self.graph.invoke(None, config=thread_config)

        resumed_snapshot = self.graph.get_state(thread_config)
        resumed_values = resumed_snapshot.values
        next_step = resumed_snapshot.next[0] if resumed_snapshot.next else None

        session_status = "WAITING_FOR_CLINICIAN_REVIEW" if next_step == "human_review" else "RE_EVALUATION_IN_PROGRESS"

        self.sess_repo.update_session_status(
            session_id=session_id,
            status=session_status,
            current_step=resumed_values.get("current_step", "clinician_re_evaluation_requested"),
            iteration_count=resumed_values.get("iteration_count", 0),
            clinician_notes=notes
        )

        self._sync_audit_and_results(session, resumed_values)

        return {
            "session_id": session_id,
            "status": session_status,
            "current_step": resumed_values.get("current_step"),
            "iteration_count": resumed_values.get("iteration_count", 0),
            "next_node": next_step
        }

    def reject_session(
        self,
        session_id: str,
        clinician: ClinicianIdentity,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clinician rejects recommendations and triggers manual takeover."""
        session = self.sess_repo.get_by_session_id(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        thread_config = {"configurable": {"thread_id": session.thread_id}}

        self.graph.update_state(
            thread_config,
            {
                "authenticated_clinician": clinician,
                "approved_by_clinician": False,
                "re_evaluation_requested": False,
                "clinician_notes": notes
            }
        )

        self.graph.invoke(None, config=thread_config)

        final_snapshot = self.graph.get_state(thread_config)
        final_values = final_snapshot.values

        self.sess_repo.update_session_status(
            session_id=session_id,
            status="REJECTED_MANUAL_TAKEOVER",
            current_step="clinician_rejected_manual_takeover",
            clinician_notes=notes,
            completed=True
        )

        self._sync_audit_and_results(session, final_values)

        return {
            "session_id": session_id,
            "status": "REJECTED_MANUAL_TAKEOVER",
            "current_step": "clinician_rejected_manual_takeover",
            "message": "Recommendations rejected by clinician. Manual medical takeover initiated."
        }
