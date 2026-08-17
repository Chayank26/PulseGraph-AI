from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_db, get_current_clinician
from src.api.schemas.doctors import DoctorCreate, DoctorResponse
from src.db.models import DoctorModel
from src.db.repositories.doctor_repository import DoctorRepository

router = APIRouter(prefix="/api/doctors", tags=["Doctors & Clinicians"])


@router.post("", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED, summary="Register New Clinician")
def create_doctor(payload: DoctorCreate, db: Session = Depends(get_db)):
    """Register a new clinician / attending physician with password hashing."""
    doctor_repo = DoctorRepository(db)
    try:
        doctor = doctor_repo.create(
            doctor_id=payload.doctor_id,
            full_name=payload.full_name,
            department=payload.department,
            password=payload.password,
            role=payload.role
        )
        return doctor
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/me", response_model=DoctorResponse, summary="Get Authenticated Clinician Profile")
def get_current_doctor_profile(current_clinician: DoctorModel = Depends(get_current_clinician)):
    """Retrieve current authenticated physician profile from JWT session token."""
    return current_clinician


@router.get("", response_model=List[DoctorResponse], summary="List Registered Clinicians")
def list_doctors(db: Session = Depends(get_db), current_clinician: DoctorModel = Depends(get_current_clinician)):
    """List all registered attending clinicians."""
    doctor_repo = DoctorRepository(db)
    return doctor_repo.get_all()
