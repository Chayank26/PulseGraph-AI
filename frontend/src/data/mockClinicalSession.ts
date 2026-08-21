import type { ClinicalSession, AgentInfo, Doctor } from '../types/clinical';

export const mockDoctor: Doctor = {
  doctor_id: 'DOC-88204',
  full_name: 'Dr. Sarah Chen, MD',
  email: 'sarah.chen@hospital.org',
  department: 'Emergency Medicine',
  role: 'Attending Physician'
};

export const mockClinicalSession: ClinicalSession = {
  session_id: 'SESSION_4492',
  patient_id: 'PATIENT 882-C',
  doctor_id: 'DOC-88204',
  thread_id: 'thread-SESS-4492',
  status: 'WAITING_FOR_CLINICIAN_REVIEW',
  current_step: 'human_review_required',
  created_at: '2026-08-20T08:14:00Z',
  updated_at: '2026-08-20T08:16:45Z',
  state: {
    patient_id: 'PATIENT 882-C',
    demographics: {
      patient_id: 'PATIENT 882-C',
      age: 68,
      gender: 'Male',
      chief_complaint: 'Acute retrosternal chest pain radiating to left jaw, severe diaphoresis',
      relevant_history: [
        'Hypertension (10+ yrs)',
        'Type 2 Diabetes Mellitus',
        'Hyperlipidemia',
        'Prior 30 pack-year smoking history'
      ],
      known_allergies: [
        'Penicillin (Rash)',
        'Shellfish (Mild Utricaria)'
      ],
      current_medications: [
        'Aspirin 81mg daily',
        'Atorvastatin 40mg daily',
        'Metformin 1000mg BID',
        'Lisinopril 20mg daily'
      ]
    },
    raw_notes: [
      '68yo male presents to ER with acute onset crushing chest pain at 13:30.',
      'Associated with diaphoresis, mild shortness of breath, and left arm numbness.',
      '[ACQUIRED CLINICAL DATA]: cxr_path = data/mock_patients/patient_001_cxr.png',
      '[ACQUIRED CLINICAL DATA]: history_score = 2',
      '[ACQUIRED CLINICAL DATA]: ecg_score = 2',
      '[ACQUIRED CLINICAL DATA]: troponin_score = 2',
      '[ACQUIRED CLINICAL DATA]: cardiac_risk_factors_count = 3'
    ],
    vitals: {
      heart_rate_bpm: 98,
      systolic_bp_mmhg: 154,
      diastolic_bp_mmhg: 92,
      resp_rate_bpm: 22,
      spo2_percent: 94,
      temperature_celsius: 36.8
    },
    risk_scores: [
      {
        score_name: 'HEART Score',
        score_value: 7,
        risk_level: 'HIGH_RISK',
        recommendation: 'Immediate cardiology consult, continuous cardiac monitoring, and serial troponins.',
        parameters_used: {
          history: 2,
          ecg: 2,
          age: 1,
          risk_factors: 1,
          troponin: 1
        },
        calculated_at: '2026-08-20T08:14:15Z'
      },
      {
        score_name: 'Wells PE Score',
        score_value: 3.0,
        risk_level: 'MODERATE_RISK',
        recommendation: 'D-Dimer testing indicated prior to CT pulmonary angiography.',
        parameters_used: {
          tachycardia: 1.5,
          alternative_diagnosis_less_likely: 1.5
        },
        calculated_at: '2026-08-20T08:14:18Z'
      }
    ],
    differentials: [
      {
        disease_name: 'Acute Coronary Syndrome (NSTEMI / STEMI)',
        icd10_code: 'I24.9',
        likelihood_percentage: 82,
        clinical_rationale: 'High HEART score (7), ST-segment depression in anterior leads V2-V4, elevated initial troponin I (1.42 ng/mL), and classic retrosternal radiation.',
        recommended_workup: [
          'Immediate 12-lead ECG repeat',
          'Urgent Cardiac Catheterization / PCI',
          'Dual antiplatelet therapy (DAPT)',
          'Heparin anticoagulation'
        ]
      },
      {
        disease_name: 'Pulmonary Embolism',
        icd10_code: 'I26.99',
        likelihood_percentage: 14,
        clinical_rationale: 'Hypoxemia (SpO2 94%), tachypnea (RR 22), sub-segmental opacity on initial portable CXR, and moderate Wells PE score.',
        recommended_workup: [
          'STAT High-sensitivity D-Dimer',
          'CT Pulmonary Angiography (CTPA) if renal function allows'
        ]
      },
      {
        disease_name: 'Acute Pericarditis',
        icd10_code: 'I30.9',
        likelihood_percentage: 4,
        clinical_rationale: 'Considered due to substernal chest pain, but lack of positional change relief or PR depression makes ACS far more probable.',
        recommended_workup: [
          'Echocardiogram to assess pericardial effusion'
        ]
      }
    ],
    imaging_data: {
      image_path: '/assets/sample_cxr.png',
      modality: 'CHEST_XRAY_PA',
      findings: [
        {
          finding_name: 'Sub-segmental filling defect / opacity',
          confidence: 0.88,
          region: 'Right Lower Lobe',
          clinical_significance: 'HIGH'
        },
        {
          finding_name: 'Enlarged Cardiac Silhouette',
          confidence: 0.92,
          region: 'Mediastinum / Cardiac Apex',
          clinical_significance: 'MODERATE'
        }
      ],
      impression: 'Sub-segmental filling defect noted in right lower lobe with mild cardiomegaly. Requires contrast-enhanced CT confirmation if clinically indicated.',
      analyzed_at: '2026-08-20T08:14:40Z'
    },
    evidence: [
      {
        title: '2023 AHA/ACC Guidelines for the Management of Patients With Acute Coronary Syndromes',
        authors: 'Gulati M, Levy PD, Mukherjee D, et al.',
        source: 'Circulation / AHA Guidelines',
        url_or_doi: '10.1161/CIR.0000000000001029',
        snippet: 'Patients presenting with acute chest pain and a HEART Score ≥ 7 fall into the High-Risk category (over 50% 6-week MACE risk). Immediate invasive evaluation or cardiac catheterization is strongly recommended (Class I, Level A).',
        relevance_score: 0.96
      },
      {
        title: 'Diagnostic Accuracy of the HEART Score in Emergency Department Patients',
        authors: 'Six AJ, Backus BE, Kelder JC',
        source: 'Netherlands Heart Journal (PubMed)',
        url_or_doi: 'PMID: 18820732',
        snippet: 'The HEART score reliably stratifies ED chest pain patients. High-score cohorts (7-10) demonstrate a major adverse cardiac event rate of 50.1%, justifying urgent heparinization and cath lab activation.',
        relevance_score: 0.91
      }
    ],
    safety_flags: [
      {
        severity: 'HIGH',
        category: 'Drug-Drug Interaction Warning',
        description: 'Co-administration of high-dose Heparin with chronic Aspirin therapy increases bleeding risk (Moderate-to-High). Monitor PTT closely.',
        source_agent: 'Safety_Agent',
        flagged_at: '2026-08-20T08:15:02Z'
      },
      {
        severity: 'MODERATE',
        category: 'Renal Function Threshold Check',
        description: 'Patient age 68 with Type 2 Diabetes; eGFR check required prior to iodinated CTPA contrast injection to prevent Contrast-Induced Nephropathy (CIN).',
        source_agent: 'Safety_Agent',
        flagged_at: '2026-08-20T08:15:05Z'
      }
    ],
    symbolic_overrides: [
      {
        rule_id: 'SR-992',
        severity: 'CRITICAL',
        message: 'Rule SR-992: Proposed anticoagulant clearance threshold for patient requires deterministic safety check. Weight-adjusted Unfractionated Heparin bolus capped at maximum 4,000 Units initial IV load.',
        deterministic_rule: 'IF Age > 65 AND Renal Impairment Risk == TRUE THEN Max_Heparin_Bolus <= 4000 IU',
        action_required: 'Confirm reduced heparin bolus weight calculation before administering IV bolus.',
        triggered_at: '2026-08-20T08:15:10Z',
        governance_status: 'APPROVED'
      }
    ],
    audit_trail: [
      {
        timestamp: '14:02:11',
        agent_name: 'Triage_Agent',
        action: 'Ingested presenting clinical symptoms',
        details: 'Symptoms ingested: Retrosteranl pain, diaphoresis. Priority: High.'
      },
      {
        timestamp: '14:02:15',
        agent_name: 'Imaging_Vision_V4',
        action: 'CheXNet Multimodal DICOM Analysis',
        details: 'Analysis of CXR-202 shows enlarged cardiac silhouette.'
      },
      {
        timestamp: '14:02:18',
        agent_name: 'Symbolic_Guardrail_01',
        action: 'Deterministic Rule Evaluation',
        details: 'Safety check: No known allergies to Iodine contrast agents in record.'
      },
      {
        timestamp: '14:03:02',
        agent_name: 'Safety_Agent',
        action: 'Pharmacological Interaction Audit',
        details: 'Deterministic rule override: Heparin dose flagged for safety limit.'
      }
    ],
    current_step: 'human_review',
    authenticated_clinician: mockDoctor,
    approved_by_clinician: false,
    iteration_count: 0,
    re_evaluation_requested: false,
    pending_data_requests: []
  }
};

