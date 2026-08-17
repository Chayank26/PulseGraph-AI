import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from src.db.models import (
    ClinicalSessionModel,
    ClinicalDataRequestModel,
    AuditLogModel,
    CDSResultModel
)

logger = logging.getLogger("PulseGraph.SessionRepository")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_session_id(self, session_id: str) -> Optional[ClinicalSessionModel]:
        return self.db.query(ClinicalSessionModel).filter(ClinicalSessionModel.session_id == session_id).first()

    def get_all_by_doctor(self, doctor_id: str) -> List[ClinicalSessionModel]:
        return self.db.query(ClinicalSessionModel).filter(ClinicalSessionModel.doctor_id == doctor_id).all()

    def get_all_by_patient(self, patient_id: str) -> List[ClinicalSessionModel]:
        return self.db.query(ClinicalSessionModel).filter(ClinicalSessionModel.patient_id == patient_id).all()

    def create_session(
        self,
        session_id: str,
        patient_id: str,
        doctor_id: str,
        thread_id: str,
        status: str = "INITIALIZED",
        current_step: str = "initialized"
    ) -> ClinicalSessionModel:
        session = ClinicalSessionModel(
            session_id=session_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            thread_id=thread_id,
            status=status,
            current_step=current_step,
            started_at=utc_now()
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        logger.info(f"Created ClinicalSession [{session_id}] for patient '{patient_id}' (Doctor: '{doctor_id}').")
        return session

    def update_session_status(
        self,
        session_id: str,
        status: str,
        current_step: Optional[str] = None,
        iteration_count: Optional[int] = None,
        clinician_notes: Optional[str] = None,
        completed: bool = False,
        approved: bool = False
    ) -> Optional[ClinicalSessionModel]:
        session = self.get_by_session_id(session_id)
        if not session:
            return None

        session.status = status
        if current_step:
            session.current_step = current_step
        if iteration_count is not None:
            session.iteration_count = iteration_count
        if clinician_notes is not None:
            session.clinician_notes = clinician_notes
        if completed and not session.completed_at:
            session.completed_at = utc_now()
        if approved and not session.approved_at:
            session.approved_at = utc_now()

        self.db.commit()
        self.db.refresh(session)
        logger.info(f"Updated ClinicalSession [{session_id}] status -> {status} (step: {session.current_step}).")
        return session

    # --------------------------------------------------
    # Data Request Operations
    # --------------------------------------------------
    def create_data_request(
        self,
        session_id: str,
        request_id: str,
        requesting_agent: str,
        pathway_name: str,
        reason: str,
        required_fields: List[Dict[str, Any]],
        optional_fields: Optional[List[Dict[str, Any]]] = None,
        priority: str = "HIGH"
    ) -> ClinicalDataRequestModel:
        req = ClinicalDataRequestModel(
            request_id=request_id,
            session_id=session_id,
            requesting_agent=requesting_agent,
            pathway_name=pathway_name,
            reason=reason,
            priority=priority,
            required_fields=required_fields,
            optional_fields=optional_fields or [],
            status="PENDING",
            created_at=utc_now()
        )
        self.db.merge(req)
        self.db.commit()
        logger.info(f"Persisted ClinicalDataRequest [{request_id}] for session [{session_id}].")
        return req

    def get_pending_data_requests(self, session_id: str) -> List[ClinicalDataRequestModel]:
        return self.db.query(ClinicalDataRequestModel).filter(
            ClinicalDataRequestModel.session_id == session_id,
            ClinicalDataRequestModel.status == "PENDING"
        ).all()

    def resolve_data_request(
        self,
        request_id: str,
        clinician_response: Dict[str, Any]
    ) -> Optional[ClinicalDataRequestModel]:
        req = self.db.query(ClinicalDataRequestModel).filter(ClinicalDataRequestModel.request_id == request_id).first()
        if not req:
            return None

        req.status = "RESOLVED"
        req.clinician_response = clinician_response
        req.resolved_at = utc_now()

        self.db.commit()
        self.db.refresh(req)
        logger.info(f"Resolved ClinicalDataRequest [{request_id}] in database.")
        return req

    # --------------------------------------------------
    # Audit Log Operations
    # --------------------------------------------------
    def add_audit_log(
        self,
        session_id: str,
        agent_name: str,
        action: str,
        summary: str,
        metadata_json: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> AuditLogModel:
        audit = AuditLogModel(
            session_id=session_id,
            agent_name=agent_name,
            action=action,
            summary=summary,
            metadata_json=metadata_json or {},
            timestamp=timestamp or utc_now()
        )
        self.db.add(audit)
        self.db.commit()
        return audit

    def get_audit_logs(self, session_id: str) -> List[AuditLogModel]:
        return self.db.query(AuditLogModel).filter(
            AuditLogModel.session_id == session_id
        ).order_by(AuditLogModel.timestamp.asc()).all()

    # --------------------------------------------------
    # CDS Result Operations
    # --------------------------------------------------
    def save_cds_result(
        self,
        session_id: str,
        risk_scores: List[Dict[str, Any]],
        differentials: List[Dict[str, Any]],
        imaging_findings: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        safety_flags: List[Dict[str, Any]],
        symbolic_overrides: List[Dict[str, Any]],
        final_status: str = "IN_PROGRESS",
        clinician_approval: Optional[Dict[str, Any]] = None
    ) -> CDSResultModel:
        existing = self.db.query(CDSResultModel).filter(CDSResultModel.session_id == session_id).first()
        if existing:
            existing.risk_scores = risk_scores
            existing.differentials = differentials
            existing.imaging_findings = imaging_findings
            existing.evidence = evidence
            existing.safety_flags = safety_flags
            existing.symbolic_overrides = symbolic_overrides
            existing.final_status = final_status
            if clinician_approval is not None:
                existing.clinician_approval = clinician_approval
            self.db.commit()
            self.db.refresh(existing)
            return existing

        cds = CDSResultModel(
            session_id=session_id,
            risk_scores=risk_scores,
            differentials=differentials,
            imaging_findings=imaging_findings,
            evidence=evidence,
            safety_flags=safety_flags,
            symbolic_overrides=symbolic_overrides,
            final_status=final_status,
            clinician_approval=clinician_approval
        )
        self.db.add(cds)
        self.db.commit()
        self.db.refresh(cds)
        logger.info(f"Persisted CDSResult for session [{session_id}]. Status: {final_status}.")
        return cds

    def get_cds_result(self, session_id: str) -> Optional[CDSResultModel]:
        return self.db.query(CDSResultModel).filter(CDSResultModel.session_id == session_id).first()
