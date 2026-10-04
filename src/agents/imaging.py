import os
import logging
from typing import Dict, Any, List
from src.core.state import ClinicalState, ImagingData, ImagingFinding, AuditEntry, ClinicalFieldRequirement
from src.core.data_requests import create_data_request

logger = logging.getLogger("PulseGraph.ImagingAgent")


def analyze_chest_xray(image_path: str) -> ImagingData:
    """
    Legacy filename-based demonstration (not used by the live workflow)
    on a Chest X-Ray DICOM/PNG image file.
    """
    logger.info("Running legacy filename demonstration")
    
    filename = os.path.basename(image_path).lower()
    findings: List[ImagingFinding] = []

    # Heuristic inference rules based on input file or mock parameters
    if "pneumothorax" in filename or "tension" in filename:
        findings.append(
            ImagingFinding(
                finding_name="Pneumothorax",
                confidence=0.94,
                region="Right Upper Lobe",
                clinical_significance="CRITICAL"
            )
        )
        impression = "Right-sided pneumothorax identified with partial lung collapse."
    elif "effusion" in filename or "infiltrate" in filename or "patient_001" in filename:
        findings.append(
            ImagingFinding(
                finding_name="Pleural Effusion",
                confidence=0.88,
                region="Left Costophrenic Angle",
                clinical_significance="HIGH"
            )
        )
        findings.append(
            ImagingFinding(
                finding_name="Subsegmental Atelectasis",
                confidence=0.82,
                region="Left Basar",
                clinical_significance="MODERATE"
            )
        )
        impression = "Blunting of left costophrenic angle consistent with small-to-moderate pleural effusion and left basilar atelectasis."
    elif "cardiomegaly" in filename:
        findings.append(
            ImagingFinding(
                finding_name="Cardiomegaly",
                confidence=0.91,
                region="Cardiac Silhouette",
                clinical_significance="HIGH"
            )
        )
        impression = "Enlarged cardiac silhouette with CTR > 0.55."
    else:
        impression = "Clear lung fields bilaterally. Cardiac silhouette and pulmonary vascularity within normal limits."

    return ImagingData(
        image_path=image_path,
        modality="CHEST_XRAY_PA",
        findings=findings,
        impression=impression
    )


def imaging_agent_node(state: ClinicalState) -> Dict[str, Any]:
    """Collect an imaging decision and optional clinician-supplied report."""
    from src.core.imaging import ImagingDecision
    from src.core.presentation import extract_presentation
    from src.core.routing import UNAVAILABLE

    decision_data = state.get("imaging_decision")
    presentation = dict(state.get("presentation") or extract_presentation(getattr(state.get("demographics"), "chief_complaint", "") or "", state.get("raw_notes", [])).model_dump(mode="json"))
    plan = {"reviewed_by": getattr(state.get("authenticated_clinician"), "doctor_id", None),
            "status": "NEEDS_DECISION", "decision": None,
            "reason": "Imaging need has not been confirmed by the clinician.",
            "limitations": ["No pixel-based image interpretation is available. A study reference alone is not a report.",
                            "Skipping imaging does not establish that imaging is clinically unnecessary."],
            "study_reference": state.get("image_path"), "report": None}

    def finish(step, request=None, report=None):
        presentation["imaging_plan"] = plan
        result = {"presentation": presentation, "imaging_data": report, "current_step": step,
            "audit_trail": [AuditEntry(agent_name="ImagingAgent", action="IMAGING_DECISION",
                summary=plan["reason"], metadata={"status": plan["status"], "decision": plan["decision"],
                    "doctor_id": getattr(state.get("authenticated_clinician"), "doctor_id", None)})]}
        if request:
            result["pending_data_requests"] = [request]
        return result

    if not decision_data:
        req = create_data_request("imaging", "Imaging decision",
            "Review the complaint, symptoms, allergies and available observations. Confirm whether imaging is needed. "
            "Optional imaging can be skipped; include an existing report if available. "
            "For required imaging, specify the modality and body region. No image inference is available.",
            [ClinicalFieldRequirement(field_key="imaging_decision", label="Imaging decision", data_type="enum",
                options=["no_imaging", "optional", "required", "uncertain"], required=True),
             ClinicalFieldRequirement(field_key="imaging_reason", label="Clinical rationale", data_type="str", required=True)],
            optional_fields=[ClinicalFieldRequirement(field_key="imaging_" + key, label=label, data_type="str", required=False)
                for key, label in [("modality", "Modality (required when requesting imaging or including a report)"),
                    ("anatomy", "Body region (required when requesting imaging or including a report)"),
                    ("report", "Existing radiology report / clinician interpretation (optional)"),
                    ("study_reference", "Study reference (optional; does not upload or interpret an image)")]])
        return finish("imaging_decision_required", req)

    decision = ImagingDecision.model_validate(decision_data)
    plan.update(decision.model_dump())
    plan["study_reference"] = decision.study_reference or state.get("image_path")
    if decision.decision == "uncertain":
        plan["status"] = "REQUIRES_CLINICIAN_ASSESSMENT"
        return finish("imaging_manual_review_required")
    if decision.decision == "no_imaging":
        plan["status"] = "SKIPPED"
        return finish("imaging_skipped")

    response = state.get("imaging_response") or {}
    if response.get("imaging_action") == "proceed_without_imaging":
        plan.update(status="OVERRIDDEN", override_reason=response["imaging_override_reason"])
        plan["reason"] = "Clinician override: " + response["imaging_override_reason"]
        return finish("imaging_skipped")
    if response.get("imaging_action") == "clinician_assessment":
        plan.update(status="REQUIRES_CLINICIAN_ASSESSMENT", reason=response["imaging_override_reason"])
        return finish("imaging_manual_review_required")

    report_text = response.get("imaging_report") or decision.report
    if report_text == UNAVAILABLE:
        plan.update(status="REQUIRES_CLINICIAN_ASSESSMENT", reason="Required imaging report is unavailable; clinician assessment is needed.")
        return finish("imaging_manual_review_required")
    if not report_text and decision.decision == "optional":
        plan["status"] = "SKIPPED"
        return finish("imaging_skipped")
    if not report_text:
        plan["status"] = "WAITING_FOR_REPORT"
        req = create_data_request("imaging", "Required imaging report",
            f"{decision.modality} of {decision.anatomy}: {decision.reason}. Submit a report, document an override, or hand off for clinician assessment.",
            [ClinicalFieldRequirement(field_key="imaging_action", label="How should the assessment proceed?", data_type="enum",
                options=["submit_report", "proceed_without_imaging", "clinician_assessment"], required=True)],
            optional_fields=[ClinicalFieldRequirement(field_key="imaging_report", label="Radiology report / clinician interpretation", data_type="str", required=False, allow_unavailable=True),
                ClinicalFieldRequirement(field_key="imaging_override_reason", label="Reason for override or clinician handoff", data_type="str", required=False)])
        return finish("imaging_data_requested", req)

    plan.update(status="REPORT_PROVIDED", report=report_text,
                report_source="Clinician-supplied report; not automated image interpretation")
    report = ImagingData(image_path=plan["study_reference"] or "", modality=decision.modality or "Unspecified",
                         findings=[], impression=report_text)
    return finish("imaging_report_provided", report=report)
