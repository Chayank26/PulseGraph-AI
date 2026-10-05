import operator
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Annotated, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field, model_validator, ConfigDict, field_validator

WorkflowStep = Literal[
    "init",
    "initialized",
    "intake_age_required",
    "waiting_for_clinical_data",
    "triage_completed",
    "triage_manual_review_required",
    "imaging_decision_required",
    "imaging_skipped",
    "imaging_report_provided",
    "imaging_manual_review_required",
    "imaging_data_requested",
    "imaging_analyzed",
    "diagnostic_completed",
    "evidence_retrieved",
    "safety_data_requested",
    "safety_audited",
    "symbolic_guardrails_evaluated",
    "data_request_processed",
    "clinician_approved",
    "clinician_rejected_manual_takeover",
    "clinician_re_evaluation_requested",
    "ehr_exported",
    "error"
]


class PatientDemographics(BaseModel):
    """Demographics information for a patient."""
    patient_id: str
    age: Optional[int] = Field(default=None, ge=0, le=130, description="Age in years")
    gender: Optional[str] = Field(default=None, description="Gender identity or biological sex")
    blood_type: Optional[str] = Field(default=None, description="ABO/Rh blood type")
    chief_complaint: Optional[str] = Field(default=None, description="Presenting complaint and symptoms")
    allergies: List[str] = Field(default_factory=list, description="Known drug or food allergies")
    chronic_conditions: List[str] = Field(default_factory=list, description="Pre-existing diagnoses")
    current_medications: List[str] = Field(default_factory=list, description="Active prescriptions")


class VitalSigns(BaseModel):
    """Extracted physiological vitals and measurements."""
    model_config = ConfigDict(allow_inf_nan=False)

    @field_validator("*", mode="before")
    @classmethod
    def reject_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError("Vital measurements cannot be booleans")
        return value

    heart_rate_bpm: Optional[float] = Field(default=None, ge=0, description="Heart rate in beats per minute")
    blood_pressure_sys: Optional[float] = Field(default=None, ge=0, description="Systolic blood pressure (mmHg)")
    blood_pressure_dia: Optional[float] = Field(default=None, ge=0, description="Diastolic blood pressure (mmHg)")
    temperature_c: Optional[float] = Field(default=None, ge=0, description="Body temperature in Celsius")
    respiratory_rate: Optional[float] = Field(default=None, ge=0, description="Breaths per minute")
    spo2_percent: Optional[float] = Field(default=None, ge=0, le=100, description="Oxygen saturation %")
    bmi: Optional[float] = Field(default=None, ge=0, description="Body Mass Index")


class RiskScore(BaseModel):
    """Calculated clinical risk score (e.g. Wells, HEART, CURB-65)."""
    score_name: str
    value: float
    unit: Optional[str] = None
    interpretation: str
    details: Dict[str, Any] = Field(default_factory=dict)
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DiagnosticDifferential(BaseModel):
    """Single candidate differential diagnosis with evidence rationale."""
    condition_name: str
    icd10_code: Optional[str] = None
    likelihood: str = Field(description="High, Moderate, Low, or Percentage")
    rationale: str
    conflicting_evidence: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    evidence_references: List[Dict[str, str]] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    recommended_workup: List[str] = Field(default_factory=list)


class SafetyFlag(BaseModel):
    """Flag for drug interaction, contraindication, or clinical safety warning."""
    severity: str = Field(description="CRITICAL, HIGH, MEDIUM, LOW")
    category: str = Field(description="DRUG_INTERACTION, CONTRAINDICATION, DOSAGE, ALLERGY_ALERT, VITAL_ALERT")
    title: str
    description: str
    source_agent: str
    flagged_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClinicalEvidence(BaseModel):
    document_id: Optional[str] = None
    claim_id: Optional[str] = None
    claim: Optional[str] = None
    support_status: str = 'UNASSESSED'
    source_version: Optional[str] = None
    verified_on: Optional[str] = None
    retrieved_at: Optional[str] = None
    content_sha256: Optional[str] = None
    """Retrieved medical literature, guideline snippet, or trial citation."""
    title: str
    authors: Optional[str] = None
    source: str = Field(description="PubMed, Medical Guideline, UpToDate, internal KB")
    url_or_doi: Optional[str] = None
    snippet: str
    relevance_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ImagingFinding(BaseModel):
    """Detected abnormality or observation from medical imaging analysis."""
    finding_name: str = Field(description="e.g. Cardiomegaly, Pleural Effusion, Infiltrate, Pneumothorax")
    confidence: float = Field(ge=0.0, le=1.0, description="Model prediction confidence score")
    region: Optional[str] = Field(default=None, description="Anatomical location e.g. Left Lower Lobe")
    clinical_significance: Optional[str] = Field(default=None, description="CRITICAL, HIGH, MODERATE, LOW")


