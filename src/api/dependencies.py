import logging
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt

from config.settings import settings
from src.db.database import SessionLocal
from src.db.models import DoctorModel
from src.db.repositories.doctor_repository import DoctorRepository

logger = logging.getLogger("PulseGraph.API.Dependencies")

security = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency providing isolated SQLAlchemy database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_clinician(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> DoctorModel:
    """
    FastAPI authentication dependency.
    Decodes and validates JWT bearer token and injects authenticated DoctorModel.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate clinician authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.pulsegraph_jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        doctor_id: Optional[str] = payload.get("doctor_id")
        if doctor_id is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Physician session token has expired. Please authenticate again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as e:
        logger.warning(f"JWT Validation Error: {e}")
        raise credentials_exception

    doctor_repo = DoctorRepository(db)
    doctor = doctor_repo.get_by_doctor_id(doctor_id)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Authenticated doctor account '{doctor_id}' no longer exists."
        )

    return doctor
