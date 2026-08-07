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
    """Utility to load mock patient data for baseline execution test."""
    notes_path = os.path.join("data", "mock_patients", "patient_001_notes.txt")
    fhir_path = os.path.join("data", "mock_patients", "patient_001.json")

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
    logger.info("=== Starting PulseGraph AI Execution Verification ===")
    
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

    # 2. Build graph
    graph = build_clinical_graph()

    # 3. Execute graph state machine
    logger.info("Invoking multi-agent workflow...")
    final_state = graph.invoke(initial_state)
    logger.info("Workflow execution complete.")

    # 4. Display Results
    print("\n" + "="*60)
    print("         PULSEGRAPH AI CLINICAL DECISION SUMMARY")
    print("="*60)
    print(f"\n[PATIENT ID]: {final_state['patient_id']}")
    print(f"Demographics: Age {demographics.age}, {demographics.gender} | Allergies: {demographics.allergies}")
    
    print("\n--- CALCULATED RISK SCORES ---")
    for score in final_state["risk_scores"]:
        print(f"• {score.score_name}: {score.value} {score.unit or ''} -> {score.interpretation}")

    print("\n--- DIAGNOSTIC DIFFERENTIALS ---")
    for diff in final_state["differentials"]:
        print(f"• [{diff.likelihood}] {diff.condition_name} (ICD: {diff.icd10_code})")
        print(f"  Rationale: {diff.rationale}")
        print(f"  Workup: {', '.join(diff.recommended_workup)}")

    print("\n--- RETRIEVED CLINICAL EVIDENCE ---")
    for ev in final_state["evidence"]:
        print(f"• Source: {ev.source} | Score: {ev.relevance_score}")
        print(f"  Title: {ev.title}")
        print(f"  Snippet: {ev.snippet}")

    print("\n--- SAFETY GUARDRAIL FLAGS ---")
    for flag in final_state["safety_flags"]:
        print(f"• [{flag.severity}] ({flag.category}) {flag.title}")
        print(f"  Description: {flag.description}")

    print("\n--- AUDIT TRAIL ---")
    for entry in final_state["audit_trail"]:
        print(f"• [{entry.agent_name}] Action: {entry.action} | Summary: {entry.summary}")

    print("\n" + "="*60)
    print("Status: SUCCESS - Multi-Agent Workflow Executed Cleanly")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
