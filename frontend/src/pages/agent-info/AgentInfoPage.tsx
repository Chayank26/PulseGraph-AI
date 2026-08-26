import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, LogIn, Terminal, Stethoscope, FileImage, BookOpen, Heart, AlertOctagon } from 'lucide-react';
import './AgentInfoPage.css';

interface AgentDetails {
  id: string;
  stage: string;
  name: string;
  tagline: string;
  color: string;
  icon: React.ReactNode;
  overview: string;
  inputsConsumed: string[];
  algorithmModel: string;
  outputsProduced: string[];
  clinicalSignificance: string;
}

const AGENT_DETAILS_MAP: Record<string, AgentDetails> = {
  triage: {
    id: 'triage',
    stage: 'STAGE 01 • PRIORITY ALPHA',
    name: 'TRIAGE & RISK STRATIFICATION AGENT',
    tagline: 'Objective Clinical Risk Scoring & Intake Parameter Standardization',
    color: '#E19B4C',
    icon: <Heart size={28} className="text-black" />,
    overview: 'The Triage Agent is the first line of automated clinical processing in PulseGraph AI. It ingests unstructured emergency nurse intake notes, chief complaints, and presenting vital signs, standardizing them into objective clinical risk scores to dictate diagnostic urgency.',
    inputsConsumed: [
      'Raw Nursing Intake Notes & Presenting Complaints',
      'Vital Signs: Heart Rate, Blood Pressure, SpO2, Resp Rate, Temperature',
      'Demographics: Patient Age, Biological Gender, History of Cardiac Risk Factors',
      'Laboratory Values: Initial Troponin & Electrocardiogram (ECG) Scores'
    ],
    algorithmModel: 'HEART Score for Major Adverse Cardiac Events (MACE) & Wells Criteria for Pulmonary Embolism (PE)',
    outputsProduced: [
      'Calculated HEART Score (0 - 10) with 6-week MACE risk estimation',
      'Calculated Wells PE Probability Score',
      'Vitals Clinical Reference Threshold Warning Flags',
      'Dynamic ClinicalDataRequest trigger if essential risk scoring parameters are missing'
    ],
    clinicalSignificance: 'Ensures that high-risk chest pain patients are immediately flagged for expedited telemetry, early invasive catheterization, or urgent CT angiography without relying on subjective initial impressions.'
  },
  imaging: {
    id: 'imaging',
    stage: 'STAGE 02 • MULTIMODAL VISION',
    name: 'MULTIMODAL VISION AGENT',
    tagline: 'CheXNet Deep Neural Radiograph Inference & Heatmap Analysis',
    color: '#C8D2E6',
    icon: <FileImage size={28} className="text-black" />,
    overview: 'The Multimodal Vision Agent processes radiological scans (Chest X-Rays / CT DICOM files) using pre-trained deep convolutional neural networks to detect 14 distinct pulmonary and cardiac pathologies.',
    inputsConsumed: [
      'PA / AP Chest Radiograph DICOM Image Scans',
      'Patient Positioning & FOV Metadata (KVP, MAS)',
      'Clinical Triage Context & Prior Pathology Findings'
    ],
    algorithmModel: 'DenseNet-121 Neural Network Architecture (CheXNet Pre-Trained on NIH ChestX-ray14 dataset)',
    outputsProduced: [
      'Multi-Label Pathology Probability Scores (Consolidation, Pneumothorax, Cardiomegaly, Pleural Effusion)',
      'Class Activation Feature Maps for anatomical region localization',
      'Structured Radiology Impression Summaries for Attending Physician review'
    ],
    clinicalSignificance: 'Provides rapid AI radiograph screening within seconds of acquisition, highlighting subtle infiltrates, effusions, or pneumothoraces to accelerate emergency diagnostic decisions.'
  },
  diagnostic: {
    id: 'diagnostic',
    stage: 'STAGE 03 • PROBABILISTIC REASONING',
    name: 'DIFFERENTIAL DIAGNOSIS AGENT',
    tagline: 'Bayesian Synthesis of Disease Hypotheses & Workup Planning',
    color: '#D6E3F5',
    icon: <Stethoscope size={28} className="text-black" />,
    overview: 'The Differential Diagnosis Agent correlates objective triage risk scores, vital signs, patient history, and vision inference findings to synthesize a ranked list of differential diagnosis candidates.',
    inputsConsumed: [
      'Triage HEART & Wells Risk Stratification Results',
      'CheXNet Chest Radiograph Inference Findings',
      'Patient Chronic Condition History & Medication Profile'
    ],
    algorithmModel: 'Bayesian Probabilistic Inference & Structured LLM Reasoning Engine',
    outputsProduced: [
      'Ranked Differential Candidates with Bayesian likelihood percentages',
      'Official ICD-10 Code Classifications (e.g., I21.4 NSTEMI, I26.99 PE, I30.9 Pericarditis)',
      'Bulleted Clinical Rationale linking symptoms to disease hypotheses',
      'Ordered Diagnostic Workup Checklist (Serial Troponins, CTPA, D-Dimer)'
    ],
    clinicalSignificance: 'Helps emergency physicians avoid premature closure cognitive bias by maintaining a broad, structured differential diagnosis backed by objective evidence.'
  },
  evidence: {
    id: 'evidence',
    stage: 'STAGE 04 • PUBMED & GUIDELINE RAG',
    name: 'EVIDENCE RAG AGENT',
    tagline: 'Vector Retrieval of AHA/ACC Guidelines & Peer-Reviewed Literature',
    color: '#CBD7C0',
    icon: <BookOpen size={28} className="text-black" />,
    overview: 'The Evidence RAG Agent searches indexed clinical practice guidelines (AHA/ACC, ESC, CHEST) and peer-reviewed PubMed literature to ground AI recommendations in verified medical consensus.',
    inputsConsumed: [
      'Synthesized Differential Hypotheses',
      'Calculated Risk Stratification Scores',
      'Indexed Clinical Guideline Vector Database'
    ],
    algorithmModel: 'Vector Cosine Embedding RAG (Retrieval-Augmented Generation) & PubMed Medical Indexing',
    outputsProduced: [
      'Relevant Guideline Excerpts & Class I/II Clinical Recommendations',
      'Vector Similarity Match Scores (e.g., 96% Vector Match)',
      'Direct DOI Links and PubMed Citation Identifiers'
    ],
    clinicalSignificance: 'Ensures all clinical recommendations align strictly with current peer-reviewed evidence and national society guidelines, giving physicians full citation transparency.'
  },
  safety: {
    id: 'safety',
    stage: 'STAGE 05 • PHARMACOLOGICAL AUDIT',
    name: 'SAFETY AGENT',
    tagline: 'Pharmacological Interaction Audit & Organ Clearance Monitoring',
    color: '#D5D4CD',
    icon: <AlertOctagon size={28} className="text-black" />,
    overview: 'The Safety Agent conducts rigorous checks for drug-drug interactions, allergy contraindications, and organ function thresholds before any treatment plan is presented for approval.',
    inputsConsumed: [
      'Patient Current Medications & Documented Allergies',
      'Renal Clearance (eGFR) & Hepatic Function (ALT/AST) Lab Values',
      'Proposed Pharmacological Recommendations & Risk Scores'
    ],
    algorithmModel: 'RxNorm & DrugBank Pharmacological DB Lookups + Clinical Safety Rule Engines',
    outputsProduced: [
      'Severity-Coded Safety Flags (CRITICAL, HIGH, MODERATE)',
      'Organ Clearance Monitor Status (eGFR, HAS-BLED Bleeding Risk)',
      'Specific Contraindication Alerts (e.g., Metoprolol block for bradycardia)'
    ],
    clinicalSignificance: 'Prevents adverse drug events (ADEs), drug-drug interactions, and inappropriate dosing in renal or hepatic impairment.'
  },
  symbolic: {
    id: 'symbolic',
    stage: 'STAGE 06 • DETERMINISTIC GOVERNANCE',
    name: 'SYMBOLIC GUARDRAIL AGENT',
    tagline: 'Non-Negotiable Deterministic Rules & Human Breakpoint Governance',
    color: '#2A2B2E',
    icon: <Terminal size={28} className="text-[#E19B4C]" />,
    overview: 'The Symbolic Guardrail Agent is the non-probabilistic governance layer of PulseGraph AI. It evaluates strict IF-THEN medical safety rules independently of Large Language Models to prevent AI hallucinations and enforce mandatory human sign-off.',
    inputsConsumed: [
      'Entire Multimodal Clinical Session State Payload',
      'Safety Agent Flags & Diagnostic Workup Requests',
      'Deterministic Hospital Medical Safety Ruleset'
    ],
    algorithmModel: 'Deterministic First-Order Symbolic Rule Engine (IF-THEN Logic Evaluation)',
    outputsProduced: [
      'Enforced Rule Override Logs (e.g., Heparin Bolus Dosage Cap at 4,000 Units)',
      'Mandatory Physician Action Directives',
      'Human-in-the-Loop Review Breakpoint Enforcement before EHR Export'
    ],
    clinicalSignificance: 'Guarantees that probabilistic AI cannot execute actions that breach critical medical safety rules, keeping the attending physician in total operational control.'
  }
};

