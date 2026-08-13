import pytest
from src.core.state import ClinicalState, PatientDemographics, VitalSigns, ClinicianIdentity, SymbolicOverrideFlag
from src.core.graph import build_clinical_graph, MAX_ITERATIONS


@pytest.fixture
def initial_test_state() -> ClinicalState:
    demographics = PatientDemographics(
        patient_id="PAT-TEST-001",
        age=62,
        gender="Female",
        allergies=["Penicillin"],
        chronic_conditions=["Hypertension"],
        current_medications=["Metoprolol 25mg daily"]
    )
    vitals = VitalSigns(
        heart_rate_bpm=45.0,
        blood_pressure_sys=130.0,
        blood_pressure_dia=80.0,
        temperature_c=36.8,
        respiratory_rate=20.0,
        spo2_percent=94.0
    )
    return {
        "patient_id": demographics.patient_id,
        "demographics": demographics,
        "raw_notes": ["Patient presenting with shortness of breath."],
        "vitals": vitals,
        "risk_scores": [],
        "differentials": [],
        "imaging_data": None,
        "safety_flags": [],
        "symbolic_overrides": [],
        "evidence": [],
        "audit_trail": [],
        "current_step": "initialized",
        "error_logs": [],
        "authenticated_clinician": None,
        "approved_by_clinician": None,
        "iteration_count": 0,
        "re_evaluation_requested": False,
        "clinician_notes": None
    }


def test_hitl_approval_flow(initial_test_state):
    """Test approval flow routes to ehr_export node."""
    graph = build_clinical_graph()
    config = {"configurable": {"thread_id": "test_hitl_approval"}}

    # Stage 1: Pause before human_review
    graph.invoke(initial_test_state, config=config)
    snapshot = graph.get_state(config)
    assert snapshot.next == ("human_review",)

    clinician = ClinicianIdentity(
        doctor_id="DOC-88204",
        full_name="Dr. Sarah Chen",
        department="Emergency Medicine"
    )

    # Stage 2: Update state with approval and resume
    graph.update_state(
        config,
        {
            "authenticated_clinician": clinician,
            "approved_by_clinician": True,
            "re_evaluation_requested": False
        }
    )
    graph.invoke(None, config=config)
    final_snapshot = graph.get_state(config)

    assert final_snapshot.values["approved_by_clinician"] is True
    assert final_snapshot.values["current_step"] == "ehr_exported"
    
    # Verify audit entry has doctor attribution
    audit_agents = [a.agent_name for a in final_snapshot.values["audit_trail"]]
    assert "EHRExportNode" in audit_agents


def test_hitl_re_evaluation_loop(initial_test_state):
    """Test rejection with re-evaluation request increments iteration_count and loops."""
    graph = build_clinical_graph()
    config = {"configurable": {"thread_id": "test_hitl_reeval"}}

    # Stage 1
    graph.invoke(initial_test_state, config=config)
    snapshot = graph.get_state(config)
    assert snapshot.next == ("human_review",)

    clinician = ClinicianIdentity(
        doctor_id="DOC-88204",
        full_name="Dr. Sarah Chen",
        department="Emergency Medicine"
    )

    # Stage 2: Reject & re-evaluate
    graph.update_state(
        config,
        {
            "authenticated_clinician": clinician,
            "approved_by_clinician": False,
            "re_evaluation_requested": True,
            "clinician_notes": "Please evaluate Pulmonary Embolism again with lower risk threshold."
        }
    )
    graph.invoke(None, config=config)
    
    # Should loop back and hit human_review again
    snapshot2 = graph.get_state(config)
    assert snapshot2.next == ("human_review",)
    assert snapshot2.values["iteration_count"] == 1
    assert any("PHYSICIAN FEEDBACK - LOOP 1" in note for note in snapshot2.values["raw_notes"])


