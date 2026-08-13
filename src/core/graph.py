import logging
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.core.state import ClinicalState, AuditEntry
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
               │                                                                                │
               │                                      ┌─────────────────────────────────────────┴───────────────┐
               │                                      ▼                                 ▼                       ▼
               │                            [feedback_processor]                  [ehr_export]                [END]
               └──────────────────────────────────────┘                                 │
                                                                                        ▼
                                                                                      [END]
    """
    logger.info("Initializing PulseGraph AI Neuro-Symbolic StateGraph with HITL Re-evaluation Routing...")
    
    workflow = StateGraph(ClinicalState)

    # 1. Register agent, review, export, and feedback nodes
    workflow.add_node("triage", triage_agent_node)
    workflow.add_node("imaging", imaging_agent_node)
    workflow.add_node("diagnostic", diagnostic_agent_node)
    workflow.add_node("evidence", evidence_rag_agent_node)
    workflow.add_node("safety", safety_agent_node)
    workflow.add_node("symbolic_guardrail", symbolic_guardrail_agent_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("ehr_export", ehr_export_node)
    workflow.add_node("feedback_processor", feedback_processor_node)

    # 2. Define workflow topology
    workflow.add_edge(START, "triage")
    workflow.add_edge("triage", "imaging")
    workflow.add_edge("imaging", "diagnostic")
    workflow.add_edge("diagnostic", "evidence")
    workflow.add_edge("evidence", "safety")
    workflow.add_edge("safety", "symbolic_guardrail")
    workflow.add_edge("symbolic_guardrail", "human_review")

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

    # 4. Compile with checkpointer & HITL interrupt
    compiled_graph = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"]
    )
    logger.info("PulseGraph AI StateGraph compiled successfully with HITL interrupt_before=['human_review'].")
    
    return compiled_graph

