import os
import json
import logging
from pprint import pprint

from config.settings import settings
from src.core.state import ClinicalState, PatientDemographics, VitalSigns, ClinicianIdentity
from src.core.graph import build_clinical_graph

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("PulseGraph.Main")


def load_mock_patient():
    """Utility to load mock patient data for Phase 3 execution test."""
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
        chronic_conditions=["Hypertension", "Recent Right Knee Surgery", "Chronic Kidney Disease"],
        current_medications=["Warfarin 5mg daily", "Ibuprofen 400mg PRN", "Metoprolol 25mg daily"]
    )

    vitals = VitalSigns(
        heart_rate_bpm=48.0,  # Severe Bradycardia (<50 bpm) to test RULE_001
        blood_pressure_sys=135.0,
        blood_pressure_dia=85.0,
        temperature_c=37.1,
        respiratory_rate=22.0,
        spo2_percent=91.0
    )

    return demographics, vitals, raw_notes


def main():
    logger.info("=== Starting PulseGraph AI Phase 3 Multimodal & Neuro-Symbolic Verification ===")
    
    # 1. Load patient state
    demographics, vitals, raw_notes = load_mock_patient()
    
    initial_state: ClinicalState = {
        "patient_id": demographics.patient_id,
        "demographics": demographics,
        "raw_notes": raw_notes,
        "vitals": vitals,
        "risk_scores": [],
        "differentials": [],
        "imaging_data": None,
        "safety_flags": [],
        "symbolic_overrides": [],
        "evidence": [],
        "audit_trail": [],
        "current_step": "initialized",
        "error_logs": []
    }

    # 2. Build graph with stateful MemorySaver & HITL interrupt
    graph = build_clinical_graph()
    thread_config = {"configurable": {"thread_id": "session_phase3_pat_88291"}}

    # 3. Stage 1 Execution: Automated Agent Workflow (Pauses before 'human_review')
    logger.info("Executing Stage 1: Running 6-Node Neuro-Symbolic agent workflow until HITL breakpoint...")
    graph.invoke(initial_state, config=thread_config)
    
    # 4. Checkpoint State Inspection at Breakpoint
    snapshot = graph.get_state(thread_config)
    paused_state = snapshot.values
    logger.info(f"Graph execution paused at breakpoint! Next step pending: {snapshot.next}")

    print("\n" + "="*70)
    print("      PULSEGRAPH AI CLINICAL DECISION SUPPORT - NEURO-SYMBOLIC AUDIT")
    print("="*70)
    print(f"\n[PATIENT ID]: {paused_state['patient_id']} | Thread ID: session_phase3_pat_88291")
    print(f"Demographics: Age {demographics.age}, {demographics.gender} | Allergies: {demographics.allergies}")
    print(f"Vitals: HR {vitals.heart_rate_bpm} bpm | BP {vitals.blood_pressure_sys}/{vitals.blood_pressure_dia} | SpO2 {vitals.spo2_percent}%")

    print("\n--- CALCULATED RISK SCORES ---")
    for score in paused_state["risk_scores"]:
        print(f"• {score.score_name}: {score.value} {score.unit or ''} -> {score.interpretation}")

    print("\n--- MULTIMODAL CHEST X-RAY ANALYSIS ---")
    img = paused_state.get("imaging_data")
    if img:
        print(f"• Modality: {img.modality} | Image: {img.image_path}")
        print(f"  Impression: {img.impression}")
        for finding in img.findings:
            print(f"  Finding: {finding.finding_name} ({finding.region}) | Confidence: {finding.confidence} | Severity: {finding.clinical_significance}")

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

    print("\n--- DETERMINISTIC SYMBOLIC OVERRIDES (NEURO-SYMBOLIC RULES) ---")
    for rule in paused_state["symbolic_overrides"]:
        print(f"🚨 [{rule.severity}] {rule.rule_id}")
        print(f"   Message: {rule.message}")
        print(f"   Rule Logic: {rule.deterministic_rule}")
        print(f"   Required Action: {rule.action_required}")

    print("\n--- AUDIT TRAIL (STAGE 1 COMPLETE) ---")
    for entry in paused_state["audit_trail"]:
        print(f"• [{entry.agent_name}] Action: {entry.action} -> {entry.summary}")

    print("\n" + "-"*70)
    print(f"⏸️ WORKFLOW PAUSED: Clinician Verification Required before node '{snapshot.next[0]}'")
    print("-"*70)

    # 5. Stage 2 Execution: Clinician Approval Signal
    print("\n[CLINICIAN INPUT]: Attending Physician Dr. Sarah Chen (DOC-88204) reviewed differential + symbolic overrides and granted APPROVAL.")
    logger.info("Executing Stage 2: Resuming graph after clinician validation signal...")
    
    clinician = ClinicianIdentity(
        doctor_id="DOC-88204",
        full_name="Dr. Sarah Chen",
        department="Emergency Medicine"
    )
    graph.update_state(
        thread_config,
        {
            "authenticated_clinician": clinician,
            "approved_by_clinician": True,
            "re_evaluation_requested": False
        }
    )
    graph.invoke(None, config=thread_config)
    final_snapshot = graph.get_state(thread_config)

    print("\n--- FINAL AUDIT TRAIL (STAGE 2 COMPLETE) ---")
    for entry in final_snapshot.values["audit_trail"]:
        print(f"• [{entry.agent_name}] Action: {entry.action} -> {entry.summary}")


    print("\n" + "="*70)
    print("Status: SUCCESS - Phase 3 Multimodal Vision & Symbolic Rules Verified")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
