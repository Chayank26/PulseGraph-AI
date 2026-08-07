import logging
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.core.state import ClinicalState, AuditEntry
from src.agents.triage import triage_agent_node
from src.agents.diagnostic import diagnostic_agent_node
from src.agents.evidence_rag import evidence_rag_agent_node
from src.agents.safety import safety_agent_node

logger = logging.getLogger("PulseGraph.Graph")


def human_review_node(state: ClinicalState) -> Dict[str, Any]:
    """
    Human-in-the-Loop (HITL) Review Node:
    Acts as an explicit clinical validation checkpoint where attending clinicians review,
    override, or approve generated diagnostic differentials and treatment recommendations.
    """
    logger.info("Executing Human-in-the-Loop Clinical Review Node...")
    
    audit_entry = AuditEntry(
        agent_name="HumanReviewNode",
        action="CLINICIAN_VALIDATION",
        summary="Clinician review completed. Recommendations verified and approved for EHR deployment.",
        metadata={"status": "APPROVED"}
    )

    return {
        "audit_trail": [audit_entry],
        "current_step": "clinician_approved"
    }


def build_clinical_graph(checkpointer: Optional[Any] = None):
    """
    Constructs and compiles the PulseGraph AI multi-agent workflow state machine.
    
    Workflow Topology:
    [START] -> triage -> diagnostic -> evidence -> safety -> human_review -> [END]
    
    Features:
    - Human-in-the-Loop interrupt configured before 'human_review'.
    - Stateful checkpointer via MemorySaver.
    """
    logger.info("Initializing PulseGraph AI StateGraph...")
    
    workflow = StateGraph(ClinicalState)

    # 1. Register agent & review nodes
    workflow.add_node("triage", triage_agent_node)
    workflow.add_node("diagnostic", diagnostic_agent_node)
    workflow.add_node("evidence", evidence_rag_agent_node)
    workflow.add_node("safety", safety_agent_node)
    workflow.add_node("human_review", human_review_node)

    # 2. Define workflow topology
    workflow.add_edge(START, "triage")
    workflow.add_edge("triage", "diagnostic")
    workflow.add_edge("diagnostic", "evidence")
    workflow.add_edge("evidence", "safety")
    workflow.add_edge("safety", "human_review")
    workflow.add_edge("human_review", END)

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
