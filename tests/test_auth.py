import os
import pytest
import tempfile
from src.auth.database import init_db, register_doctor, authenticate_doctor, get_db_connection
from src.auth.session import save_persistent_session, load_persistent_session


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    init_db(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


def test_init_and_seed_doctor(temp_db):
    """Verify default doctor DOC-88204 is seeded automatically."""
    user = authenticate_doctor("DOC-88204", "password123", db_path=temp_db)
    assert user is not None
    assert user["doctor_id"] == "DOC-88204"
    assert user["full_name"] == "Dr. Sarah Chen"
    assert user["department"] == "Emergency Medicine"


def test_register_and_authenticate_new_doctor(temp_db):
    """Test registering a new doctor with bcrypt hashing and authenticating."""
    registered = register_doctor(
        doctor_id="DOC-99001",
        full_name="Dr. Gregory House",
        department="Diagnostic Medicine",
        password="securepassword",
        db_path=temp_db
    )
    assert registered is True

    # Authenticate valid password
    auth_user = authenticate_doctor("DOC-99001", "securepassword", db_path=temp_db)
    assert auth_user is not None
    assert auth_user["full_name"] == "Dr. Gregory House"
    assert auth_user["department"] == "Diagnostic Medicine"

    # Authenticate invalid password
    invalid = authenticate_doctor("DOC-99001", "wrongpassword", db_path=temp_db)
    assert invalid is None


def test_register_duplicate_doctor_fails(temp_db):
    """Test registering duplicate doctor_id fails gracefully."""
    dup = register_doctor(
        doctor_id="DOC-88204",
        full_name="Duplicate Doctor",
        department="Surgery",
        password="password123",
        db_path=temp_db
    )
    assert dup is False


def test_jwt_session_save_and_load():
    """Test JWT token encoding and decoding."""
    doc_info = {
        "doctor_id": "DOC-88204",
        "full_name": "Dr. Sarah Chen",
        "department": "Emergency Medicine",
        "role": "Attending Physician"
    }

    token = save_persistent_session(doc_info)
    assert isinstance(token, str)
    assert len(token) > 20

    decoded = load_persistent_session(token)
    assert decoded is not None
    assert decoded["doctor_id"] == "DOC-88204"
    assert decoded["full_name"] == "Dr. Sarah Chen"
    assert decoded["department"] == "Emergency Medicine"


def test_invalid_jwt_session():
    """Test loading invalid or corrupted JWT token returns None."""
    decoded = load_persistent_session("invalid.jwt.token")
    assert decoded is None
