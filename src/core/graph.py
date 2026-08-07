import logging
from langgraph.graph import StateGraph, START, END
from src.core.state import ClinicalState
from src.agents.triage import triage_agent_node
from src.agents.diagnostic import diagnostic_agent_node
from src.agents.evidence_rag import evidence_rag_agent_node
from src.agents.safety import safety_agent_node

logger = logging.getLogger("PulseGraph.Graph")


def build_clinical_graph():
    """
    Constructs and compiles the PulseGraph AI multi-agent workflow state machine.
    
    Workflow Topology:
    [START] -> triage -> diagnostic -> evidence_rag -> safety -> [END]
    """
    logger.info("Initializing PulseGraph AI StateGraph...")
    
    workflow = StateGraph(ClinicalState)

    # 1. Register agent nodes
    workflow.add_node("triage", triage_agent_node)
    workflow.add_node("diagnostic", diagnostic_agent_node)
    workflow.add_node("evidence_rag", evidence_rag_agent_node)
    workflow.add_node("safety", safety_agent_node)

    # 2. Define edge sequence
    workflow.add_edge(START, "triage")
    workflow.add_edge("triage", "diagnostic")
    workflow.add_edge("diagnostic", "evidence_rag")
    workflow.add_edge("evidence_rag", "safety")
    workflow.add_edge("safety", END)

    # 3. Compile graph
    compiled_graph = workflow.compile()
    logger.info("PulseGraph AI StateGraph compiled successfully.")
    
    return compiled_graph
