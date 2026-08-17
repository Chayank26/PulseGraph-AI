from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import jwt

from config.settings import settings
from src.api.dependencies import get_db
from src.api.schemas.auth import LoginRequest, TokenResponse
from src.db.repositories.doctor_repository import DoctorRepository

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, summary="Physician Login Authentication")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate clinician using doctor_id and password.
    Returns signed JWT bearer token upon successful authentication.
    """
    doctor_repo = DoctorRepository(db)
    doctor = doctor_repo.authenticate(payload.doctor_id, payload.password)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid physician doctor_id or password."
        )

    now = datetime.now(timezone.utc)
    token_payload = {
        "doctor_id": doctor.doctor_id,
        "full_name": doctor.full_name,
        "department": doctor.department,
        "role": doctor.role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expiration_minutes)
    }

    token = jwt.encode(token_payload, settings.pulsegraph_jwt_secret, algorithm=settings.jwt_algorithm)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        doctor_id=doctor.doctor_id,
        full_name=doctor.full_name,
        department=doctor.department,
        role=doctor.role
    )
