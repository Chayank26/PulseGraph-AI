import os
import json
import logging
from pprint import pprint

from config.settings import settings
from src.core.state import ClinicalState, PatientDemographics, VitalSigns
from src.core.graph import build_clinical_graph

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("PulseGraph.Main")


def load_mock_patient():
    """Utility to load mock patient data for Phase 2 execution test."""
    notes_path = os.path.join("data", "mock_patients", "patient_001_notes.txt")

    raw_notes = []
    if os.path.exists(notes_path):
        with open(notes_path, "r") as f:
            raw_notes.append(f.read())

    demographics = PatientDemographics(
        patient_id="PAT-88291",
        age=58,
        gender="Male",
        blood_type="A+",
        allergies=["Penicillin"],
        chronic_conditions=["Hypertension", "Recent Right Knee Surgery"],
        current_medications=["Warfarin 5mg daily", "Ibuprofen 400mg PRN"]
    )

    vitals = VitalSigns(
        heart_rate_bpm=108.0,
        blood_pressure_sys=135.0,
        blood_pressure_dia=85.0,
        temperature_c=37.1,
        respiratory_rate=22.0,
        spo2_percent=91.0
    )

    return demographics, vitals, raw_notes


def main():
    logger.info("=== Starting PulseGraph AI Phase 2 HITL Execution Verification ===")
    
    # 1. Load patient state
    demographics, vitals, raw_notes = load_mock_patient()
    
    initial_state: ClinicalState = {
        "patient_id": demographics.patient_id,
        "demographics": demographics,
        "raw_notes": raw_notes,
        "vitals": vitals,
        "risk_scores": [],
        "differentials": [],
        "safety_flags": [],
        "evidence": [],
        "audit_trail": [],
        "current_step": "initialized",
        "error_logs": []
    }

    # 2. Build graph with stateful MemorySaver & HITL interrupt
    graph = build_clinical_graph()
    thread_config = {"configurable": {"thread_id": "session_pat_88291"}}

    # 3. Stage 1 Execution: Automated Agent Workflow (Pauses before 'human_review')
    logger.info("Executing Stage 1: Running automated agent workflow until HITL breakpoint...")
    graph.invoke(initial_state, config=thread_config)
    
    # 4. Checkpoint State Inspection at Breakpoint
    snapshot = graph.get_state(thread_config)
    paused_state = snapshot.values
    logger.info(f"Graph execution paused at breakpoint! Next step pending: {snapshot.next}")

    print("\n" + "="*65)
    print("      PULSEGRAPH AI CLINICAL DECISION SUPPORT - HITL AUDIT")
    print("="*65)
    print(f"\n[PATIENT ID]: {paused_state['patient_id']} | Thread ID: session_pat_88291")
    print(f"Demographics: Age {demographics.age}, {demographics.gender} | Allergies: {demographics.allergies}")
    
    print("\n--- CALCULATED RISK SCORES ---")
    for score in paused_state["risk_scores"]:
        print(f"• {score.score_name}: {score.value} {score.unit or ''} -> {score.interpretation}")

    print("\n--- DIAGNOSTIC DIFFERENTIALS ---")
    for diff in paused_state["differentials"]:
        print(f"• [{diff.likelihood}] {diff.condition_name} (ICD: {diff.icd10_code})")
        print(f"  Rationale: {diff.rationale}")
        print(f"  Recommended Workup: {', '.join(diff.recommended_workup)}")

    print("\n--- RETRIEVED CLINICAL EVIDENCE ---")
    for ev in paused_state["evidence"]:
        print(f"• Source: {ev.source} | Relevance: {ev.relevance_score}")
        print(f"  Title: {ev.title}")

    print("\n--- SAFETY GUARDRAIL FLAGS ---")
    for flag in paused_state["safety_flags"]:
        print(f"• [{flag.severity}] ({flag.category}) {flag.title}")
        print(f"  Source: {flag.source_agent} | Description: {flag.description}")

    print("\n--- AUDIT TRAIL (STAGE 1) ---")
    for entry in paused_state["audit_trail"]:
        print(f"• [{entry.agent_name}] Action: {entry.action} -> {entry.summary}")

    print("\n" + "-"*65)
    print(f"⏸️ WORKFLOW PAUSED: Human Clinician Review Required before node '{snapshot.next[0]}'")
    print("-"*65)

    # 5. Stage 2 Execution: Clinician Validation Signal
    print("\n[CLINICIAN INPUT]: Attending Physician reviewed recommendations and granted APPROVAL.")
    logger.info("Executing Stage 2: Resuming graph after clinician validation signal...")
    
    final_output = graph.invoke(None, config=thread_config)
    final_snapshot = graph.get_state(thread_config)

    print("\n--- FINAL AUDIT TRAIL (STAGE 2 COMPLETE) ---")
    for entry in final_snapshot.values["audit_trail"]:
        print(f"• [{entry.agent_name}] Action: {entry.action} -> {entry.summary}")

    print("\n" + "="*65)
    print("Status: SUCCESS - Stateful MemorySaver & HITL Breakpoint Verified")
    print("="*65 + "\n")


if __name__ == "__main__":
    main()