class ImagingData(BaseModel):
    """Ingested medical image metadata and model diagnostic output."""
    image_path: str
    modality: str = Field(default="CHEST_XRAY_PA", description="e.g. CHEST_XRAY_PA, CT_CHEST")
    findings: List[ImagingFinding] = Field(default_factory=list)
    impression: Optional[str] = Field(default=None, description="Clinical impression notes")
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClinicianIdentity(BaseModel):
    """Authenticated physician profile for candidate rule logging and audit attribution."""
    doctor_id: str = Field(description="e.g. DOC-88204")
    full_name: str = Field(description="e.g. Dr. Sarah Chen")
    department: str = Field(description="e.g. Emergency Medicine")
    role: Optional[str] = Field(default=None, description="Role e.g. Attending Physician, Resident, Nurse")
    authenticated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SymbolicOverrideFlag(BaseModel):
    """Non-negotiable deterministic rule override flag."""
    rule_id: str = Field(description="e.g. RULE_001_BRADYCARDIA_BETA_BLOCKER")
    severity: Optional[str] = Field(default=None, description="CRITICAL_OVERRIDE, HARD_CONTRAINDICATION")
    message: str
    deterministic_rule: str
    action_required: str
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    authored_by: Optional[ClinicianIdentity] = Field(default=None, description="Physician who proposed or logged this rule candidate")
    governance_status: str = Field(default="PENDING_PEER_REVIEW", description="PENDING_PEER_REVIEW, APPROVED, REJECTED")
    originating_patient_id: Optional[str] = Field(default=None, description="Patient ID associated with rule proposal")


class ClinicalFieldRequirement(BaseModel):
    """Specification of a single requested clinical data field."""
    allow_unavailable: bool = False
    field_key: str = Field(description="System identifier e.g. ecg_score, troponin_score, cardiac_risk_factors_count")
    label: str = Field(description="Human-readable label for UI form rendering")
    data_type: str = Field(description="float, int, bool, str, enum, file")
    required: bool = Field(default=True, description="True if mandatory for clinical assessment; False if optional")
    description: Optional[str] = Field(default=None, description="Clinical rationale for requesting this field")
    options: Optional[List[str]] = Field(default=None, description="Valid choices for select/enum inputs")


class ClinicalDataRequest(BaseModel):
    """Structured data acquisition request created by any clinical agent when required data is missing."""
    request_id: str = Field(description="Unique request ID e.g. REQ-TRIAGE-HEART-001")
    requesting_agent: str = Field(description="Node name of requesting agent e.g. triage, imaging, safety, diagnostic, symbolic_guardrail")
    pathway_name: str = Field(description="Clinical pathway or score requiring data e.g. HEART Score Assessment")
    reason: str = Field(description="Explanation of missing information requiring clinician input")
    priority: str = Field(default="HIGH", description="CRITICAL, HIGH, ROUTINE")
    required_fields: List[ClinicalFieldRequirement] = Field(default_factory=list)
    optional_fields: List[ClinicalFieldRequirement] = Field(default_factory=list)
    status: str = Field(default="PENDING", description="PENDING, RESOLVED, SKIPPED, EXPIRED")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = Field(default=None)
    clinician_response: Optional[Dict[str, Any]] = Field(default=None)

    @model_validator(mode="after")
    def validate_request_fields_and_status(self) -> "ClinicalDataRequest":
        if not self.required_fields and not self.optional_fields:
            raise ValueError(f"ClinicalDataRequest [{self.request_id}] must contain at least one field requirement.")

        if self.status == "RESOLVED":
            if not self.clinician_response or not isinstance(self.clinician_response, dict):
                raise ValueError(f"ClinicalDataRequest [{self.request_id}] cannot be RESOLVED without a valid clinician_response dictionary.")

            for req_field in self.required_fields:
                if req_field.required:
                    val = self.clinician_response.get(req_field.field_key)
                    if val is None or (isinstance(val, str) and not val.strip()):
                        raise ValueError(
                            f"Cannot resolve request '{self.request_id}': missing required field '{req_field.label}' ({req_field.field_key})."
                        )
        return self