def test_max_iteration_cutoff(initial_test_state):
    """Test graph force-terminates when iteration_count reaches MAX_ITERATIONS."""
    graph = build_clinical_graph()
    config = {"configurable": {"thread_id": "test_hitl_max_iter"}}

    graph.invoke(initial_test_state, config=config)

    clinician = ClinicianIdentity(
        doctor_id="DOC-88204",
        full_name="Dr. Sarah Chen",
        department="Emergency Medicine"
    )

    # Loop 1
    graph.update_state(
        config,
        {
            "authenticated_clinician": clinician,
            "approved_by_clinician": False,
            "re_evaluation_requested": True,
            "clinician_notes": "Loop 1 feedback"
        }
    )
    graph.invoke(None, config=config)

    # Loop 2
    graph.update_state(
        config,
        {
            "authenticated_clinician": clinician,
            "approved_by_clinician": False,
            "re_evaluation_requested": True,
            "clinician_notes": "Loop 2 feedback"
        }
    )
    graph.invoke(None, config=config)

    # Attempt Loop 3 (Exceeds MAX_ITERATIONS = 2)
    graph.update_state(
        config,
        {
            "authenticated_clinician": clinician,
            "approved_by_clinician": False,
            "re_evaluation_requested": True,
            "clinician_notes": "Loop 3 feedback"
        }
    )
    graph.invoke(None, config=config)

    final_snapshot = graph.get_state(config)
    # Graph should now be terminated (no next node)
    assert not final_snapshot.next


def test_candidate_rule_attribution(initial_test_state):
    """Test candidate SymbolicOverrideFlag authored by physician has proper attribution."""
    clinician = ClinicianIdentity(
        doctor_id="DOC-88204",
        full_name="Dr. Sarah Chen",
        department="Emergency Medicine"
    )

    flag = SymbolicOverrideFlag(
        rule_id="CANDIDATE_RULE_001",
        severity="CRITICAL_OVERRIDE",
        message="Manual takeover rule",
        deterministic_rule="IF HR < 50 THEN HOLD Metoprolol",
        action_required="Hold dose",
        authored_by=clinician,
        governance_status="PENDING_PEER_REVIEW",
        originating_patient_id="PAT-TEST-001"
    )

    assert flag.authored_by.doctor_id == "DOC-88204"
    assert flag.authored_by.full_name == "Dr. Sarah Chen"
    assert flag.governance_status == "PENDING_PEER_REVIEW"
    assert flag.originating_patient_id == "PAT-TEST-001"


def test_data_request_interrupt_and_resume(initial_test_state):
    """Test that creating a ClinicalDataRequest pauses graph at data_request_review and resumes directly to requesting agent."""
    from src.core.data_requests import create_data_request, resolve_request
    from src.core.state import ClinicalFieldRequirement

    graph = build_clinical_graph()
    config = {"configurable": {"thread_id": "test_data_req_interrupt"}}

    req = create_data_request(
        requesting_agent="triage",
        pathway_name="HEART Score Assessment",
        reason="Missing troponin score",
        required_fields=[
            ClinicalFieldRequirement(field_key="troponin_score", label="Troponin Score", data_type="int")
        ]
    )

    # State has a pending data request
    initial_test_state["pending_data_requests"] = [req]

    # Graph invocation should pause at data_request_review
    graph.invoke(initial_test_state, config=config)
    snapshot = graph.get_state(config)
    assert snapshot.next == ("data_request_review",)

    # Clinician supplies data and resolves request
    resolved = resolve_request(req, {"troponin_score": 0})
    graph.update_state(
        config,
        {
            "pending_data_requests": [resolved],
            "resolved_data_requests": [resolved]
        }
    )


    # Resuming graph should route to human_review (after running triage -> imaging -> diagnostic -> evidence -> safety -> symbolic)
    graph.invoke(None, config=config)
    snapshot2 = graph.get_state(config)
    assert snapshot2.next == ("human_review",)
    assert snapshot2.values["current_step"] == "symbolic_guardrails_evaluated"



