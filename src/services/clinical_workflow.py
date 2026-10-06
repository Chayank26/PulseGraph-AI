import logging
import hashlib
import json
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from src.core.state import (
    ClinicalState,
    AuditEntry,
    PatientDemographics,
    VitalSigns,
    ClinicianIdentity
)
from src.core.graph import build_clinical_graph, MAX_ITERATIONS
from src.core.diagnostic import input_fingerprint, invalidate_diagnostics
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


from src.services.session_lock import WorkflowConflictError, serialized_session


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
        for event_index, entry in enumerate(audit_trail):
            entry_dict = _to_json_serializable(entry)
            event_id = hashlib.sha256(json.dumps({'index':event_index, 'entry':entry_dict}, sort_keys=True).encode()).hexdigest()
            self.sess_repo.add_audit_log(
                session_id=session.session_id,
                agent_name=entry_dict.get("agent_name", "WorkflowSystem"),
                action=entry_dict.get("action", "STATE_UPDATE"),
                summary=entry_dict.get("summary", ""),
                metadata_json={**entry_dict.get("metadata", {}), "checkpoint_event_id":event_id},
                timestamp=datetime.fromisoformat(entry_dict["timestamp"])
            )

        # 2. Sync Pending Data Requests
        all_requests = state_values.get('pending_data_requests', []) + state_values.get('resolved_data_requests', [])
        pending_reqs = list({r.request_id:r for r in all_requests}.values())
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
                priority=req_dict.get("priority", "HIGH"),
                request_status=req_dict['status'],
                clinician_response=req_dict.get('clinician_response'),
                resolved_at=datetime.fromisoformat(req_dict['resolved_at']) if req_dict.get('resolved_at') else None,
                created_at=datetime.fromisoformat(req_dict['created_at']) if req_dict.get('created_at') else None
            )

        # 3. Sync CDS Recommendations
        self.sess_repo.save_cds_result(
            session_id=session.session_id,
            urgency=state_values.get("urgency"),
            presentation=state_values.get("presentation"),
            risk_scores=_to_json_serializable(state_values.get("risk_scores", [])),
            differentials=_to_json_serializable(state_values.get("differentials", [])),
            imaging_findings=_to_json_serializable(state_values.get("imaging_data").findings if state_values.get("imaging_data") else []),
            evidence=_to_json_serializable(state_values.get("evidence", [])),
            safety_flags=_to_json_serializable(state_values.get("safety_flags", [])),
            symbolic_overrides=_to_json_serializable(state_values.get("symbolic_overrides", [])),
            final_status=session.status,
            clinician_approval={"approved": state_values.get("approved_by_clinician"), "notes": state_values.get("clinician_notes"), "record": state_values.get("approval_record")}
        )

    @serialized_session
    def run_session(
        self,
        session_id: str,
        raw_notes: Optional[List[str]] = None,
        vitals_payload: Optional[Dict[str, Any]] = None,
        image_path: Optional[str] = None,
        urgency_context: Optional[Dict[str, Any]] = None,
        imaging_decision: Optional[Dict[str, Any]] = None,
        pathway_decisions: Optional[Dict[str, Any]] = None
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
            chief_complaint=patient_model.chief_complaint,
            allergies=patient_model.allergies or [],
            chronic_conditions=patient_model.chronic_conditions or [],
            current_medications=patient_model.current_medications or []
        )

        intake = session.intake_data or {}
        vitals_payload = vitals_payload if vitals_payload is not None else intake.get("vitals")
        vitals = VitalSigns(**vitals_payload) if vitals_payload else None

        notes_list = list(raw_notes if raw_notes is not None else intake.get("raw_notes", []))
        image_path = image_path if image_path is not None else intake.get("image_path")


        clinician_identity = ClinicianIdentity(
            doctor_id=doctor_model.doctor_id,
            full_name=doctor_model.full_name,
            department=doctor_model.department,
            role=doctor_model.role
        )

        prior = self.graph.get_state({"configurable": {"thread_id": session.thread_id}})
        if prior.values:
            raise WorkflowConflictError("This session has already started. Resolve its pending request, use clinician review, or create a new session for a new assessment.")
        initial_state: ClinicalState = {
            "urgency_observation_revision": prior.values.get("urgency_observation_revision", 0) + 1,
            "urgency_resume_node": "triage",
            "active_data_request_id": None,
            "patient_id": patient_model.patient_id,
            "demographics": demographics,
            "raw_notes": notes_list,
            "vitals": vitals,
            "image_path": image_path,
            "imaging_decision": imaging_decision if imaging_decision is not None else intake.get("imaging_decision"),
            "pathway_decisions": pathway_decisions if pathway_decisions is not None else intake.get("pathway_decisions"),
            "urgency_context": urgency_context if urgency_context is not None else intake.get("urgency_context"),
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

        if state_values.get("current_step") in ("triage_manual_review_required", "imaging_manual_review_required"):
            session_status = "REQUIRES_CLINICIAN_ASSESSMENT"
        elif next_step == "data_request_review":
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

    @serialized_session
    def resolve_data_request(
        self,
        session_id: str,
        request_id: str,
        response_data: Dict[str, Any],
        reviewing_doctor_id: Optional[str] = None
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
            raise WorkflowConflictError(f"Checkpoint unavailable for session [{session_id}]; recovery is required before continuing.")

        pending_requests = snapshot.values.get("pending_data_requests", [])
        target_req = next((r for r in pending_requests if (r.request_id if hasattr(r, "request_id") else r.get("request_id")) == request_id), None)
        if not target_req:
            if any((r.request_id if hasattr(r, 'request_id') else r.get('request_id')) == request_id
                   for r in snapshot.values.get('resolved_data_requests', [])):
                raise WorkflowConflictError('This clinical data request has already been resolved. Reload the session.')
            raise ValueError(f"ClinicalDataRequest [{request_id}] not found in session pending requests.")

        if (target_req.requesting_agent in ("urgency_check", "imaging", "diagnostic", "safety") or target_req.pathway_name == "Low-back clinical assessment") and reviewing_doctor_id != session.doctor_id:
            raise ValueError("Urgency, imaging and diagnostic decisions must be reviewed by the session's authenticated clinician.")

        request_status = target_req.status if hasattr(target_req, 'status') else target_req.get('status')
        if request_status != 'PENDING':
            raise WorkflowConflictError('This clinical data request has already been resolved. Reload the session.')

        # Validate clinician input against field requirements
        validate_response(target_req, response_data)

        # Mark resolved in core model and DB repository
        resolved_req = core_resolve_request(target_req, response_data)

        # Apply response data to state and update checkpoint
        state_updates = apply_response_to_state(snapshot.values, response_data)
        state_updates["pending_data_requests"] = [r if (r.request_id if hasattr(r, "request_id") else r.get("request_id")) != request_id else resolved_req for r in pending_requests]
        
        resolved_list = snapshot.values.get("resolved_data_requests", []) + [resolved_req]
        state_updates["resolved_data_requests"] = resolved_list
        state_updates["active_data_request_id"] = request_id
        if target_req.requesting_agent == "urgency_check":
            state_updates["audit_trail"].append(AuditEntry(
                agent_name="UrgencyScreen", action="URGENCY_REVIEW_ACKNOWLEDGED",
                summary="Clinician reviewed flagged observations and permitted assessment continuation.",
                metadata={"doctor_id": reviewing_doctor_id, "request_id": request_id}))

        if snapshot.values.get('diagnostic_fingerprint'):
            state_updates.update(invalidate_diagnostics(snapshot.values))
            state_updates.update(active_data_request_id=None, urgency_resume_node='triage')

        # Route from the review checkpoint back to the requesting agent.
        # Inferring the last writer (triage) would skip its unfinished scores.
        self.graph.update_state(thread_config, state_updates, as_node="data_request_review")

        self._sync_audit_and_results(session, self.graph.get_state(thread_config).values)

        # Resume graph execution
        logger.info(f"Resuming graph after resolving data request [{request_id}].")
        self.graph.invoke(None, config=thread_config)

        resumed_snapshot = self.graph.get_state(thread_config)
        resumed_values = resumed_snapshot.values
        next_step = resumed_snapshot.next[0] if resumed_snapshot.next else None

        if resumed_values.get("current_step") in ("triage_manual_review_required", "imaging_manual_review_required"):
            session_status = "REQUIRES_CLINICIAN_ASSESSMENT"
        elif next_step == "data_request_review":
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

    @serialized_session
    def recover_session(self, session_id, doctor_id):
        """Rebuild projections only at stable graph boundaries; never replay clinical actions."""
        session = self.sess_repo.get_by_session_id(session_id)
        if session is None:
            raise ValueError('Session not found.')
        if session.doctor_id != doctor_id:
            raise PermissionError('Only the session owner may recover this session.')
        snapshot = self.graph.get_state({'configurable': {'thread_id':session.thread_id}})
        values = snapshot.values
        if not values:
            raise WorkflowConflictError('Checkpoint unavailable; automatic reconstruction is not supported.')
        recovered_approval = False
        if snapshot.next in (('human_review',), ('ehr_export',)) and values.get('approved_by_clinician'):
            record = values.get('approval_record')
            if not record or record.get('doctor_id') != doctor_id or not record.get('review_version') or not record.get('approved_at'):
                raise WorkflowConflictError('Interrupted approval has no attributable record; operator recovery is required.')
            if values.get('diagnostic_fingerprint') != input_fingerprint(values):
                raise WorkflowConflictError('Interrupted approval inputs are stale; operator recovery is required.')
            # Re-enter the review interruption without invoking any clinical or export node.
            config = {'configurable': {'thread_id':session.thread_id}}
            self.graph.update_state(config, {
                'approved_by_clinician': False, 'approval_record': None,
                're_evaluation_requested': False, 'current_step':'clinician_review_recovered',
                'audit_trail':[AuditEntry(agent_name='HumanReviewNode', action='INTERRUPTED_APPROVAL_RESET',
                    summary='Owner returned interrupted approval to fresh review; prior intent was not replayed.',
                    metadata={'doctor_id':doctor_id, 'prior_approval':record})]
            }, as_node='symbolic_guardrail')
            snapshot = self.graph.get_state(config)
            values = snapshot.values
            recovered_approval = True
        if snapshot.next not in ((), ('human_review',), ('data_request_review',)):
            raise WorkflowConflictError('Checkpoint is mid-transition; operator recovery is required. No action was replayed.')
        step = values.get('current_step', 'unknown')
        if snapshot.next == ('data_request_review',):
            status = 'WAITING_FOR_CLINICAL_DATA'
        elif snapshot.next == ('human_review',):
            status = 'WAITING_FOR_CLINICIAN_REVIEW'
        elif step in ('triage_manual_review_required', 'imaging_manual_review_required'):
            status = 'REQUIRES_CLINICIAN_ASSESSMENT'
        elif step == 'ehr_exported' and values.get('approved_by_clinician'):
            status = 'APPROVED'
        elif step == 'clinician_rejected_manual_takeover':
            status = 'REJECTED_MANUAL_TAKEOVER'
        else:
            raise WorkflowConflictError('Checkpoint has no recognized stable outcome; operator recovery is required.')
        self.sess_repo.update_session_status(session_id, status, current_step=step,
            iteration_count=values.get('iteration_count', 0), approved=status == 'APPROVED',
            completed=status in ('APPROVED', 'REJECTED_MANUAL_TAKEOVER'),
            clear_approval=status == 'WAITING_FOR_CLINICIAN_REVIEW')
        self._sync_audit_and_results(session, values)
        return {'session_id':session_id, 'status':status, 'recovery':'FRESH_REVIEW_REQUIRED' if recovered_approval else 'PROJECTIONS_RECONCILED',
                'clinical_actions_replayed':False}

    @serialized_session
    def review_package(self, session_id, doctor_id):
        return self._review_package(session_id, doctor_id)

    def _review_package(self, session_id, doctor_id):
        from hashlib import sha256
        import json
        session = self.sess_repo.get_by_session_id(session_id)
        if not session:
            raise ValueError('Session not found.')
        if session.doctor_id != doctor_id:
            raise PermissionError('Only the session owner may review or approve this package.')
        snapshot = self.graph.get_state({'configurable': {'thread_id': session.thread_id}})
        values = snapshot.values
        if not values:
            raise WorkflowConflictError('Checkpoint unavailable; recovery is required before clinical review.')
        fields = ('demographics', 'vitals', 'urgency', 'presentation', 'risk_scores', 'differentials',
                  'imaging_data', 'evidence', 'safety_flags', 'symbolic_overrides', 'medication_reconciliation')
        package = {key:_to_json_serializable(values.get(key)) for key in fields}
        binding = {'session_id':session_id, 'checkpoint':snapshot.config, 'package':package}
        version = sha256(json.dumps(binding, sort_keys=True, default=str).encode()).hexdigest()
        interrupted_approval = snapshot.next in (('human_review',), ('ehr_export',)) and bool(values.get('approved_by_clinician'))
        eligible = (not interrupted_approval and snapshot.next == ('human_review',) and bool(values.get('diagnostic_fingerprint'))
                    and values['diagnostic_fingerprint'] == input_fingerprint(values))
        return {**package, 'session_id':session_id, 'patient_id':session.patient_id,
                'status':session.status, 'review_version':version, 'can_approve':eligible,
                'at_review_checkpoint':snapshot.next == ('human_review',) and not interrupted_approval,
                'recovery_required':interrupted_approval,
                'approval':values.get('approval_record'),
                'limitations':['Approval records clinician review; it is not clinical validation or proof of EHR delivery.']}

    @serialized_session
    def approve_session(
        self,
        session_id: str,
        clinician: ClinicianIdentity,
        notes: Optional[str] = None,
        review_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clinician approves CDS recommendations, resuming graph to ehr_export node."""
        session = self.sess_repo.get_by_session_id(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        package = self._review_package(session_id, clinician.doctor_id)
        if package['recovery_required']:
            raise WorkflowConflictError('Approval was interrupted. Recover this session and review the new package before approving.')
        thread_config = {"configurable": {"thread_id": session.thread_id}}
        if self.graph.get_state(thread_config).next != ("human_review",):
            raise ValueError("Clinical review actions require the human-review checkpoint; pending data or urgency review must be completed first.")


        snapshot = self.graph.get_state(thread_config)
        if not snapshot.values.get('diagnostic_fingerprint') or snapshot.values['diagnostic_fingerprint'] != input_fingerprint(snapshot.values):
            raise WorkflowConflictError('Diagnostic results are stale. Request reevaluation before approval.')

        if not review_version or review_version != package['review_version']:
            raise WorkflowConflictError('Review package changed or no version was supplied. Reload and review before approval.')
        approval_record = {'review_version':review_version, 'doctor_id':clinician.doctor_id,
                           'approved_at':datetime.now(timezone.utc).isoformat()}

        self.graph.update_state(
            thread_config,
            {
                "approval_record": approval_record,
                "audit_trail": [AuditEntry(agent_name='HumanReviewNode', action='VERSIONED_APPROVAL',
                    summary='Session owner approved the displayed review package.', metadata=approval_record)],
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
            "message": "Clinical review approval recorded. External EHR delivery is not implemented."
        }

    @serialized_session
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

        if session.doctor_id != clinician.doctor_id:
            raise PermissionError('Only the session owner may make clinical review decisions.')

        thread_config = {"configurable": {"thread_id": session.thread_id}}
        if self.graph.get_state(thread_config).next != ("human_review",):
            raise ValueError("Clinical review actions require the human-review checkpoint; pending data or urgency review must be completed first.")


        if self.graph.get_state(thread_config).values.get('iteration_count', 0) >= MAX_ITERATIONS:
            raise WorkflowConflictError('Reevaluation limit reached; clinician takeover is required.')

        self.graph.update_state(
            thread_config,
            {
                "authenticated_clinician": clinician,
                "approved_by_clinician": False,
                "re_evaluation_requested": True,
                **invalidate_diagnostics(self.graph.get_state(thread_config).values),
                "clinician_notes": notes
            }
        )

        self._sync_audit_and_results(session, self.graph.get_state(thread_config).values)
        self.graph.invoke(None, config=thread_config)

        resumed_snapshot = self.graph.get_state(thread_config)
        resumed_values = resumed_snapshot.values
        next_step = resumed_snapshot.next[0] if resumed_snapshot.next else None

        session_status = ("REQUIRES_CLINICIAN_ASSESSMENT" if resumed_values.get('current_step') in ('triage_manual_review_required', 'imaging_manual_review_required') else "WAITING_FOR_CLINICAL_DATA" if next_step == "data_request_review" else
                          "WAITING_FOR_CLINICIAN_REVIEW" if next_step == "human_review" else "RE_EVALUATION_IN_PROGRESS")

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

    @serialized_session
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

        if session.doctor_id != clinician.doctor_id:
            raise PermissionError('Only the session owner may make clinical review decisions.')

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
