from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_db, get_current_clinician
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


@router.get("/{session_id}/results", response_model=CDSResultResponse, summary="Get Generated CDS Recommendations")
def get_session_results(
    session_id: str,
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """Retrieve persistent generated clinical decision-support results (risk scores, differentials, evidence, safety)."""
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
