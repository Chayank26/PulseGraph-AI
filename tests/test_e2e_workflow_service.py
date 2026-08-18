import uuid
import pytest
from src.db.repositories.doctor_repository import DoctorRepository
from src.db.repositories.patient_repository import PatientRepository
from src.db.repositories.session_repository import SessionRepository
from src.services.clinical_workflow import ClinicalWorkflowService
from src.core.state import ClinicianIdentity


def test_full_workflow_service_e2e_lifecycle(db_session):
    """End-to-end integration test of ClinicalWorkflowService with PostgreSQL persistence."""
    doc_repo = DoctorRepository(db_session)
    pat_repo = PatientRepository(db_session)
    sess_repo = SessionRepository(db_session)

    uid = uuid.uuid4().hex[:6]
    doc_id = f"DOC-WF-{uid}"
    pat_id = f"PAT-WF-{uid}"

    doc = doc_repo.create(doctor_id=doc_id, full_name="Dr. Workflow", department="ER", password="pass")
    pat = pat_repo.create(patient_id=pat_id, age=60, gender="Male")

    session_id = f"SESS-WF-{uid}"
    thread_id = f"thread-{session_id}"
    sess = sess_repo.create_session(
        session_id=session_id,
        patient_id=pat_id,
        doctor_id=doc_id,
        thread_id=thread_id,
        status="INITIALIZED",
        current_step="initialized"
    )

    workflow_service = ClinicalWorkflowService(db_session)

    # 1. Run Session (detects chest pain with missing HEART components -> pauses at data_request_review)
    res1 = workflow_service.run_session(
        session_id=session_id,
        raw_notes=["Patient presents with acute retrosternal chest pain. cxr_path=data/mock_patients/patient_001_cxr.png"]
    )

    assert res1["session_id"] == session_id
    assert res1["status"] == "WAITING_FOR_CLINICAL_DATA"
    assert res1["next_node"] == "data_request_review"
    assert len(res1["pending_requests"]) == 1
    req_id = res1["pending_requests"][0]["request_id"]

    # Verify DB persistence of data request and session status
    db_sess = sess_repo.get_by_session_id(session_id)
    assert db_sess.status == "WAITING_FOR_CLINICAL_DATA"
    pending_db_reqs = sess_repo.get_pending_data_requests(session_id)
    assert len(pending_db_reqs) == 1
    assert pending_db_reqs[0].request_id == req_id

    # 2. Resolve Data Request with clinician inputs
    res2 = workflow_service.resolve_data_request(
        session_id=session_id,
        request_id=req_id,
        response_data={"history_score": 2, "ecg_score": 1, "troponin_score": 0, "cardiac_risk_factors_count": 2}
    )

    assert res2["status"] == "WAITING_FOR_CLINICIAN_REVIEW"
    assert res2["next_node"] == "human_review"

    # Verify DB persistence of resolved request and CDS results
    resolved_db_reqs = sess_repo.get_pending_data_requests(session_id)
    assert len(resolved_db_reqs) == 0

    cds_result = sess_repo.get_cds_result(session_id)
    assert cds_result is not None
    assert len(cds_result.risk_scores) > 0

    # 3. Clinician Approves Recommendations
    clinician_identity = ClinicianIdentity(
        doctor_id=doc_id,
        full_name="Dr. Workflow",
        department="ER"
    )
    res3 = workflow_service.approve_session(session_id, clinician_identity, notes="Approved for PE protocol.")

    assert res3["status"] == "APPROVED"
    assert res3["current_step"] == "ehr_exported"

    # Final DB checks
    final_db_sess = sess_repo.get_by_session_id(session_id)
    assert final_db_sess.status == "APPROVED"
    assert final_db_sess.approved_at is not None
    assert final_db_sess.completed_at is not None
