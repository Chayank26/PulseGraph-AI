import uuid
import pytest
from src.db.repositories.doctor_repository import DoctorRepository
from src.db.repositories.patient_repository import PatientRepository
from src.db.repositories.session_repository import SessionRepository
from src.services.clinical_workflow import ClinicalWorkflowService
from src.core.checkpointer import get_default_checkpointer
from src.core.graph import build_clinical_graph
from src.core.state import ClinicianIdentity


def test_postgres_checkpointer_reconstruction_and_thread_persistence(db_session):
    """
    Phase 16 Test:
    Verifies that Graph A executes until interrupt (data_request_review), Graph A is destroyed,
    Graph B is initialized from PostgresSaver checkpointer using the SAME thread_id,
    and Graph B resumes execution directly without restarting from START.
    """
    doc_repo = DoctorRepository(db_session)
    pat_repo = PatientRepository(db_session)
    sess_repo = SessionRepository(db_session)

    uid = uuid.uuid4().hex[:6]
    doc_id = f"DOC-PG-{uid}"
    pat_id = f"PAT-PG-{uid}"

    doc = doc_repo.create(doctor_id=doc_id, full_name="Dr. Postgres Checkpoint", department="ER", password="pass")
    pat = pat_repo.create(patient_id=pat_id, age=55, gender="Male")

    session_id = f"SESS-PG-{uid}"
    thread_id = f"thread-{session_id}"
    sess = sess_repo.create_session(
        session_id=session_id,
        patient_id=pat_id,
        doctor_id=doc_id,
        thread_id=thread_id,
        status="INITIALIZED",
        current_step="initialized"
    )

    # 1. Instantiate Workflow Service Instance A with PostgresSaver checkpointer
    postgres_checkpointer = get_default_checkpointer(force_backend="postgres")
    service_a = ClinicalWorkflowService(db_session, checkpointer=postgres_checkpointer)

    # Run session -> pauses at data_request_review breakpoint due to missing HEART score inputs
    res1 = service_a.run_session(
        session_id=session_id,
        raw_notes=["Patient presents with retrosternal chest pain. cxr_path=data/mock_patients/patient_001_cxr.png"]
    )
    assert res1["status"] == "WAITING_FOR_CLINICAL_DATA"
    assert res1["next_node"] == "data_request_review"
    assert len(res1["pending_requests"]) == 1
    req_id = res1["pending_requests"][0]["request_id"]

    # 2. SIMULATE BACKEND PROCESS RESTART:
    # Completely destroy Service A and Graph instance A
    del service_a

    # 3. Instantiate NEW Service Instance B with NEW Graph B compiled from PostgresSaver
    service_b = ClinicalWorkflowService(db_session, checkpointer=postgres_checkpointer)

    # Verify state snapshot in Graph B using the SAME thread_id
    thread_config = {"configurable": {"thread_id": thread_id}}
    snapshot_b = service_b.graph.get_state(thread_config)
    assert snapshot_b.next[0] == "data_request_review"
    assert len(snapshot_b.values["pending_data_requests"]) == 1
    assert snapshot_b.values["pending_data_requests"][0].request_id == req_id

    # 4. Resolve Data Request on Service Instance B
    res2 = service_b.resolve_data_request(
        session_id=session_id,
        request_id=req_id,
        response_data={"history_score": 2, "ecg_score": 1, "troponin_score": 0, "cardiac_risk_factors_count": 2}
    )
    assert res2["status"] == "WAITING_FOR_CLINICIAN_REVIEW"
    assert res2["next_node"] == "human_review"

    # 5. SIMULATE SECOND BACKEND RESTART AT HUMAN REVIEW BREAKPOINT:
    del service_b
    service_c = ClinicalWorkflowService(db_session, checkpointer=postgres_checkpointer)

    snapshot_c = service_c.graph.get_state(thread_config)
    assert snapshot_c.next[0] == "human_review"
    assert len(snapshot_c.values["differentials"]) > 0

    # 6. Clinician Approves on Service Instance C after process restart
    clinician_identity = ClinicianIdentity(doctor_id=doc_id, full_name="Dr. Postgres Checkpoint", department="ER")
    res3 = service_c.approve_session(session_id, clinician_identity, notes="Approved after restart.")

    assert res3["status"] == "APPROVED"
    assert res3["current_step"] == "ehr_exported"