export const AgentInfoPage: React.FC = () => {
  const { agentId } = useParams<{ agentId: string }>();
  const agentKey = (agentId || 'triage').toLowerCase();
  const agent = AGENT_DETAILS_MAP[agentKey] || AGENT_DETAILS_MAP.triage;

  return (
    <div className="agent-info-shell">
      {/* Public Header Bar */}
      <header className="agent-info-header">
        <Link to="/" className="flex items-center gap-3 no-underline">
          <div className="w-8 h-8 rounded-lg bg-[#2A2B2E] text-[#E19B4C] font-mono font-bold text-sm flex items-center justify-center border border-black">
            PG
          </div>
          <div>
            <h1 className="font-serif italic text-lg font-bold text-[#1A1A1C] leading-none">PulseGraph</h1>
            <p className="text-[10px] font-mono uppercase text-[#66655C]">Neuro-Symbolic Clinical AI</p>
          </div>
        </Link>

        <Link to="/" className="agent-info-btn-secondary">
          <ArrowLeft size={14} />
          <span>Back to Landing Page</span>
        </Link>
      </header>

      {/* Main Content Area */}
      <main className="agent-info-main">
        {/* Agent Overview Hero Box */}
        <div
          className="agent-info-hero"
          style={{ backgroundColor: agent.color, color: agent.id === 'symbolic' ? '#FFFFFF' : '#000000' }}
        >
          <div className="flex items-center justify-between">
            <div className="agent-info-meta" style={{ color: agent.id === 'symbolic' ? '#E19B4C' : 'rgba(0,0,0,0.7)' }}>
              {agent.stage}
            </div>
            <div className="p-2.5 rounded-2xl bg-white/20 backdrop-blur-xs border border-black/10">
              {agent.icon}
            </div>
          </div>

          <h1 className="agent-info-title" style={{ color: agent.id === 'symbolic' ? '#FFFFFF' : '#000000' }}>
            {agent.name}
          </h1>

          <p className="agent-info-subtitle" style={{ color: agent.id === 'symbolic' ? '#D1D5DB' : 'rgba(0,0,0,0.85)' }}>
            "{agent.tagline}"
          </p>

          <div className="pt-2 text-sm font-sans leading-relaxed max-w-4xl" style={{ color: agent.id === 'symbolic' ? '#E5E7EB' : '#1A1A1C' }}>
            {agent.overview}
          </div>
        </div>

        {/* Technical Architecture Breakdown Grid */}
        <div className="agent-info-grid">
          {/* Inputs Consumed */}
          <div className="agent-info-card">
            <h3 className="agent-info-card-title">
              <span className="w-3 h-3 rounded-full bg-[#E19B4C]"></span>
              <span>Clinical Inputs Consumed</span>
            </h3>
            <ul className="agent-info-list">
              {agent.inputsConsumed.map((inp, idx) => (
                <li key={idx}>
                  <span className="bullet"></span>
                  <span>{inp}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Algorithm & AI Model */}
          <div className="agent-info-card">
            <h3 className="agent-info-card-title">
              <span className="w-3 h-3 rounded-full bg-black"></span>
              <span>Algorithm & Reasoning Model</span>
            </h3>
            <div className="text-sm font-semibold text-black bg-[#FAF8F2] border border-[#DCD8BE] rounded-xl p-4">
              {agent.algorithmModel}
            </div>
            <p className="text-xs text-[#66655C] leading-relaxed">
              Executes asynchronously within the LangGraph orchestrator thread with automatic PostgresSaver checkpointing.
            </p>
          </div>

          {/* Outputs Produced */}
          <div className="agent-info-card">
            <h3 className="agent-info-card-title">
              <span className="w-3 h-3 rounded-full bg-[#E19B4C]"></span>
              <span>Outputs Produced</span>
            </h3>
            <ul className="agent-info-list">
              {agent.outputsProduced.map((out, idx) => (
                <li key={idx}>
                  <span className="bullet"></span>
                  <span>{out}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Clinical Significance */}
          <div className="agent-info-card">
            <h3 className="agent-info-card-title">
              <span className="w-3 h-3 rounded-full bg-[#1C3829]"></span>
              <span>Clinical Safety & Value</span>
            </h3>
            <p className="text-sm text-[#1A1A1C] leading-relaxed font-semibold bg-[#E8EFE2] border border-[#BDCCA6] rounded-xl p-4 text-[#1C3829]">
              "{agent.clinicalSignificance}"
            </p>
          </div>
        </div>

        {/* Action CTA Bar */}
        <div className="agent-info-cta-bar">
          <div>
            <h4 className="font-serif italic text-xl font-bold text-black">Ready to test the interactive pipeline?</h4>
            <p className="text-xs text-[#66655C] font-mono mt-0.5">
              Sign in with your physician credentials to run real multi-agent clinical sessions.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link to="/" className="agent-info-btn-secondary">
              <ArrowLeft size={14} />
              <span>Back to Landing Page</span>
            </Link>

            <Link to="/login" className="agent-info-btn-primary">
              <LogIn size={15} />
              <span>Sign In to Access Workspace</span>
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full bg-[#F5F3EB] border-t border-[#E2DFC9] py-4 text-center text-xs font-mono text-[#8C8A7B]">
        PulseGraph AI Clinical Decision Support Engine — Human Clinical Review Mandatory.
      </footer>
    </div>
  );
};
