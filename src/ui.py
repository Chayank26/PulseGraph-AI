import os
import sys
import json
import logging
import streamlit as st
from datetime import datetime, timezone

# Ensure project root directory is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.settings import settings
from src.auth.database import authenticate_doctor, init_db
from src.auth.session import save_persistent_session, load_persistent_session, clear_persistent_session
from src.core.state import ClinicalState, PatientDemographics, VitalSigns, ClinicianIdentity, SymbolicOverrideFlag
from src.core.graph import build_clinical_graph, MAX_ITERATIONS
from src.core.data_requests import get_pending_requests, validate_response, resolve_request, apply_response_to_state


# Page Configuration
st.set_page_config(
    page_title="PulseGraph AI - Clinical Decision Support System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom Styling (Dark Clinical Theme)
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #e0e6ed;
    }
    .main-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        border: 1px solid #334155;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .doctor-banner {
        background-color: #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .alert-critical {
        background-color: #450a0a;
        border: 1px solid #991b1b;
        border-left: 5px solid #ef4444;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.75rem;
    }
    .alert-high {
        background-color: #451a03;
        border: 1px solid #9a3412;
        border-left: 5px solid #f97316;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.75rem;
    }
    .card-box {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .badge-approved {
        background-color: #065f46;
        color: #34d399;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-pending {
        background-color: #78350f;
        color: #fbbf24;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    </style>
""", unsafe_allow_html=True)


# Initialize DB
init_db()


def get_mock_patient_state() -> ClinicalState:
    """Helper to initialize mock patient state PAT-88291."""
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
        heart_rate_bpm=48.0,
        blood_pressure_sys=135.0,
        blood_pressure_dia=85.0,
        temperature_c=37.1,
        respiratory_rate=22.0,
        spo2_percent=91.0
    )

    return {
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
        "error_logs": [],
        "authenticated_clinician": None,
        "approved_by_clinician": None,
        "iteration_count": 0,
        "re_evaluation_requested": False,
        "clinician_notes": None
    }


def render_login_gate():
    """Render persistent login interface."""
    st.markdown("<div class='main-header'><h1>🏥 PulseGraph AI - Physician Portal</h1><p>Clinical Decision Support & Neuro-Symbolic Diagnostics Agent Framework</p></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='card-box'>", unsafe_allow_html=True)
        st.subheader("🔐 Physician Authentication")
        st.caption("Default Test Doctor Credentials: **DOC-88204** / Password: **password123**")
        
        doctor_id = st.text_input("Doctor ID", value="DOC-88204", key="login_doc_id")
        password = st.text_input("Password", type="password", value="password123", key="login_pw")
        
        if st.button("Sign In to Clinical System", type="primary", use_container_width=True):
            user_info = authenticate_doctor(doctor_id, password)
            if user_info:
                token = save_persistent_session(user_info)
                st.session_state["session_token"] = token
                st.session_state["doctor_info"] = user_info
                st.success(f"Welcome back, {user_info['full_name']}!")
                st.rerun()
            else:
                st.error("Invalid Doctor ID or Password.")
        st.markdown("</div>", unsafe_allow_html=True)


def main_dashboard():
    """Render main clinical decision support dashboard."""
    doctor_info = st.session_state["doctor_info"]

    # Header & Banner
    col_banner, col_logout = st.columns([5, 1])
    with col_banner:
        st.markdown(f"""
            <div class="doctor-banner">
                <div>
                    <h3 style="margin:0; padding:0; color:#60a5fa;">👨‍⚕️ {doctor_info['full_name']} ({doctor_info['doctor_id']})</h3>
                    <p style="margin:0; padding:0; color:#94a3b8; font-size:0.9rem;">{doctor_info['role']} | Department: <b>{doctor_info['department']}</b></p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col_logout:
        if st.button("Sign Out", type="secondary", use_container_width=True):
            clear_persistent_session()
            st.session_state.pop("session_token", None)
            st.session_state.pop("doctor_info", None)
            st.rerun()

    # Graph Setup & Thread State Management
    thread_id = f"session_ui_patient_88291"
    thread_config = {"configurable": {"thread_id": thread_id}}

    if "graph" not in st.session_state:
        st.session_state["graph"] = build_clinical_graph()
        
    graph = st.session_state["graph"]

    # Initialize graph if unstarted
    snapshot = graph.get_state(thread_config)
    if not snapshot.values:
        initial_state = get_mock_patient_state()
        graph.invoke(initial_state, config=thread_config)
        snapshot = graph.get_state(thread_config)

    paused_state = snapshot.values
    demographics = paused_state.get("demographics")
    vitals = paused_state.get("vitals")

    # Patient Header Banner
    st.markdown(f"""
        <div class="card-box" style="border-left: 4px solid #10b981;">
            <h2 style="margin:0; color:#34d399;">📋 Patient Report: {paused_state.get('patient_id')}</h2>
            <p style="margin:0; color:#cbd5e1;"><b>Age:</b> {demographics.age} | <b>Gender:</b> {demographics.gender} | <b>Blood Type:</b> {demographics.blood_type or 'N/A'} | <b>Allergies:</b> {', '.join(demographics.allergies) if demographics.allergies else 'NKDA'}</p>
            <p style="margin:0; color:#cbd5e1;"><b>Chronic Conditions:</b> {', '.join(demographics.chronic_conditions)}</p>
            <p style="margin:0; color:#cbd5e1;"><b>Current Prescriptions:</b> {', '.join(demographics.current_medications)}</p>
        </div>
    """, unsafe_allow_html=True)

    # Vitals Grid
    st.subheader("📊 Extraction & Vital Signs")
    v1, v2, v3, v4, v5 = st.columns(5)
    v1.metric("Heart Rate", f"{vitals.heart_rate_bpm} bpm", delta="Severe Bradycardia" if vitals.heart_rate_bpm < 50 else None, delta_color="inverse")
    v2.metric("Blood Pressure", f"{int(vitals.blood_pressure_sys)}/{int(vitals.blood_pressure_dia)}", "mmHg")
    v3.metric("SpO2", f"{vitals.spo2_percent}%", delta="Hypoxia" if vitals.spo2_percent < 92 else None, delta_color="inverse")
    v4.metric("Temp", f"{vitals.temperature_c} °C")
    v5.metric("Resp Rate", f"{vitals.respiratory_rate} /min")

    st.markdown("---")

    # 2 Column Main Layout (Clinical Data vs HITL Panel)
    col_left, col_right = st.columns([3, 2])

    with col_left:
        # Risk Scores
        st.subheader("🧮 Calculated Clinical Risk Scores")
        for score in paused_state.get("risk_scores", []):
            st.markdown(f"""
                <div class="card-box">
                    <h4 style="margin:0; color:#38bdf8;">• {score.score_name}: <span style="color:#f59e0b;">{score.value} {score.unit or ''}</span></h4>
                    <p style="margin:4px 0 0 0; color:#e2e8f0;"><b>Interpretation:</b> {score.interpretation}</p>
                </div>
            """, unsafe_allow_html=True)

        # Multimodal Radiology
        st.subheader("🩻 Multimodal Radiology Analysis (Chest X-Ray)")
        img = paused_state.get("imaging_data")
        if img:
            st.markdown(f"""
                <div class="card-box">
                    <p style="margin:0; color:#94a3b8;">Modality: <b>{img.modality}</b> | Path: <code>{img.image_path}</code></p>
                    <p style="margin:4px 0 0 0; color:#f87171;"><b>Radiologist Impression:</b> {img.impression}</p>
            """, unsafe_allow_html=True)
            for f in img.findings:
                st.markdown(f"• **Finding:** {f.finding_name} ({f.region}) | Confidence: `{f.confidence}` | Significance: **{f.clinical_significance}**")
            st.markdown("</div>", unsafe_allow_html=True)

        # Diagnostic Differentials
        st.subheader("🩺 Candidate Differential Diagnoses")
        for diff in paused_state.get("differentials", []):
            st.markdown(f"""
                <div class="card-box">
                    <h4 style="margin:0; color:#a78bfa;">[{diff.likelihood}] {diff.condition_name} <span style="font-size:0.85rem; color:#94a3b8;">(ICD-10: {diff.icd10_code})</span></h4>
                    <p style="margin:4px 0; color:#cbd5e1;"><b>Rationale:</b> {diff.rationale}</p>
                    <p style="margin:0; color:#38bdf8;"><b>Recommended Workup:</b> {', '.join(diff.recommended_workup)}</p>
                </div>
            """, unsafe_allow_html=True)

        # Medical Evidence RAG
        st.subheader("📚 Grounding Clinical Evidence (PubMed / Guidelines)")
        for ev in paused_state.get("evidence", []):
            st.markdown(f"""
                <div class="card-box">
                    <h5 style="margin:0; color:#60a5fa;">{ev.title}</h5>
                    <p style="margin:2px 0; font-size:0.85rem; color:#94a3b8;">Source: {ev.source} | Authors: {ev.authors or 'N/A'}</p>
                    <p style="margin:4px 0 0 0; font-size:0.9rem; color:#cbd5e1;"><i>"{ev.snippet}"</i></p>
                </div>
            """, unsafe_allow_html=True)

    with col_right:
        # Safety Guardrails & Hard Rules
        st.subheader("🚨 Safety Guardrail & Symbolic Overrides")
        
        # Pharmacology & Vital Flags
        for flag in paused_state.get("safety_flags", []):
            css_cls = "alert-critical" if flag.severity in ["CRITICAL", "HIGH"] else "alert-high"
            st.markdown(f"""
                <div class="{css_cls}">
                    <h4 style="margin:0; color:#fca5a5;">[{flag.severity}] {flag.title}</h4>
                    <p style="margin:4px 0 0 0; color:#fee2e2;">{flag.description}</p>
                    <p style="margin:2px 0 0 0; font-size:0.8rem; color:#fca5a5;">Source: {flag.source_agent}</p>
                </div>
            """, unsafe_allow_html=True)

        # Deterministic Rules
        for rule in paused_state.get("symbolic_overrides", []):
            auth_str = f" | Authored by: {rule.authored_by.full_name}" if rule.authored_by else ""
            status_badge = f"<span class='badge-pending'>{rule.governance_status}</span>" if rule.governance_status != "APPROVED" else "<span class='badge-approved'>APPROVED</span>"
            st.markdown(f"""
                <div class="alert-critical" style="background-color:#581c87; border-color:#9333ea;">
                    <h4 style="margin:0; color:#e9d5ff;">🚨 {rule.rule_id} {status_badge}</h4>
                    <p style="margin:4px 0 0 0; color:#f3e8ff;"><b>Rule Logic:</b> <code>{rule.deterministic_rule}</code></p>
                    <p style="margin:4px 0 0 0; color:#fae8ff;">{rule.message}</p>
                    <p style="margin:4px 0 0 0; color:#f0abfc;"><b>Required Action:</b> {rule.action_required}{auth_str}</p>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Conditional Clinical Data Acquisition UI Panel
        pending_requests = get_pending_requests(paused_state)
        if pending_requests:
            req = pending_requests[0]
            st.markdown(f"""
                <div class="alert-high" style="background-color:#451a03; border:2px solid #f97316;">
                    <h3 style="margin:0; color:#fbbf24;">⚠️ Additional Clinical Data Required</h3>
                    <p style="margin:4px 0 0 0; color:#fed7aa;"><b>Requesting Agent:</b> <code style="color:#60a5fa;">{req.requesting_agent.upper()}</code> | <b>Pathway:</b> <b>{req.pathway_name}</b></p>
                    <p style="margin:4px 0 0 0; color:#ffedd5;"><b>Clinical Rationale:</b> {req.reason}</p>
                </div>
            """, unsafe_allow_html=True)

            with st.form(key=f"data_acquisition_form_{req.request_id}"):
                st.write("📋 **Provide Missing Clinical Parameters:**")
                form_responses = {}
                for field in req.required_fields + req.optional_fields:
                    field_label = f"{field.label} {'*' if field.required else '(Optional)'}"
                    if field.options:
                        selected_opt = st.selectbox(field_label, options=field.options, help=field.description)
                        # Extract value e.g. "0 (Normal)" -> 0
                        val_part = selected_opt.split()[0] if (selected_opt and "(" in selected_opt) else selected_opt
                        form_responses[field.field_key] = val_part
                    elif field.data_type in ["int", "float"]:
                        form_responses[field.field_key] = st.number_input(field_label, value=0, help=field.description)
                    else:
                        form_responses[field.field_key] = st.text_input(field_label, help=field.description)

                submit_btn = st.form_submit_button("Submit Clinical Data", type="primary", use_container_width=True)
                if submit_btn:
                    is_valid, errors = validate_response(req, form_responses)
                    if not is_valid:
                        for err in errors:
                            st.error(f"⚠️ {err}")
                    else:
                        resolved = resolve_request(req, form_responses)
                        state_updates = apply_response_to_state(paused_state, form_responses)
                        state_updates["pending_data_requests"] = [resolved]
                        state_updates["resolved_data_requests"] = [resolved]

                        st.session_state["graph"].update_state(thread_config, state_updates, as_node="data_request_review")
                        st.session_state["graph"].invoke(None, config=thread_config)

                        st.session_state["flash_message"] = ("success", f"Clinical data submitted for {req.pathway_name}. Workflow resuming...")
                        st.rerun()

            st.markdown("---")

        # HITL Interactive Decision Panel
        st.subheader("⚡ Human-in-the-Loop Decision Panel")
        st.caption(f"Current Re-evaluation Loop Iteration: **{paused_state.get('iteration_count', 0)} / {MAX_ITERATIONS}**")

        current_step = paused_state.get("current_step", "")
        is_finished = not bool(snapshot.next)

        # Flash messages across reruns
        if "flash_message" in st.session_state:
            msg_type, msg_text = st.session_state.pop("flash_message")
            if msg_type == "success":
                st.success(msg_text)
            elif msg_type == "info":
                st.info(msg_text)
            elif msg_type == "warning":
                st.warning(msg_text)

        if current_step == "ehr_exported" or paused_state.get("approved_by_clinician") is True:
            st.success("✅ **Care Plan Approved & Exported to EHR** by Physician.")
        elif current_step.startswith("clinician_rejected") or (paused_state.get("approved_by_clinician") is False and not paused_state.get("re_evaluation_requested")):
            st.error("🛑 **Care Plan Terminated for Manual Doctor Takeover**.")
        elif snapshot.next:
            if snapshot.next[0] == "data_request_review":
                st.warning("⚠️ **Workflow Paused**: Awaiting missing clinical parameters above.")
            else:
                st.info(f"⏸️ Graph Execution Paused before node: `{snapshot.next[0]}`")

        notes_input = st.text_area("Clinician Notes & Feedback Guidance", placeholder="Enter clinical rationale, feedback for re-evaluation, or candidate override notes...", key="clinician_notes_input", disabled=is_finished)


        clinician_identity = ClinicianIdentity(
            doctor_id=doctor_info["doctor_id"],
            full_name=doctor_info["full_name"],
            department=doctor_info["department"],
            role=doctor_info.get("role", "Attending Physician")
        )

        b1, b2, b3 = st.columns(3)

        # Button 1: Approve Plan
        if b1.button("✅ Approve Plan", type="primary", use_container_width=True, disabled=is_finished):
            st.session_state["graph"].update_state(
                thread_config,
                {
                    "authenticated_clinician": clinician_identity,
                    "approved_by_clinician": True,
                    "re_evaluation_requested": False,
                    "clinician_notes": notes_input
                }
            )
            st.session_state["graph"].invoke(None, config=thread_config)
            st.session_state["flash_message"] = ("success", "Plan Approved! Recommendations exported to EHR.")
            st.rerun()

        # Button 2: Reject & Re-run AI with Feedback
        if b2.button("🔄 Reject & Re-run", use_container_width=True, disabled=is_finished or paused_state.get('iteration_count', 0) >= MAX_ITERATIONS):
            if not notes_input.strip():
                st.error("⚠️ Please enter feedback notes before requesting re-evaluation.")
            elif paused_state.get("iteration_count", 0) >= MAX_ITERATIONS:
                st.error(f"🛑 Maximum re-evaluation iterations ({MAX_ITERATIONS}) reached. Must select Approve or Manual Takeover.")
            else:
                st.session_state["graph"].update_state(
                    thread_config,
                    {
                        "authenticated_clinician": clinician_identity,
                        "approved_by_clinician": False,
                        "re_evaluation_requested": True,
                        "clinician_notes": notes_input
                    }
                )
                st.session_state["graph"].invoke(None, config=thread_config)
                st.session_state["flash_message"] = ("info", "Re-evaluating graph with physician feedback...")
                st.rerun()

        # Button 3: Reject & Manual Takeover
        if b3.button("🛑 Manual Takeover", use_container_width=True, disabled=is_finished):
            if not notes_input.strip():
                st.error("⚠️ Please enter a rationale note for manual takeover / rule logging.")
            else:
                candidate_rule = SymbolicOverrideFlag(
                    rule_id=f"CANDIDATE_RULE_{doctor_info['doctor_id']}_{datetime.now(timezone.utc).strftime('%H%M%S')}",
                    severity="CRITICAL_OVERRIDE",
                    message=f"MANUAL TAKEOVER: {notes_input}",
                    deterministic_rule="IF ClinicianOverride == True THEN TerminateAIWorkflow",
                    action_required="Attending Physician manual care pathway initiated.",
                    authored_by=clinician_identity,
                    governance_status="PENDING_PEER_REVIEW",
                    originating_patient_id=paused_state.get("patient_id")
                )

                st.session_state["graph"].update_state(
                    thread_config,
                    {
                        "authenticated_clinician": clinician_identity,
                        "approved_by_clinician": False,
                        "re_evaluation_requested": False,
                        "clinician_notes": notes_input,
                        "symbolic_overrides": [candidate_rule]
                    }
                )
                st.session_state["graph"].invoke(None, config=thread_config)
                st.session_state["flash_message"] = ("warning", "Manual takeover logged. Candidate symbolic override recorded for peer review.")
                st.rerun()


    # Audit Trail Log
    with st.expander("📝 View Full State Audit Trail"):
        for entry in paused_state.get("audit_trail", []):
            st.text(f"• [{entry.agent_name}] Action: {entry.action} -> {entry.summary}")


def main():
    """Main application router."""
    if "session_token" not in st.session_state:
        render_login_gate()
    else:
        # Validate persistent token
        user_info = load_persistent_session(st.session_state["session_token"])
        if user_info:
            st.session_state["doctor_info"] = user_info
            main_dashboard()
        else:
            st.session_state.pop("session_token", None)
            render_login_gate()


if __name__ == "__main__":
    main()
