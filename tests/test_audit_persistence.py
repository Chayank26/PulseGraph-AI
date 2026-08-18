import uuid
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_append_only_audit_log_persistence_e2e():
    """Integration test verifying append-only audit trail logging in PostgreSQL across entire workflow execution."""
    uid = uuid.uuid4().hex[:6]
    doc_id = f"DOC-AUDIT-{uid}"
    pat_id = f"PAT-AUDIT-{uid}"

    # 1. Register & authenticate doctor
    client.post("/api/doctors", json={"doctor_id": doc_id, "full_name": "Dr. Auditor", "department": "Cardiology", "password": "Password123!"})
    token = client.post("/api/auth/login", json={"doctor_id": doc_id, "password": "Password123!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create patient & session
    client.post("/api/patients", json={"patient_id": pat_id, "age": 62, "gender": "Male"}, headers=headers)
    sess_resp = client.post("/api/clinical/sessions", json={"patient_id": pat_id, "raw_notes": ["Patient with severe chest pain. cxr_path=data/mock_patients/patient_001_cxr.png"]}, headers=headers)
    session_id = sess_resp.json()["session_id"]

    # 3. Initial execution (pauses at data_request_review)
    run1 = client.post(f"/api/clinical/sessions/{session_id}/run", headers=headers)
    req_id = run1.json()["pending_requests"][0]["request_id"]

    # Fetch audit logs after stage 1
    audit1 = client.get(f"/api/clinical/sessions/{session_id}/audit-trail", headers=headers).json()
    count_stage1 = len(audit1)
    assert count_stage1 > 0
    actions_stage1 = [log["action"] for log in audit1]
    assert "CLINICAL_DATA_ACQUISITION" in actions_stage1 or "DATA_REQUEST_CREATED" in actions_stage1

    # 4. Resolve data request
    client.post(
        f"/api/clinical/sessions/{session_id}/data-requests/{req_id}/resolve",
        json={"response_data": {"history_score": 2, "ecg_score": 1, "troponin_score": 0, "cardiac_risk_factors_count": 2}},
        headers=headers
    )

    # Fetch audit logs after resolution (should contain all stage 1 logs PLUS new agent execution logs)
    audit2 = client.get(f"/api/clinical/sessions/{session_id}/audit-trail", headers=headers).json()
    count_stage2 = len(audit2)
    assert count_stage2 > count_stage1

    agents_logged = {log["agent_name"] for log in audit2}
    assert "ImagingAgent" in agents_logged or "DiagnosticAgent" in agents_logged or "SafetyAgent" in agents_logged

    # 5. Clinician approves session
    client.post(f"/api/clinical/sessions/{session_id}/approve", json={"notes": "Audit verification approved."}, headers=headers)

    # Fetch final audit trail
    audit3 = client.get(f"/api/clinical/sessions/{session_id}/audit-trail", headers=headers).json()
    count_stage3 = len(audit3)
    assert count_stage3 > count_stage2

    final_actions = [log["action"] for log in audit3]
    assert "CLINICIAN_VALIDATION" in final_actions
    assert "EHR_PACKAGE_EXPORT" in final_actions

    # Verify chronological ordering by timestamp
    timestamps = [log["timestamp"] for log in audit3]
    assert timestamps == sorted(timestamps)
