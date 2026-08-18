import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.main import app
from config.settings import settings
from src.db.models import ClinicalSessionModel, ClinicalDataRequestModel, AuditLogModel, CDSResultModel, PatientModel, DoctorModel

client = TestClient(app)


def test_master_e2e_system_flow():
    """
    Complete Master End-to-End System Test satisfying Phase 13 requirements:
    1. Register Doctor -> 2. Login -> 3. Create Dynamic Patient -> 4. Create Session ->
    5. Run Graph -> 6. Detect Data Request -> 7. Resolve Request -> 8. Resume Graph ->
    9. Reach HITL Review -> 10. Clinician Approval -> 11. EHR Export ->
    12. Verify PostgreSQL Database Persistence.
    """
    uid = uuid.uuid4().hex[:6]
    doc_id = f"DOC-E2E-{uid}"
    pat_id = f"PAT-E2E-{uid}"

    # 1. Register Doctor
    reg_resp = client.post("/api/doctors", json={
        "doctor_id": doc_id,
        "full_name": "Dr. Master E2E Physician",
        "department": "Emergency Medicine",
        "password": "MasterSecurePassword123!",
        "role": "Attending Physician"
    })
    assert reg_resp.status_code == 201

    # 2. Doctor Login
    login_resp = client.post("/api/auth/login", json={"doctor_id": doc_id, "password": "MasterSecurePassword123!"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create Dynamic Patient
    pat_resp = client.post("/api/patients", json={
        "patient_id": pat_id,
        "age": 67,
        "gender": "Female",
        "blood_type": "B+",
        "allergies": ["Sulfa Drugs"],
        "chronic_conditions": ["Diabetes Mellitus Type 2", "Hypertension"],
        "current_medications": ["Metformin 500mg", "Amlodipine 5mg"]
    }, headers=headers)
    assert pat_resp.status_code == 201

    # 4. Create Clinical Session
    sess_resp = client.post("/api/clinical/sessions", json={
        "patient_id": pat_id,
        "raw_notes": ["Patient presents with acute chest pain and shortness of breath. cxr_path=data/mock_patients/patient_001_cxr.png"]
    }, headers=headers)
    assert sess_resp.status_code == 201
    session_id = sess_resp.json()["session_id"]

    # 5. Run Graph (Detects missing HEART score inputs -> pauses at data_request_review)
    run_resp = client.post(f"/api/clinical/sessions/{session_id}/run", headers=headers)
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["status"] == "WAITING_FOR_CLINICAL_DATA"
    assert len(run_data["pending_requests"]) == 1
    req_id = run_data["pending_requests"][0]["request_id"]

    # 6. Fetch & Resolve Data Request
    get_reqs = client.get(f"/api/clinical/sessions/{session_id}/data-requests", headers=headers)
    assert get_reqs.status_code == 200
    assert len(get_reqs.json()) == 1

    resolve_resp = client.post(
        f"/api/clinical/sessions/{session_id}/data-requests/{req_id}/resolve",
        json={"response_data": {"history_score": 2, "ecg_score": 1, "troponin_score": 0, "cardiac_risk_factors_count": 2}},
        headers=headers
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "WAITING_FOR_CLINICIAN_REVIEW"

    # 7. Fetch Review Package
    rev_resp = client.get(f"/api/clinical/sessions/{session_id}/review", headers=headers)
    assert rev_resp.status_code == 200
    assert len(rev_resp.json()["differentials"]) > 0

    # 8. Approve Session
    approve_resp = client.post(
        f"/api/clinical/sessions/{session_id}/approve",
        json={"notes": "E2E Master Verification Passed. Approved for discharge."},
        headers=headers
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "APPROVED"
    assert approve_resp.json()["current_step"] == "ehr_exported"

    # 9. Verify PostgreSQL Database Records directly via SQLAlchemy
    engine = create_engine(settings.database_url)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        db_doc = db.query(DoctorModel).filter(DoctorModel.doctor_id == doc_id).first()
        assert db_doc is not None

        db_pat = db.query(PatientModel).filter(PatientModel.patient_id == pat_id).first()
        assert db_pat is not None
        assert db_pat.age == 67

        db_sess = db.query(ClinicalSessionModel).filter(ClinicalSessionModel.session_id == session_id).first()
        assert db_sess is not None
        assert db_sess.status == "APPROVED"
        assert db_sess.approved_at is not None

        db_cds = db.query(CDSResultModel).filter(CDSResultModel.session_id == session_id).first()
        assert db_cds is not None
        assert db_cds.final_status == "APPROVED"
        assert db_cds.clinician_approval["approved"] is True

        db_audits = db.query(AuditLogModel).filter(AuditLogModel.session_id == session_id).all()
        assert len(db_audits) > 0
    finally:
        db.close()
