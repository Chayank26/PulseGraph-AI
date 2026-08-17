import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_db, get_current_clinician
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
