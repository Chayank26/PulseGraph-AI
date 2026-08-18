import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_db, get_current_clinician, to_clinician_identity
from src.api.schemas.sessions import (
    SessionCreateRequest,
    SessionResponse,
    DataRequestResolvePayload,
    ClinicianReviewPayload,
    ClinicianReevaluatePayload
)
from src.db.models import DoctorModel
from src.db.repositories.patient_repository import PatientRepository
from src.db.repositories.session_repository import SessionRepository
from src.services.clinical_workflow import ClinicalWorkflowService

router = APIRouter(prefix="/api/clinical/sessions", tags=["Clinical Sessions & Assessment"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED, summary="Initialize Clinical Session")
def create_session(
    payload: SessionCreateRequest,
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """
    Initialize a new PulseGraph clinical decision-support session for a patient.
    Generates a unique session_id and LangGraph thread_id.
    """
    patient_repo = PatientRepository(db)
    patient = patient_repo.get_by_patient_id(payload.patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{payload.patient_id}' does not exist. Please create patient first."
        )

    sess_repo = SessionRepository(db)
    session_id = f"SESS-{uuid.uuid4().hex[:8].upper()}"
    thread_id = f"thread-{session_id}"

    session = sess_repo.create_session(
        session_id=session_id,
        patient_id=payload.patient_id,
        doctor_id=current_clinician.doctor_id,
        thread_id=thread_id,
        status="INITIALIZED",
        current_step="initialized"
    )
    return session


@router.post("/{session_id}/run", summary="Run/Execute Clinical Session Workflow")
def run_session(
    session_id: str,
    raw_notes: Optional[List[str]] = None,
    image_path: Optional[str] = None,
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """
    Triggers/executes the multi-agent LangGraph workflow for a session.
    Automatically pauses at data_request_review or human_review.
    """
    workflow_service = ClinicalWorkflowService(db)
    try:
        result = workflow_service.run_session(
            session_id=session_id,
            raw_notes=raw_notes,
            image_path=image_path
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Workflow execution error: {e}")


@router.get("/{session_id}", response_model=SessionResponse, summary="Get Clinical Session Progress")
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """Retrieve current clinical session details and workflow state."""
    sess_repo = SessionRepository(db)
    session = sess_repo.get_by_session_id(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session '{session_id}' not found.")
    return session


@router.get("", response_model=List[SessionResponse], summary="List Physician Sessions")
def list_sessions(
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """List all clinical assessment sessions initiated by the authenticated physician."""
    sess_repo = SessionRepository(db)
    return sess_repo.get_all_by_doctor(current_clinician.doctor_id)
