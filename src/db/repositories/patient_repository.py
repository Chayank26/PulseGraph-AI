import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from src.db.models import PatientModel

logger = logging.getLogger("PulseGraph.PatientRepository")


class PatientRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_patient_id(self, patient_id: str) -> Optional[PatientModel]:
        return self.db.query(PatientModel).filter(PatientModel.patient_id == patient_id).first()

    def get_all(self) -> List[PatientModel]:
        return self.db.query(PatientModel).all()

    def create(
        self,
        patient_id: str,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        blood_type: Optional[str] = None,
        allergies: Optional[List[str]] = None,
        chronic_conditions: Optional[List[str]] = None,
        current_medications: Optional[List[str]] = None
    ) -> PatientModel:
        existing = self.get_by_patient_id(patient_id)
        if existing:
            raise ValueError(f"Patient ID '{patient_id}' already exists.")

        patient = PatientModel(
            patient_id=patient_id,
            age=age,
            gender=gender,
            blood_type=blood_type,
            allergies=allergies or [],
            chronic_conditions=chronic_conditions or [],
            current_medications=current_medications or []
        )
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        logger.info(f"Created Patient record: {patient_id}")
        return patient

    def update(self, patient_id: str, updates: Dict[str, Any]) -> Optional[PatientModel]:
        patient = self.get_by_patient_id(patient_id)
        if not patient:
            return None

        for field in ["age", "gender", "blood_type", "allergies", "chronic_conditions", "current_medications"]:
            if field in updates and updates[field] is not None:
                setattr(patient, field, updates[field])

        self.db.commit()
        self.db.refresh(patient)
        logger.info(f"Updated Patient record: {patient_id}")
        return patient
