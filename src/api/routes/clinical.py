from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_db, get_current_clinician, to_clinician_identity
from src.api.schemas.clinical import (
    ClinicalDataRequestResponse,
    AuditLogResponse,
    CDSResultResponse
)
from src.api.schemas.sessions import (
    DataRequestResolvePayload,
    ClinicianReviewPayload,
    ClinicianReevaluatePayload
)
from src.db.models import DoctorModel
from src.db.repositories.session_repository import SessionRepository
from src.services.clinical_workflow import ClinicalWorkflowService

router = APIRouter(prefix="/api/clinical/sessions", tags=["Clinical Decision Support Execution"])


@router.get("/{session_id}/data-requests", response_model=List[ClinicalDataRequestResponse], summary="Get Session Data Requests")
def get_session_data_requests(
    session_id: str,
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """Retrieve all pending ClinicalDataRequests for a session."""
    sess_repo = SessionRepository(db)
    session = sess_repo.get_by_session_id(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session '{session_id}' not found.")

    return sess_repo.get_pending_data_requests(session_id)


@router.post("/{session_id}/data-requests/{request_id}/resolve", summary="Resolve Clinical Data Request")
def resolve_data_request(
    session_id: str,
    request_id: str,
    payload: DataRequestResolvePayload,
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """Submit requested missing clinical data and resume workflow execution directly at requesting agent."""
    workflow_service = ClinicalWorkflowService(db)
    try:
        result = workflow_service.resolve_data_request(
            session_id=session_id,
            request_id=request_id,
            response_data=payload.response_data
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Data request resolution error: {e}")


@router.get("/{session_id}/review", summary="Get Human-in-the-Loop Clinical Review Package")
def get_review_package(
    session_id: str,
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """Retrieve complete CDS review package for attending physician review."""
    sess_repo = SessionRepository(db)
    session = sess_repo.get_by_session_id(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session '{session_id}' not found.")

    cds_result = sess_repo.get_cds_result(session_id)
    if not cds_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No CDS result generated for review yet.")

    return {
        "session_id": session_id,
        "patient_id": session.patient_id,
        "doctor_id": session.doctor_id,
        "status": session.status,
        "current_step": session.current_step,
        "risk_scores": cds_result.risk_scores,
        "differentials": cds_result.differentials,
        "imaging_findings": cds_result.imaging_findings,
        "evidence": cds_result.evidence,
        "safety_flags": cds_result.safety_flags,
        "symbolic_overrides": cds_result.symbolic_overrides
    }


@router.post("/{session_id}/approve", summary="Clinician Approval")
def approve_session(
    session_id: str,
    payload: Optional[ClinicianReviewPayload] = None,
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """Attending physician approves generated recommendations, resuming workflow to EHR export."""
    workflow_service = ClinicalWorkflowService(db)
    clinician_identity = to_clinician_identity(current_clinician)
    notes = payload.notes if payload else None
    try:
        return workflow_service.approve_session(session_id, clinician_identity, notes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{session_id}/reevaluate", summary="Clinician Request Re-evaluation")
def reevaluate_session(
    session_id: str,
    payload: ClinicianReevaluatePayload,
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """Attending physician requests re-evaluation loop with feedback instructions."""
    workflow_service = ClinicalWorkflowService(db)
    clinician_identity = to_clinician_identity(current_clinician)
    try:
        return workflow_service.reevaluate_session(session_id, clinician_identity, payload.notes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{session_id}/reject", summary="Clinician Rejection / Manual Takeover")
def reject_session(
    session_id: str,
    payload: Optional[ClinicianReviewPayload] = None,
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """Attending physician rejects recommendations and initiates manual clinical takeover."""
    workflow_service = ClinicalWorkflowService(db)
    clinician_identity = to_clinician_identity(current_clinician)
    notes = payload.notes if payload else None
    try:
        return workflow_service.reject_session(session_id, clinician_identity, notes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{session_id}/results", response_model=CDSResultResponse, summary="Get Generated CDS Recommendations")
def get_session_results(
    session_id: str,
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """Retrieve persistent generated clinical decision-support results."""
    sess_repo = SessionRepository(db)
    cds_result = sess_repo.get_cds_result(session_id)
    if not cds_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No generated CDS result found for session '{session_id}'."
        )
    return cds_result


@router.get("/{session_id}/audit-trail", response_model=List[AuditLogResponse], summary="Get Session Audit Log")
def get_session_audit_logs(
    session_id: str,
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """Retrieve append-only audit trail for a clinical assessment session."""
    sess_repo = SessionRepository(db)
    return sess_repo.get_audit_logs(session_id)
