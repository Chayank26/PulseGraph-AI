import bcrypt
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from src.db.models import DoctorModel

logger = logging.getLogger("PulseGraph.DoctorRepository")


class DoctorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_doctor_id(self, doctor_id: str) -> Optional[DoctorModel]:
        return self.db.query(DoctorModel).filter(DoctorModel.doctor_id == doctor_id).first()

    def get_all(self) -> List[DoctorModel]:
        return self.db.query(DoctorModel).all()

    def create(
        self,
        doctor_id: str,
        full_name: str,
        department: str,
        password: str,
        role: str = "Attending Physician"
    ) -> DoctorModel:
        existing = self.get_by_doctor_id(doctor_id)
        if existing:
            raise ValueError(f"Doctor ID '{doctor_id}' already exists.")

        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        doctor = DoctorModel(
            doctor_id=doctor_id,
            full_name=full_name,
            department=department,
            role=role,
            password_hash=hashed_pw
        )
        self.db.add(doctor)
        self.db.commit()
        self.db.refresh(doctor)
        logger.info(f"Created Doctor record: {doctor_id} ({full_name})")
        return doctor

    def authenticate(self, doctor_id: str, password: str) -> Optional[DoctorModel]:
        doctor = self.get_by_doctor_id(doctor_id)
        if not doctor:
            logger.warning(f"Authentication failed: Doctor ID '{doctor_id}' not found.")
            return None

        if bcrypt.checkpw(password.encode("utf-8"), doctor.password_hash.encode("utf-8")):
            logger.info(f"Doctor {doctor_id} authenticated successfully.")
            return doctor

        logger.warning(f"Authentication failed: Invalid password for doctor '{doctor_id}'.")
        return None
