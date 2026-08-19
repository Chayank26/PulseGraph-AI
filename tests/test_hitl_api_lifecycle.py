import uuid
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_hitl_api_review_approval_lifecycle():
    """Integration test verifying HITL review package fetch, clinician approval, and EHR export persistence."""
    uid = uuid.uuid4().hex[:6]
    doc_id = f"DOC-HITL-{uid}"
    pat_id = f"PAT-HITL-{uid}"

    # Register and authenticate doctor
    client.post("/api/doctors", json={"doctor_id": doc_id, "full_name": "Dr. HITL Reviewer", "department": "ICU", "password": "Password123!", "role": "Attending Physician"})
    login_resp = client.post("/api/auth/login", json={"doctor_id": doc_id, "password": "Password123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create patient & session
    client.post("/api/patients", json={"patient_id": pat_id, "age": 50, "gender": "Female"}, headers=headers)
    sess_resp = client.post("/api/clinical/sessions", json={"patient_id": pat_id, "raw_notes": ["Patient with chest pain. cxr_path=data/mock_patients/patient_001_cxr.png, history_score=2, ecg_score=1, troponin_score=0, cardiac_risk_factors_count=2"]}, headers=headers)
    session_id = sess_resp.json()["session_id"]

    # Execute workflow (runs directly to human_review breakpoint since no missing data requests are created)
    run_resp = client.post(f"/api/clinical/sessions/{session_id}/run", headers=headers)
    assert run_resp.status_code == 200
    assert run_resp.json()["status"] == "WAITING_FOR_CLINICIAN_REVIEW"
    assert run_resp.json()["next_node"] == "human_review"

    # Fetch review package
    review_resp = client.get(f"/api/clinical/sessions/{session_id}/review", headers=headers)
    assert review_resp.status_code == 200
    rev_data = review_resp.json()
    assert rev_data["session_id"] == session_id
    assert len(rev_data["differentials"]) > 0

    # Clinician approves session
    approve_resp = client.post(
        f"/api/clinical/sessions/{session_id}/approve",
        json={"notes": "Differentials and safety checks verified. Approved."},
        headers=headers
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "APPROVED"
    assert approve_resp.json()["current_step"] == "ehr_exported"

    # Check persistent CDS results
    res_resp = client.get(f"/api/clinical/sessions/{session_id}/results", headers=headers)
    assert res_resp.status_code == 200
    assert res_resp.json()["clinician_approval"]["approved"] is True


def test_hitl_reevaluation_loop_and_max_iterations():
    """Integration test verifying clinician re-evaluation loop, iteration counter, and MAX_ITERATIONS cutoff."""
    uid = uuid.uuid4().hex[:6]
    doc_id = f"DOC-REEVAL-{uid}"
    pat_id = f"PAT-REEVAL-{uid}"

    client.post("/api/doctors", json={"doctor_id": doc_id, "full_name": "Dr. Reeval", "department": "ER", "password": "Password123!"})
    login_resp = client.post("/api/auth/login", json={"doctor_id": doc_id, "password": "Password123!"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/patients", json={"patient_id": pat_id, "age": 45, "gender": "Male"}, headers=headers)
    sess_resp = client.post("/api/clinical/sessions", json={"patient_id": pat_id, "raw_notes": ["Patient with chest pain. cxr_path=data/mock_patients/patient_001_cxr.png, history_score=2, ecg_score=1, troponin_score=0, cardiac_risk_factors_count=2"]}, headers=headers)
    session_id = sess_resp.json()["session_id"]

    client.post(f"/api/clinical/sessions/{session_id}/run", headers=headers)

    # 1st Re-evaluation loop
    reeval1_resp = client.post(
        f"/api/clinical/sessions/{session_id}/reevaluate",
        json={"notes": "Please re-analyze chest X-ray findings for pneumothorax."},
        headers=headers
    )
    assert reeval1_resp.status_code == 200
    assert reeval1_resp.json()["iteration_count"] == 1

    # 2nd Re-evaluation loop (reaches MAX_ITERATIONS limit of 2)
    reeval2_resp = client.post(
        f"/api/clinical/sessions/{session_id}/reevaluate",
        json={"notes": "Consider pulmonary embolism in differential."},
        headers=headers
    )
    assert reeval2_resp.status_code == 200
    assert reeval2_resp.json()["iteration_count"] == 2

    # 3rd Re-evaluation attempt triggers MAX_ITERATIONS cutoff (terminates graph safely to END)
    reeval3_resp = client.post(
        f"/api/clinical/sessions/{session_id}/reevaluate",
        json={"notes": "Third loop attempt."},
        headers=headers
    )
    assert reeval3_resp.status_code == 200
    assert reeval3_resp.json()["next_node"] is None  # Graph terminated for manual takeover


def test_hitl_rejection_manual_takeover():
    """Integration test verifying clinician rejection / manual clinical takeover."""
    uid = uuid.uuid4().hex[:6]
    doc_id = f"DOC-REJ-{uid}"
    pat_id = f"PAT-REJ-{uid}"

    client.post("/api/doctors", json={"doctor_id": doc_id, "full_name": "Dr. Reject", "department": "Surgery", "password": "Password123!"})
    token = client.post("/api/auth/login", json={"doctor_id": doc_id, "password": "Password123!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/patients", json={"patient_id": pat_id, "age": 70, "gender": "Female"}, headers=headers)
    session_id = client.post("/api/clinical/sessions", json={"patient_id": pat_id, "raw_notes": ["Patient with chest pain. cxr_path=data/mock_patients/patient_001_cxr.png, history_score=2, ecg_score=1, troponin_score=0, cardiac_risk_factors_count=2"]}, headers=headers).json()["session_id"]
    client.post(f"/api/clinical/sessions/{session_id}/run", headers=headers)

    reject_resp = client.post(
        f"/api/clinical/sessions/{session_id}/reject",
        json={"notes": "Patient requires immediate surgical intervention."},
        headers=headers
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "REJECTED_MANUAL_TAKEOVER"
