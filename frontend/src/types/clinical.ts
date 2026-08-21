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
  disease_name: string;
  icd10_code: string;
  likelihood_percentage: number;
  clinical_rationale: string;
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
  status: 'PENDING' | 'RESOLVED';
  created_at: string;
  clinician_response?: Record<string, any>;
}

export interface ClinicalState {
  patient_id: string;
  demographics: PatientDemographics;
  raw_notes: string[];
  vitals: VitalSigns;
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