export const agentsList: AgentInfo[] = [
  {
    id: 'triage',
    number: '01',
    name: 'TRIAGE',
    shortName: 'Triage',
    tagline: 'Workflow: Priority Alpha',
    color: '#E19B4C',
    lightColor: '#F5C68D',
    status: 'COMPLETED',
    route: '/triage'
  },
  {
    id: 'imaging',
    number: '02',
    name: 'IMAGING',
    shortName: 'Imaging',
    tagline: 'Modality: MRI/CT',
    color: '#C8D2E6',
    lightColor: '#E8EEFA',
    status: 'COMPLETED',
    route: '/imaging'
  },
  {
    id: 'diagnostic',
    number: '03',
    name: 'DIFF. DX',
    shortName: 'Differential',
    tagline: 'Reasoning: Probabilistic',
    color: '#D6E3F5',
    lightColor: '#EEF4FD',
    status: 'COMPLETED',
    route: '/diagnostic'
  },
  {
    id: 'evidence',
    number: '04',
    name: 'EVIDENCE',
    shortName: 'Evidence',
    tagline: 'Retrieval: PubMed/Full',
    color: '#CBD7C0',
    lightColor: '#E8EFE2',
    status: 'COMPLETED',
    route: '/evidence'
  },
  {
    id: 'safety',
    number: '05',
    name: 'SAFETY',
    shortName: 'Safety',
    tagline: 'Layer: Symbolic Guard',
    color: '#D5D4CD',
    lightColor: '#EFEFEA',
    status: 'COMPLETED',
    route: '/safety'
  }
];
