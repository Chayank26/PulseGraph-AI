import operator
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Annotated, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field, model_validator

WorkflowStep = Literal[
    "init",
    "initialized",
    "intake_age_required",
    "waiting_for_clinical_data",
    "triage_completed",
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
    allergies: List[str] = Field(default_factory=list, description="Known drug or food allergies")
    chronic_conditions: List[str] = Field(default_factory=list, description="Pre-existing diagnoses")
    current_medications: List[str] = Field(default_factory=list, description="Active prescriptions")


class VitalSigns(BaseModel):
    """Extracted physiological vitals and measurements."""
    heart_rate_bpm: Optional[float] = Field(default=None, description="Heart rate in beats per minute")
    blood_pressure_sys: Optional[float] = Field(default=None, description="Systolic blood pressure (mmHg)")
    blood_pressure_dia: Optional[float] = Field(default=None, description="Diastolic blood pressure (mmHg)")
    temperature_c: Optional[float] = Field(default=None, description="Body temperature in Celsius")
    respiratory_rate: Optional[float] = Field(default=None, description="Breaths per minute")
    spo2_percent: Optional[float] = Field(default=None, description="Oxygen saturation %")
    bmi: Optional[float] = Field(default=None, description="Body Mass Index")


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


def merge_requests(left: List[ClinicalDataRequest], right: List[ClinicalDataRequest]) -> List[ClinicalDataRequest]:
    """Reducer helper to merge ClinicalDataRequest lists by request_id, preserving lifecycle state."""
    if not left:
        return right or []
    if not right:
        return left or []

    req_map = {}
    for item in left:
        req_id = item.request_id if hasattr(item, "request_id") else item.get("request_id")
        req_map[req_id] = item

    for item in right:
        req_id = item.request_id if hasattr(item, "request_id") else item.get("request_id")
        existing = req_map.get(req_id)
        if existing:
            existing_status = existing.status if hasattr(existing, "status") else existing.get("status")
            new_status = item.status if hasattr(item, "status") else item.get("status")
            if existing_status == "RESOLVED" and new_status != "RESOLVED":
                continue
        req_map[req_id] = item

    return list(req_map.values())


class ClinicalState(TypedDict):
    """
    Central state definition for PulseGraph AI multi-agent workflow graph.
    Maintains immutable audit records, running diagnostic differentials,
    imaging analysis, symbolic override flags, retrieved evidence, and safety guardrails.
    """
    patient_id: str
    demographics: Optional[PatientDemographics]
    raw_notes: Annotated[List[str], merge_list]
    vitals: Optional[VitalSigns]
    risk_scores: Annotated[List[RiskScore], merge_list]
    differentials: Annotated[List[DiagnosticDifferential], merge_list]
    imaging_data: Optional[ImagingData]
    safety_flags: Annotated[List[SafetyFlag], merge_list]
    symbolic_overrides: Annotated[List[SymbolicOverrideFlag], merge_list]
    evidence: Annotated[List[ClinicalEvidence], merge_list]
    audit_trail: Annotated[List[AuditEntry], merge_list]
    current_step: WorkflowStep
    error_logs: Annotated[List[str], merge_list]
    authenticated_clinician: Optional[ClinicianIdentity]
    approved_by_clinician: Optional[bool]
    iteration_count: int
    re_evaluation_requested: bool
    clinician_notes: Optional[str]
    pending_data_requests: Annotated[List[ClinicalDataRequest], merge_requests]
    resolved_data_requests: Annotated[List[ClinicalDataRequest], merge_requests]
    active_data_request_id: Optional[str]
