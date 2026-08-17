from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_db, get_current_clinician
from src.api.schemas.patients import PatientCreate, PatientUpdate, PatientResponse
from src.db.models import DoctorModel
from src.db.repositories.patient_repository import PatientRepository

router = APIRouter(prefix="/api/patients", tags=["Patient Records"])


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED, summary="Create Patient Record")
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """Create a new patient record in PostgreSQL."""
    patient_repo = PatientRepository(db)
    try:
        patient = patient_repo.create(
            patient_id=payload.patient_id,
            age=payload.age,
            gender=payload.gender,
            blood_type=payload.blood_type,
            allergies=payload.allergies,
            chronic_conditions=payload.chronic_conditions,
            current_medications=payload.current_medications
        )
        return patient
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("", response_model=List[PatientResponse], summary="List All Patients")
def list_patients(
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """Retrieve all patient records."""
    patient_repo = PatientRepository(db)
    return patient_repo.get_all()


@router.get("/{patient_id}", response_model=PatientResponse, summary="Get Patient Details")
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """Retrieve patient record by patient_id."""
    patient_repo = PatientRepository(db)
    patient = patient_repo.get_by_patient_id(patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient '{patient_id}' not found.")
    return patient


@router.put("/{patient_id}", response_model=PatientResponse, summary="Update Patient Record")
def update_patient(
    patient_id: str,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    current_clinician: DoctorModel = Depends(get_current_clinician)
):
    """Update existing patient record."""
    patient_repo = PatientRepository(db)
    patient = patient_repo.update(patient_id, payload.model_dump(exclude_unset=True))
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient '{patient_id}' not found.")
    return patient
