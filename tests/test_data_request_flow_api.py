import uuid
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_data_request_flow_api_lifecycle():
    """Integration test verifying full ClinicalDataRequest API lifecycle, validation, persistence, and resumption."""
    uid = uuid.uuid4().hex[:6]
    doc_id = f"DOC-REQ-{uid}"
    pat_id = f"PAT-REQ-{uid}"

    # 1. Register and authenticate doctor
    reg_resp = client.post("/api/doctors", json={
        "doctor_id": doc_id,
        "full_name": "Dr. Data Request Test",
        "department": "Emergency Medicine",
        "password": "Password123!",
        "role": "Attending Physician"
    })
    assert reg_resp.status_code == 201

    login_resp = client.post("/api/auth/login", json={"doctor_id": doc_id, "password": "Password123!"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create patient record
    pat_resp = client.post("/api/patients", json={
        "patient_id": pat_id,
        "age": 58,
        "gender": "Male",
        "allergies": ["Penicillin"]
    }, headers=headers)
    assert pat_resp.status_code == 201

    # 3. Create session
    sess_resp = client.post("/api/clinical/sessions", json={
        "patient_id": pat_id,
        "raw_notes": ["Patient presents with retrosternal chest pain. cxr_path=data/mock_patients/patient_001_cxr.png"]
    }, headers=headers)
    assert sess_resp.status_code == 201
    session_id = sess_resp.json()["session_id"]

    # 4. Execute session (pauses at data_request_review due to missing HEART score components)
    run_resp = client.post(f"/api/clinical/sessions/{session_id}/run", headers=headers)
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["status"] == "WAITING_FOR_CLINICAL_DATA"
    assert run_data["next_node"] == "data_request_review"
    assert len(run_data["pending_requests"]) == 1

    req_id = run_data["pending_requests"][0]["request_id"]
    assert run_data["pending_requests"][0]["requesting_agent"] == "triage"

    # 5. Fetch pending requests via API
    get_reqs_resp = client.get(f"/api/clinical/sessions/{session_id}/data-requests", headers=headers)
    assert get_reqs_resp.status_code == 200
    pending_list = get_reqs_resp.json()
    assert len(pending_list) == 1
    assert pending_list[0]["request_id"] == req_id

    # 6. Test invalid input validation error (missing required history_score) -> 400 Bad Request
    invalid_resolve_resp = client.post(
        f"/api/clinical/sessions/{session_id}/data-requests/{req_id}/resolve",
        json={"response_data": {"ecg_score": 1}},
        headers=headers
    )
    assert invalid_resolve_resp.status_code == 400
    assert "Missing required clinical field" in invalid_resolve_resp.json()["detail"]

    # 7. Test valid resolution -> resumes execution directly at triage node and proceeds to human_review
    valid_resolve_resp = client.post(
        f"/api/clinical/sessions/{session_id}/data-requests/{req_id}/resolve",
        json={"response_data": {"history_score": 2, "ecg_score": 1, "troponin_score": 0, "cardiac_risk_factors_count": 2}},
        headers=headers
    )
    assert valid_resolve_resp.status_code == 200
    res_data = valid_resolve_resp.json()
    assert res_data["status"] == "WAITING_FOR_CLINICIAN_REVIEW"
    assert res_data["next_node"] == "human_review"

    # 8. Verify pending requests is now empty
    get_reqs_resp_after = client.get(f"/api/clinical/sessions/{session_id}/data-requests", headers=headers)
    assert get_reqs_resp_after.status_code == 200
    assert len(get_reqs_resp_after.json()) == 0
