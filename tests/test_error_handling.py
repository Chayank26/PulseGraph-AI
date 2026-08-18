import uuid
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_401_unauthorized_without_token():
    """Verify 401 Unauthorized response when accessing protected endpoint without JWT token."""
    response = client.get("/api/doctors/me")
    assert response.status_code == 401
    assert "not validate" in response.json()["detail"].lower() or "credentials" in response.json()["detail"].lower()


def test_404_not_found_for_nonexistent_resources():
    """Verify 404 Not Found response when requesting nonexistent patient or session."""
    uid = uuid.uuid4().hex[:6]
    doc_id = f"DOC-ERR-{uid}"
    client.post("/api/doctors", json={"doctor_id": doc_id, "full_name": "Dr. Err", "department": "ER", "password": "Password123!"})
    token = client.post("/api/auth/login", json={"doctor_id": doc_id, "password": "Password123!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Nonexistent patient
    pat_resp = client.get("/api/patients/PAT-NONEXISTENT-999", headers=headers)
    assert pat_resp.status_code == 404
    assert "not found" in pat_resp.json()["detail"].lower()

    # Nonexistent session
    sess_resp = client.get("/api/clinical/sessions/SESS-NONEXISTENT-999", headers=headers)
    assert sess_resp.status_code == 404
    assert "not found" in sess_resp.json()["detail"].lower()


def test_409_conflict_on_duplicate_doctor():
    """Verify 409 Conflict when attempting to register duplicate doctor_id."""
    uid = uuid.uuid4().hex[:6]
    doc_id = f"DOC-DUPERR-{uid}"

    res1 = client.post("/api/doctors", json={"doctor_id": doc_id, "full_name": "Dr. Original", "department": "ICU", "password": "Password123!"})
    assert res1.status_code == 201

    res2 = client.post("/api/doctors", json={"doctor_id": doc_id, "full_name": "Dr. Duplicate", "department": "ICU", "password": "Password123!"})
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"].lower()


def test_422_unprocessable_entity_validation_failure():
    """Verify 422 Unprocessable Entity when request payload fails Pydantic schema validation."""
    # Password too short (<6 characters)
    res = client.post("/api/doctors", json={"doctor_id": "DOC-SHORT", "full_name": "Dr. Short", "department": "ER", "password": "123"})
    assert res.status_code == 422
    assert "validation failure" in res.json()["detail"].lower()
