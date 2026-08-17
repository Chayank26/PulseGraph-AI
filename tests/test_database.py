import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.database import Base
from src.db.repositories.doctor_repository import DoctorRepository
from src.db.repositories.patient_repository import PatientRepository
from src.db.repositories.session_repository import SessionRepository
from config.settings import settings


@pytest.fixture
def db_session():
    """Fixture providing a transactional PostgreSQL database session for testing."""
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_doctor_repository_lifecycle(db_session):
    """Test DoctorRepository creation, retrieval, and bcrypt authentication."""
    repo = DoctorRepository(db_session)
    doc_id = "DOC-TEST-999"

    # Create doctor
    doc = repo.create(
        doctor_id=doc_id,
        full_name="Dr. Test Physician",
        department="Internal Medicine",
        password="securePassword123!",
        role="Attending Physician"
    )
    assert doc.doctor_id == doc_id
    assert doc.full_name == "Dr. Test Physician"

    # Authenticate valid credentials
    auth_doc = repo.authenticate(doc_id, "securePassword123!")
    assert auth_doc is not None
    assert auth_doc.doctor_id == doc_id

    # Authenticate invalid password
    invalid_auth = repo.authenticate(doc_id, "wrongPassword")
    assert invalid_auth is None


def test_patient_repository_lifecycle(db_session):
    """Test PatientRepository creation, retrieval, and updates."""
    repo = PatientRepository(db_session)
    pat_id = "PAT-TEST-999"

    patient = repo.create(
        patient_id=pat_id,
        age=55,
        gender="Female",
        blood_type="O+",
        allergies=["Aspirin"],
        chronic_conditions=["Hypertension"],
        current_medications=["Lisinopril 10mg"]
    )
    assert patient.patient_id == pat_id
    assert patient.age == 55

    # Update patient
    updated = repo.update(pat_id, {"age": 56, "chronic_conditions": ["Hypertension", "Diabetes"]})
    assert updated.age == 56
    assert "Diabetes" in updated.chronic_conditions


def test_session_repository_lifecycle(db_session):
    """Test SessionRepository session creation, data request, audit log, and CDS result persistence."""
    doc_repo = DoctorRepository(db_session)
    pat_repo = PatientRepository(db_session)
    sess_repo = SessionRepository(db_session)

    d_id = "DOC-SESS-001"
    p_id = "PAT-SESS-001"

    doc_repo.create(doctor_id=d_id, full_name="Dr. Session", department="ER", password="pass")
    pat_repo.create(patient_id=p_id, age=50, gender="Male")

    session_id = "SESS-TEST-001"
    sess = sess_repo.create_session(
        session_id=session_id,
        patient_id=p_id,
        doctor_id=d_id,
        thread_id="thread-test-001",
        status="IN_PROGRESS",
        current_step="initialized"
    )
    assert sess.session_id == session_id

    # Persist data request
    req = sess_repo.create_data_request(
        session_id=session_id,
        request_id="REQ-TEST-001",
        requesting_agent="triage",
        pathway_name="HEART Score",
        reason="Missing ECG",
        required_fields=[{"field_key": "ecg_score", "label": "ECG", "data_type": "enum", "required": True}]
    )
    assert req.request_id == "REQ-TEST-001"

    # Add audit log
    audit = sess_repo.add_audit_log(
        session_id=session_id,
        agent_name="TriageAgent",
        action="DATA_REQUEST_CREATED",
        summary="Created HEART data request"
    )
    assert audit.session_id == session_id

    # Save CDS result
    cds = sess_repo.save_cds_result(
        session_id=session_id,
        risk_scores=[{"score_name": "HEART Score", "value": 4.0}],
        differentials=[{"condition_name": "Acute Coronary Syndrome", "likelihood": "High"}],
        imaging_findings=[],
        evidence=[],
        safety_flags=[],
        symbolic_overrides=[],
        final_status="COMPLETED"
    )
    assert cds.session_id == session_id
    assert len(cds.risk_scores) == 1
