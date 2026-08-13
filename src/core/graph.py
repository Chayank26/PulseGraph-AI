import logging
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.core.state import ClinicalState, AuditEntry
from src.core.data_requests import get_pending_requests
from src.agents.triage import triage_agent_node
from src.agents.imaging import imaging_agent_node
from src.agents.diagnostic import diagnostic_agent_node
from src.agents.evidence_rag import evidence_rag_agent_node
from src.agents.safety import safety_agent_node
from src.agents.symbolic_guardrail import symbolic_guardrail_agent_node

logger = logging.getLogger("PulseGraph.Graph")

MAX_ITERATIONS = 2


def human_review_node(state: ClinicalState) -> Dict[str, Any]:
    """
    Human-in-the-Loop (HITL) Review Node:
    Acts as an explicit clinical validation checkpoint where attending clinicians review,
    override, or approve generated diagnostic differentials, imaging reports, safety alerts,
    and deterministic symbolic overrides.
    """
    logger.info("Executing Human-in-the-Loop Clinical Review Node...")
    
    clinician = state.get("authenticated_clinician")
    approved = state.get("approved_by_clinician")
    notes = state.get("clinician_notes")
    re_eval = state.get("re_evaluation_requested", False)

    status_str = "APPROVED" if approved is True else ("RE_EVALUATION_REQUESTED" if re_eval else "REJECTED_MANUAL_TAKEOVER")
    doctor_name = clinician.full_name if clinician else "Attending Clinician"
    doctor_id = clinician.doctor_id if clinician else "DOC-UNKNOWN"

    summary_text = (
        f"Clinician review completed by {doctor_name} ({doctor_id}). Status: {status_str}."
    )
    if notes:
        summary_text += f" Notes: {notes}"

    audit_entry = AuditEntry(
        agent_name="HumanReviewNode",
        action="CLINICIAN_VALIDATION",
        summary=summary_text,
        metadata={
            "status": status_str,
            "doctor_id": doctor_id,
            "doctor_name": doctor_name,
            "approved": approved,
            "re_evaluation_requested": re_eval
        }
    )

    return {
        "audit_trail": [audit_entry],
        "current_step": f"clinician_{status_str.lower()}"
    }


def data_request_review_node(state: ClinicalState) -> Dict[str, Any]:
    """
    Data Request Review Node:
    Explicit pause/checkpoint node executed when clinical agents require additional
    patient information before completing analysis.
    """
    logger.info("Executing Clinical Data Request Review Node...")
    pending = get_pending_requests(state)
    req_summary = f"Pending clinical data requests: {len(pending)}" if pending else "Clinical data acquisition resolved."

    audit_entry = AuditEntry(
        agent_name="DataRequestReviewNode",
        action="CLINICAL_DATA_ACQUISITION",
        summary=req_summary,
        metadata={"pending_count": len(pending)}
    )

    return {
        "audit_trail": [audit_entry],
        "current_step": "data_request_processed"
    }


def ehr_export_node(state: ClinicalState) -> Dict[str, Any]:
    """
    EHR Export Node:
    Final node executed upon clinician approval to export verified recommendations to EHR.
    """
    logger.info("Executing EHR Export Node...")
    clinician = state.get("authenticated_clinician")
    doc_id = clinician.doctor_id if clinician else "SYSTEM"

    audit_entry = AuditEntry(
        agent_name="EHRExportNode",
        action="EHR_PACKAGE_EXPORT",
        summary=f"Clinical decision support package successfully approved by {doc_id} and exported to EHR.",
        metadata={"export_status": "SUCCESS"}
    )
    return {
        "audit_trail": [audit_entry],
        "current_step": "ehr_exported"
    }


