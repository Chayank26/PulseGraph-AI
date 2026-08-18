import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
import jwt

from config.settings import settings
from src.api.dependencies import get_current_clinician, to_clinician_identity
from src.api.schemas.doctors import DoctorCreate
from src.db.models import DoctorModel
from src.db.repositories.doctor_repository import DoctorRepository
from src.core.state import ClinicianIdentity


def test_bcrypt_password_security(db_session):
    """Test bcrypt hashing security and authentication validation."""
    repo = DoctorRepository(db_session)
    doc_id = f"DOC-AUTH-{uuid.uuid4().hex[:6]}"

    # Create doctor
    doc = repo.create(
        doctor_id=doc_id,
        full_name="Dr. Auth Hardening",
        department="Cardiology",
        password="SuperSecretPassword123!",
        role="Attending Physician"
    )
    # Ensure plaintext password is NEVER stored
    assert doc.password_hash != "SuperSecretPassword123!"
    assert doc.password_hash.startswith("$2b$")

    # Valid login
    auth_doc = repo.authenticate(doc_id, "SuperSecretPassword123!")
    assert auth_doc is not None

    # Invalid login
    assert repo.authenticate(doc_id, "WrongPassword") is None


def test_doctor_registration_duplicate_rejection(db_session):
    """Test duplicate doctor registration rejection."""
    repo = DoctorRepository(db_session)
    doc_id = f"DOC-DUP-{uuid.uuid4().hex[:6]}"

    repo.create(
        doctor_id=doc_id,
        full_name="Dr. Original",
        department="ICU",
        password="Password123!"
    )

    with pytest.raises(ValueError, match="already exists"):
        repo.create(
            doctor_id=doc_id,
            full_name="Dr. Duplicate",
            department="ICU",
            password="Password123!"
        )


def test_clinician_identity_conversion(db_session):
    """Test conversion of DoctorModel to ClinicianIdentity domain object."""
    doc = DoctorModel(
        doctor_id="DOC-CONV-123",
        full_name="Dr. Conversion Test",
        department="Neurology",
        role="Consultant",
        password_hash="hashed"
    )

    identity = to_clinician_identity(doc)
    assert isinstance(identity, ClinicianIdentity)
    assert identity.doctor_id == "DOC-CONV-123"
    assert identity.full_name == "Dr. Conversion Test"
    assert identity.department == "Neurology"
    assert identity.role == "Consultant"
    assert isinstance(identity.authenticated_at, datetime)


def test_expired_jwt_token_rejection(db_session):
    """Test rejection of expired JWT session token."""
    repo = DoctorRepository(db_session)
    doc_id = f"DOC-EXP-{uuid.uuid4().hex[:6]}"
    repo.create(doctor_id=doc_id, full_name="Dr. Expired", department="ER", password="pass")

    now = datetime.now(timezone.utc)
    expired_payload = {
        "doctor_id": doc_id,
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1)
    }
    expired_token = jwt.encode(expired_payload, settings.pulsegraph_jwt_secret, algorithm=settings.jwt_algorithm)

    class MockCredentials:
        credentials = expired_token

    with pytest.raises(HTTPException) as exc_info:
        get_current_clinician(credentials=MockCredentials(), db=db_session)

    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()
