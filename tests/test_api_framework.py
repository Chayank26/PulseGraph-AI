import uuid
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"


def test_doctor_auth_and_patient_api_lifecycle():
    uid = uuid.uuid4().hex[:6]
    # 1. Register a doctor
    doc_id = f"DOC-API-{uid}"
    reg_payload = {
        "doctor_id": doc_id,
        "full_name": "Dr. API Test",
        "department": "Emergency Medicine",
        "password": "Password123!",
        "role": "Attending Physician"
    }
    reg_resp = client.post("/api/doctors", json=reg_payload)
    assert reg_resp.status_code == 201
    assert reg_resp.json()["doctor_id"] == doc_id

    # 2. Login to get JWT token
    login_resp = client.post("/api/auth/login", json={"doctor_id": doc_id, "password": "Password123!"})
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    token = token_data["access_token"]
    assert token is not None

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Get profile /api/doctors/me
    me_resp = client.get("/api/doctors/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["doctor_id"] == doc_id

    # 4. Create patient via API
    pat_id = f"PAT-API-{uid}"
    pat_payload = {
        "patient_id": pat_id,
        "age": 64,
        "gender": "Male",
        "blood_type": "A+",
        "allergies": ["Penicillin"],
        "chronic_conditions": ["Hypertension"],
        "current_medications": ["Metoprolol"]
    }
    create_pat_resp = client.post("/api/patients", json=pat_payload, headers=headers)
    assert create_pat_resp.status_code == 201
    assert create_pat_resp.json()["patient_id"] == pat_id

    # 5. Retrieve patient details
    get_pat_resp = client.get(f"/api/patients/{pat_id}", headers=headers)
    assert get_pat_resp.status_code == 200
    assert get_pat_resp.json()["age"] == 64

    # 6. Initialize clinical session
    sess_payload = {
        "patient_id": pat_id,
        "raw_notes": ["Patient presents with chest pain."]
    }
    sess_resp = client.post("/api/clinical/sessions", json=sess_payload, headers=headers)
    assert sess_resp.status_code == 201
    sess_data = sess_resp.json()
    assert sess_data["patient_id"] == pat_id
    assert sess_data["doctor_id"] == doc_id
    assert sess_data["session_id"].startswith("SESS-")
