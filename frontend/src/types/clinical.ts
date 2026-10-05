export type AgentStatusType = 'IDLE' | 'RUNNING' | 'COMPLETED' | 'WAITING_FOR_DATA' | 'ERROR';

export type SeverityType = 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';

export type SessionStatusType = 
  | 'INITIALIZED'
  | 'RUNNING'
  | 'WAITING_FOR_CLINICAL_DATA'
  | 'WAITING_FOR_CLINICIAN_REVIEW'
  | 'APPROVED'
  | 'REJECTED_MANUAL_TAKEOVER';

export interface Doctor {
  id?: number;
  doctor_id: string;
  full_name: string;
  department: string;
  role: string;
  email?: string;
  created_at?: string;
}

export interface PatientDemographics {
  id?: number;
  patient_id: string;
  age?: number;
  gender?: string;
  blood_type?: string;
  chief_complaint?: string;
  relevant_history?: string[];
  allergies: string[];
  chronic_conditions: string[];
  current_medications: string[];
  created_at?: string;
  updated_at?: string;
}

export interface VitalSigns {
  heart_rate_bpm?: number;
  systolic_bp_mmhg?: number;
  diastolic_bp_mmhg?: number;
  resp_rate_bpm?: number;
  spo2_percent?: number;
  temperature_celsius?: number;
}

export interface RiskScore {
  score_name: string;
  score_value: number;
  risk_level: string;
  recommendation: string;
  parameters_used: Record<string, any>;
  calculated_at?: string;
}

export interface DiagnosticDifferential {
  condition_name: string;
  icd10_code?: string | null;
  likelihood: string;
  supporting_evidence?: string[];
  rationale: string;
  recommended_workup: string[];
}

export interface ImagingFinding {
  finding_name: string;
  confidence: number;
  region?: string;
  clinical_significance: SeverityType;
}

export interface ImagingData {
  image_path: string;
  modality: string;
  findings: ImagingFinding[];
  impression?: string;
  analyzed_at?: string;
}

export interface ClinicalEvidence {
  claim?: string;
  support_status?: string;
  source_version?: string;
  verified_on?: string;
  retrieved_at?: string;
  content_sha256?: string;
  title: string;
  authors?: string;
  source: string;
  url_or_doi?: string;
  snippet: string;
  relevance_score?: number;
}

export interface SafetyFlag {
  severity: SeverityType;
  category: string;
  description: string;
  source_agent: string;
  flagged_at: string;
}

export interface SymbolicOverrideFlag {
  rule_id: string;
  severity: SeverityType;
  message: string;
  deterministic_rule: string;
  action_required: string;
  triggered_at: string;
  governance_status: 'PENDING_PEER_REVIEW' | 'APPROVED' | 'REJECTED';
}

export interface AuditEntry {
  timestamp: string;
  agent_name: string;
  action: string;
  details: string;
}

export interface ClinicalFieldRequirement {
  allow_unavailable?: boolean;
  field_key: string;
  label: string;
  data_type: string;
  required: boolean;
  description?: string;
  options?: string[];
}

export interface ClinicalDataRequest {
  request_id: string;
  requesting_agent: string;
  pathway_name: string;
  reason: string;
  priority: SeverityType;
  required_fields: ClinicalFieldRequirement[];
  optional_fields?: ClinicalFieldRequirement[];
  status: 'PENDING' | 'RESOLVED';
  created_at: string;
  clinician_response?: Record<string, any>;
}

export interface ClinicalState {
  urgency?: UrgencyAssessment;
  presentation?: ClinicalPresentation;
  patient_id: string;
  demographics: PatientDemographics;
  raw_notes: string[];
  vitals?: VitalSigns;
  risk_scores: RiskScore[];
  differentials: DiagnosticDifferential[];
  imaging_data?: ImagingData;
  safety_flags: SafetyFlag[];
  symbolic_overrides: SymbolicOverrideFlag[];
  evidence: ClinicalEvidence[];
  audit_trail: AuditEntry[];
  current_step: string;
  authenticated_clinician?: Doctor;
  approved_by_clinician?: boolean;
  iteration_count: number;
  re_evaluation_requested: boolean;
  pending_data_requests: ClinicalDataRequest[];
  active_data_request_id?: string;
}

export interface ClinicalSession {
  session_id: string;
  patient_id: string;
  doctor_id: string;
  thread_id: string;
  status: string;
  current_step: string;
  started_at?: string;
  completed_at?: string;
  approved_at?: string;
  created_at?: string;
  updated_at?: string;
  state: ClinicalState;
}

export interface AgentInfo {
  id: string;
  number: string;
  name: string;
  shortName: string;
  tagline: string;
  color: string;
  lightColor: string;
  status: AgentStatusType;
  route: string;
}


export interface ImagingPlan {
  status: 'NEEDS_DECISION' | 'WAITING_FOR_REPORT' | 'REPORT_PROVIDED' | 'SKIPPED' | 'OVERRIDDEN' | 'REQUIRES_CLINICIAN_ASSESSMENT';
  decision: 'no_imaging' | 'optional' | 'required' | 'uncertain' | null;
  reason: string;
  modality?: string | null;
  anatomy?: string | null;
  study_reference?: string | null;
  report?: string | null;
  report_source?: string;
  override_reason?: string;
  limitations: string[];
}

export interface ClinicalPresentation {
  evidence_review?: { status: string; reason?: string; limitations: string[]; claims: { claim: string; status: string; reason: string }[] };
  symbolic_review?: { status: string; limitations: string[]; rules: { rule_id: string; status: string; reason: string }[] };
  diagnostic_review?: { status: string; input_fingerprint?: string; limitations?: string[] };
  imaging_plan?: ImagingPlan | null;
  routing?: {
    groups: Record<string, string[]>;
    pathways: { key: string; name: string; status: string; rationale: string; unavailable_fields: string[] }[];
    handoff_reasons: string[];
    requires_clinician_assessment: boolean;
    limitations: string[];
  } | null;
  extractor_version: string;
  sources: { source_id: string; text: string }[];
  symptoms: {
    symptom: string;
    status: 'present' | 'absent' | 'historical' | 'uncertain' | 'other_person' | 'conflicting';
    clarification_source?: string | null;
    mentions: {
      source_id: string; quote: string; context: string; start: number; end: number;
      status: string; time_course?: string | null; severity?: string | null; location?: string | null;
    }[];
  }[];
  unrecognized_sources: string[];
  unrecognized_fragments?: { source_id: string; start: number; end: number; quote: string }[];
  limitations: string[];
}


export interface UrgencyContext {
  clinician_concern?: boolean | null;
  new_confusion?: boolean | null;
  pregnant?: boolean | null;
  oxygen_scale?: 'standard' | 'individualized' | 'unknown';
}

export interface UrgencyAssessment {
  status: 'URGENT_REVIEW' | 'INCOMPLETE' | 'OUTSIDE_SCOPE' | 'NO_TRIGGER_DETECTED';
  action: string;
  acknowledged: boolean;
  assessed_at: string;
  rules_version: string;
  rules_review_status: string;
  reasons: { rule_id: string; explanation: string; source: string }[];
  missing_information: string[];
  limitations: string[];
}
