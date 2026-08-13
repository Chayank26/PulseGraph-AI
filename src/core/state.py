import operator
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Annotated
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


class PatientDemographics(BaseModel):
    """Demographics information for a patient."""
    patient_id: str
    age: int = Field(ge=0, le=130, description="Age in years")
    gender: str = Field(description="Gender identity or biological sex")
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
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ImagingFinding(BaseModel):
    """Detected abnormality or observation from medical imaging analysis."""
    finding_name: str = Field(description="e.g. Cardiomegaly, Pleural Effusion, Infiltrate, Pneumothorax")
    confidence: float = Field(ge=0.0, le=1.0, description="Model prediction confidence score")
    region: Optional[str] = Field(default=None, description="Anatomical location e.g. Left Lower Lobe")
    clinical_significance: str = Field(default="MODERATE", description="CRITICAL, HIGH, MODERATE, LOW")


class ImagingData(BaseModel):
    """Ingested medical image metadata and model diagnostic output."""
    image_path: str
    modality: str = Field(default="CHEST_XRAY_PA", description="e.g. CHEST_XRAY_PA, CT_CHEST")
    findings: List[ImagingFinding] = Field(default_factory=list)
    impression: str = Field(default="Normal imaging study")
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClinicianIdentity(BaseModel):
    """Authenticated physician profile for candidate rule logging and audit attribution."""
    doctor_id: str = Field(description="e.g. DOC-88204")
    full_name: str = Field(description="e.g. Dr. Sarah Chen")
    department: str = Field(description="e.g. Emergency Medicine")
    role: str = Field(default="Attending Physician")
    authenticated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SymbolicOverrideFlag(BaseModel):
    """Non-negotiable deterministic rule override flag."""
    rule_id: str = Field(description="e.g. RULE_001_BRADYCARDIA_BETA_BLOCKER")
    severity: str = Field(default="CRITICAL_OVERRIDE", description="CRITICAL_OVERRIDE, HARD_CONTRAINDICATION")
    message: str
    deterministic_rule: str
    action_required: str
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    authored_by: Optional[ClinicianIdentity] = Field(default=None, description="Physician who proposed or logged this rule candidate")
    governance_status: str = Field(default="PENDING_PEER_REVIEW", description="PENDING_PEER_REVIEW, APPROVED, REJECTED")
    originating_patient_id: Optional[str] = Field(default=None, description="Patient ID associated with rule proposal")


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
    current_step: str
    error_logs: Annotated[List[str], merge_list]
    # Clinician Authentication & HITL Loop Management
    authenticated_clinician: Optional[ClinicianIdentity]
    approved_by_clinician: Optional[bool]
    iteration_count: int
    re_evaluation_requested: bool
    clinician_notes: Optional[str]