def feedback_processor_node(state: ClinicalState) -> Dict[str, Any]:
    """
    Feedback Processor Node:
    Processes physician feedback notes, increments iteration count, and prepares state
    for re-evaluation loop back to the diagnostic node.
    """
    current_count = state.get("iteration_count", 0) + 1
    notes = state.get("clinician_notes", "")
    clinician = state.get("authenticated_clinician")
    doctor_id = clinician.doctor_id if clinician else "DOC-UNKNOWN"

    logger.info(f"Processing clinician feedback for iteration {current_count}/{MAX_ITERATIONS}. Doctor: {doctor_id}")

    feedback_text = f"[PHYSICIAN FEEDBACK - LOOP {current_count} by {doctor_id}]: {notes}"

    audit_entry = AuditEntry(
        agent_name="FeedbackProcessorNode",
        action="FEEDBACK_RE_EVALUATION",
        summary=f"Feedback loop {current_count}/{MAX_ITERATIONS} initiated by {doctor_id}. Re-analyzing differentials.",
        metadata={"iteration_count": current_count, "notes": notes}
    )

    return {
        "iteration_count": current_count,
        "raw_notes": [feedback_text],
        "re_evaluation_requested": False,
        "audit_trail": [audit_entry],
        "current_step": f"re_evaluation_loop_{current_count}"
    }


def _check_data_request_routing(state: ClinicalState, default_next_node: str) -> str:
    """Helper router checking if pending data requests exist after an agent node."""
    pending = get_pending_requests(state)
    if pending:
        iteration_count = state.get("iteration_count", 0)
        if iteration_count < MAX_ITERATIONS * 3:
            logger.info(f"Pending ClinicalDataRequest detected ({pending[0].request_id}). Routing to 'data_request_review'.")
            return "data_request_review"
        else:
            logger.warning(f"Data request loop hit iteration safety limit. Routing to END.")
            return END
    return default_next_node


def route_after_triage(state: ClinicalState) -> str:
    return _check_data_request_routing(state, "imaging")


def route_after_imaging(state: ClinicalState) -> str:
    return _check_data_request_routing(state, "diagnostic")


def route_after_diagnostic(state: ClinicalState) -> str:
    return _check_data_request_routing(state, "evidence")


def route_after_safety(state: ClinicalState) -> str:
    return _check_data_request_routing(state, "symbolic_guardrail")


def route_after_symbolic_guardrail(state: ClinicalState) -> str:
    return _check_data_request_routing(state, "human_review")


def route_after_data_request_review(state: ClinicalState) -> str:
    """
    Conditional routing executed after clinician resolves data acquisition request.
    Routes execution DIRECTLY BACK to the requesting agent node.
    """
    all_requests = state.get("pending_data_requests", []) + state.get("resolved_data_requests", [])
    if all_requests:
        last_req = all_requests[-1]
        agent_node = last_req.requesting_agent
        if agent_node in ["triage", "imaging", "diagnostic", "evidence", "safety", "symbolic_guardrail"]:
            logger.info(f"Data request resolved. Resuming execution directly at requesting agent node '{agent_node}'.")
            return agent_node
    logger.info("Resuming execution at default node 'triage'.")
    return "triage"


def route_after_review(state: ClinicalState) -> str:
    """
    Conditional routing function executed after human_review node.
    - If approved_by_clinician == True -> ehr_export
    - If approved_by_clinician == False AND re_evaluation_requested == True:
        - If iteration_count < MAX_ITERATIONS -> feedback_processor (which routes to diagnostic)
        - If iteration_count >= MAX_ITERATIONS -> END (max iteration safety cutoff)
    - Otherwise -> END (manual takeover)
    """
    approved = state.get("approved_by_clinician")
    re_eval = state.get("re_evaluation_requested", False)
    iteration_count = state.get("iteration_count", 0)

    if approved is True:
        logger.info("Clinician APPROVED plan. Routing to 'ehr_export'.")
        return "ehr_export"

    if approved is False and re_eval:
        if iteration_count < MAX_ITERATIONS:
            logger.info(f"Re-evaluation requested (iteration {iteration_count + 1}/{MAX_ITERATIONS}). Routing to 'feedback_processor'.")
            return "feedback_processor"
        else:
            logger.warning(f"Re-evaluation loop reached MAX_ITERATIONS cutoff ({MAX_ITERATIONS}). Terminating graph for manual takeover.")
            return END

    logger.info("Clinician REJECTED plan or manual takeover initiated. Terminating graph.")
    return END