class AuditEntry(BaseModel):
    """Audit log entry capturing state mutations and agent actions."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent_name: str
    action: str
    summary: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


def merge_list(left: List[Any], right: List[Any]) -> List[Any]:
    """Helper reducer function to merge lists in LangGraph state updates."""
    return left + right


def merge_requests(left: List[ClinicalDataRequest], right: Optional[List[ClinicalDataRequest]]) -> List[ClinicalDataRequest]:
    """Reducer helper to merge ClinicalDataRequest lists by request_id, preserving lifecycle state."""
    if not left and not right:
        return []

    req_map = {}
    for item in (left or []):
        req_id = item.request_id if hasattr(item, "request_id") else item.get("request_id")
        req_map[req_id] = item

    for item in (right or []):
        req_id = item.request_id if hasattr(item, "request_id") else item.get("request_id")
        req_map[req_id] = item

    pending = []
    for item in req_map.values():
        status = item.status if hasattr(item, "status") else item.get("status")
        if status != "RESOLVED":
            pending.append(item)

    return pending


def merge_resolved_requests(left, right):
    """Retain answered requests for subsequent triage passes."""
    requests = {r.request_id: r for r in (left or [])}
    requests.update({r.request_id: r for r in (right or [])})
    return list(requests.values())


def merge_risk_scores(left, right):
    """Replace recalculated scores instead of accumulating duplicate results."""
    scores = {}  # Each triage pass provides the current complete/partial score set.
    scores.update({score.score_name: score for score in (right or [])})
    return list(scores.values())


class ClinicalState(TypedDict):
    """
    Central state definition for PulseGraph AI multi-agent workflow graph.
    Maintains immutable audit records, running diagnostic differentials,
    imaging analysis, symbolic override flags, retrieved evidence, and safety guardrails.
    """
    diagnostic_followup_answers: Optional[Dict[str, Any]]
    diagnostic_followup_rounds: int
    diagnostic_followup_disposition: Optional[str]
    diagnostic_fingerprint: Optional[str]
    patient_id: str
    demographics: Optional[PatientDemographics]
    urgency: Optional[Dict[str, Any]]
    imaging_assessment_fingerprint: Optional[str]
    imaging_decision: Optional[Dict[str, Any]]
    imaging_response: Optional[Dict[str, Any]]
    image_path: Optional[str]
    pathway_decisions: Optional[Dict[str, Any]]
    urgency_context: Optional[Dict[str, Any]]
    urgency_resume_node: Optional[str]
    urgency_observation_revision: int
    presentation: Optional[Dict[str, Any]]
    raw_notes: Annotated[List[str], merge_list]
    vitals: Optional[VitalSigns]
    risk_scores: Annotated[List[RiskScore], merge_risk_scores]
    differentials: List[DiagnosticDifferential]
    imaging_data: Optional[ImagingData]
    safety_flags: List[SafetyFlag]
    symbolic_overrides: List[SymbolicOverrideFlag]
    evidence: List[ClinicalEvidence]
    audit_trail: Annotated[List[AuditEntry], merge_list]
    current_step: WorkflowStep
    error_logs: Annotated[List[str], merge_list]
    authenticated_clinician: Optional[ClinicianIdentity]
    approved_by_clinician: Optional[bool]
    iteration_count: int
    re_evaluation_requested: bool
    clinician_notes: Optional[str]
    pending_data_requests: Annotated[List[ClinicalDataRequest], merge_requests]
    resolved_data_requests: Annotated[List[ClinicalDataRequest], merge_resolved_requests]
    active_data_request_id: Optional[str]