def build_clinical_graph(checkpointer: Optional[Any] = None):
    """
    Constructs and compiles the PulseGraph AI Neuro-Symbolic multi-agent workflow state machine.
    
    Workflow Topology:
    [START] -> triage -> imaging -> diagnostic -> evidence -> safety -> symbolic_guardrail -> human_review
               │          │          │                          │          │                    │
               ▼          ▼          ▼                          ▼          ▼                    ▼
        [data_request_review] ◄─────────────────────────────────────────────────────────────────┘
               │
               ▼ (Resumes directly at requesting agent node e.g. triage/diagnostic/safety)
    """
    logger.info("Initializing PulseGraph AI Neuro-Symbolic StateGraph with Data Acquisition & HITL Routing...")
    
    workflow = StateGraph(ClinicalState)

    # 1. Register agent, review, data request, export, and feedback nodes
    workflow.add_node("triage", triage_agent_node)
    workflow.add_node("imaging", imaging_agent_node)
    workflow.add_node("diagnostic", diagnostic_agent_node)
    workflow.add_node("evidence", evidence_rag_agent_node)
    workflow.add_node("safety", safety_agent_node)
    workflow.add_node("symbolic_guardrail", symbolic_guardrail_agent_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("ehr_export", ehr_export_node)
    workflow.add_node("feedback_processor", feedback_processor_node)
    workflow.add_node("data_request_review", data_request_review_node)

    # 2. Define workflow topology
    workflow.add_edge(START, "triage")

    # Conditional data request routing after each agent node
    workflow.add_conditional_edges("triage", route_after_triage, {"data_request_review": "data_request_review", "imaging": "imaging", END: END})
    workflow.add_conditional_edges("imaging", route_after_imaging, {"data_request_review": "data_request_review", "diagnostic": "diagnostic", END: END})
    workflow.add_conditional_edges("diagnostic", route_after_diagnostic, {"data_request_review": "data_request_review", "evidence": "evidence", END: END})
    workflow.add_edge("evidence", "safety")
    workflow.add_conditional_edges("safety", route_after_safety, {"data_request_review": "data_request_review", "symbolic_guardrail": "symbolic_guardrail", END: END})
    workflow.add_conditional_edges("symbolic_guardrail", route_after_symbolic_guardrail, {"data_request_review": "data_request_review", "human_review": "human_review", END: END})

    # Resumption routing from data_request_review back to requesting agent
    workflow.add_conditional_edges(
        "data_request_review",
        route_after_data_request_review,
        {
            "triage": "triage",
            "imaging": "imaging",
            "diagnostic": "diagnostic",
            "evidence": "evidence",
            "safety": "safety",
            "symbolic_guardrail": "symbolic_guardrail",
            "human_review": "human_review",
            END: END
        }
    )

    # Feedback loop routing back to diagnostic
    workflow.add_edge("feedback_processor", "diagnostic")
    workflow.add_edge("ehr_export", END)

    # Conditional routing after human review
    workflow.add_conditional_edges(
        "human_review",
        route_after_review,
        {
            "ehr_export": "ehr_export",
            "feedback_processor": "feedback_processor",
            END: END
        }
    )

    # 3. Default checkpointer to MemorySaver if not provided
    if checkpointer is None:
        checkpointer = MemorySaver()

    # 4. Compile with checkpointer & HITL interrupts
    compiled_graph = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review", "data_request_review"]
    )
    logger.info("PulseGraph AI StateGraph compiled successfully with interrupt_before=['human_review', 'data_request_review'].")
    
    return compiled_graph


