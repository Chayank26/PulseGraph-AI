import React, { useState } from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { useAuth } from '../../context/AuthContext';
import { UserCheck, CheckCircle, XCircle, RotateCcw, FileCode, AlertOctagon, ShieldCheck } from 'lucide-react';
import { EhrExportModal } from '../../components/common/EhrExportModal';
import './ReviewPage.css';

export const ReviewPage: React.FC = () => {
  const { doctor } = useAuth();
  const { session, approveSession, rejectSession, reevaluateSession } = useWorkflow();
  const state = session.state;

  const [reviewNotes, setReviewNotes] = useState<string>('Reviewed risk scores, imaging findings, and safety flags. Recommendations approved.');
  const [reevalNotes, setReevalNotes] = useState<string>('Re-evaluate differential diagnosis considering serial troponin trend at 3h.');
  const [activeActionTab, setActiveActionTab] = useState<'APPROVE' | 'REEVAL' | 'REJECT'>('APPROVE');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [isEhrModalOpen, setIsEhrModalOpen] = useState<boolean>(false);

  const primaryDiff = state.differentials?.[0] || {
    disease_name: 'Acute Coronary Syndrome / NSTEMI',
    icd10_code: 'I21.4',
    likelihood_percentage: 68,
    clinical_rationale: 'High HEART score (6/10), presenting chest pain, and hypertensive vitals.'
  };

  const topRiskScore = state.risk_scores?.[0] || {
    score_name: 'HEART Score',
    score_value: 6,
    risk_level: 'HIGH_RISK',
    recommendation: 'High risk (50-65% MACE risk). Immediate admission and early invasive strategy.'
  };

  const handleApprove = async () => {
    setSubmitting(true);
    try {
      await approveSession(reviewNotes);
      setIsEhrModalOpen(true);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReevaluate = async () => {
    setSubmitting(true);
    try {
      await reevaluateSession(reevalNotes);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    setSubmitting(true);
    try {
      await rejectSession(reviewNotes);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="review-shell animate-fade-in font-sans">
      {/* Header Banner */}
      <div className="review-banner">
        <div>
          <div className="review-banner-meta">
            <UserCheck size={16} />
            <span>MANDATORY CLINICAL CHECKPOINT</span>
          </div>
          <h1 className="review-banner-title">
            HUMAN-IN-THE-LOOP REVIEW WORKBENCH
          </h1>
          <p className="review-banner-subtitle">
            Attending physician verification, decision sign-off, and FHIR R4 EHR export authorization.
          </p>
        </div>

        <div className="review-banner-badge">
          <span>STATUS: {session.status}</span>
        </div>
      </div>

      {/* Review Package Summary Grid */}
      <div className="review-grid">
        {/* Left Column: Differential & Findings Summary Package */}
        <div className="review-card">
          <h3 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C] flex items-center justify-between">
            <span>CLINICAL PACKAGE SUMMARY FOR APPROVAL</span>
            <span className="font-mono text-black">PATIENT: {session.patient_id}</span>
          </h3>

          {/* Primary Hypothesis */}
          <div className="space-y-3">
            <h4 className="font-serif italic text-xl font-bold text-black">Primary Diagnostic Hypothesis</h4>
            <div className="bg-white border-2 border-black rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-base text-black">{primaryDiff.disease_name}</span>
                <span className="font-mono text-xs font-bold text-black bg-[#D6E3F5] px-3 py-1 rounded-full border border-black">
                  ICD-10: {primaryDiff.icd10_code} • {primaryDiff.likelihood_percentage}%
                </span>
              </div>
              <p className="text-xs text-[#4A4943] leading-relaxed font-sans">
                {primaryDiff.clinical_rationale}
              </p>
            </div>
          </div>

          {/* Risk Score Summary */}
          <div className="space-y-3">
            <h4 className="font-serif italic text-xl font-bold text-black">Calculated Risk Stratification</h4>
            <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-2 text-xs">
              <div className="flex items-center justify-between font-mono font-bold text-black">
                <span>{topRiskScore.score_name} Score: {topRiskScore.score_value}</span>
                <span className="bg-[#F7D8D8] text-[#8C2A2A] px-2.5 py-0.5 rounded border border-[#EAAFA0] font-bold">
                  {topRiskScore.risk_level}
                </span>
              </div>
              <p className="text-[#66655C]">{topRiskScore.recommendation}</p>
            </div>
          </div>

          {/* Safety & Guardrail Compliance */}
          <div className="space-y-3">
            <h4 className="font-serif italic text-xl font-bold text-black">Safety & Guardrail Compliance</h4>
            <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between text-black font-semibold">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck size={14} className="text-green-700" />
                  <span>Deterministic Symbolic Overrides:</span>
                </span>
                <span className="font-bold">{state.symbolic_overrides?.length || 0} Rule(s) Evaluated</span>
              </div>
              <div className="flex items-center justify-between text-black font-semibold">
                <span className="flex items-center gap-1.5">
                  <AlertOctagon size={14} className="text-red-700" />
                  <span>Pharmacological Safety Flags:</span>
                </span>
                <span className="font-bold">{state.safety_flags?.length || 0} Flag(s) Flagged</span>
              </div>
            </div>
          </div>

          {session.status === 'APPROVED' && (
            <button
              onClick={() => setIsEhrModalOpen(true)}
              className="w-full bg-[#2A2B2E] text-white py-3 rounded-full font-mono text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 hover:bg-black shadow-md"
            >
              <FileCode size={15} className="text-[#E19B4C]" />
              <span>Inspect FHIR R4 EHR Export Bundle</span>
            </button>
          )}
        </div>

        {/* Right Column: Interactive Clinician Action Workbench */}
        <div className="review-card">
          <h3 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C]">
            PHYSICIAN DECISION & AUTHORIZATION
          </h3>

          {/* Action Tabs */}
          <div className="grid grid-cols-3 gap-2 p-1 bg-[#EAE7DA] rounded-xl font-mono text-xs font-bold">
            <button
              onClick={() => setActiveActionTab('APPROVE')}
              className={`py-2 rounded-lg transition ${
                activeActionTab === 'APPROVE' ? 'bg-[#2A2B2E] text-white shadow-sm' : 'text-[#66655C] hover:text-black'
              }`}
            >
              1. Approve
            </button>
            <button
              onClick={() => setActiveActionTab('REEVAL')}
              className={`py-2 rounded-lg transition ${
                activeActionTab === 'REEVAL' ? 'bg-[#2A2B2E] text-white shadow-sm' : 'text-[#66655C] hover:text-black'
              }`}
            >
              2. Re-Evaluate
            </button>
            <button
              onClick={() => setActiveActionTab('REJECT')}
              className={`py-2 rounded-lg transition ${
                activeActionTab === 'REJECT' ? 'bg-[#2A2B2E] text-white shadow-sm' : 'text-[#66655C] hover:text-black'
              }`}
            >
              3. Reject
            </button>
          </div>

          {/* Tab 1: Approve & Persist */}
          {activeActionTab === 'APPROVE' && (
            <div className="space-y-4 text-xs font-sans">
              <div className="p-4 rounded-xl border border-[#98A885] bg-[#E8EFE2] space-y-1">
                <h5 className="font-bold text-[#2C421C] uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle size={15} />
                  <span>Option 1: Approve & Export to EHR</span>
                </h5>
                <p className="text-[#2C421C]/80 leading-relaxed">
                  Persists final CDS recommendations to PostgreSQL, appends attending clinician digital signature to audit trail, and exports payload to hospital EHR (FHIR R4).
                </p>
              </div>

              <div>
                <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1 font-bold">
                  Attending Physician Verification Notes
                </label>
                <textarea
                  rows={3}
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  className="w-full bg-white border border-[#DCD8BE] rounded-xl p-3 text-xs text-black focus:outline-none focus:ring-2 focus:ring-black"
                />
              </div>

              {doctor && (
                <div className="bg-white border border-[#DCD8BE] rounded-xl p-3 text-[11px] font-mono text-[#66655C] flex items-center justify-between">
                  <span>Digital Signature: {doctor.full_name} ({doctor.department})</span>
                  <span>{new Date().toLocaleDateString()}</span>
                </div>
              )}

              <button
                onClick={handleApprove}
                disabled={submitting || session.status === 'APPROVED'}
                className="w-full bg-[#1C3829] text-white py-3.5 rounded-full font-mono text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 hover:bg-black transition shadow-lg"
              >
                <CheckCircle size={15} className="text-[#9DB08F]" />
                <span>{submitting ? 'Persisting to PostgreSQL & Exporting EHR...' : session.status === 'APPROVED' ? 'Session Approved & Persisted' : 'Approve Recommendations & Export EHR'}</span>
              </button>
            </div>
          )}

          {/* Tab 2: Request Re-Evaluation */}
          {activeActionTab === 'REEVAL' && (
            <div className="space-y-4 text-xs font-sans">
              <div className="p-4 rounded-xl border border-[#DCD8BE] bg-white space-y-1">
                <h5 className="font-bold text-black uppercase tracking-wider flex items-center gap-1.5">
                  <RotateCcw size={15} />
                  <span>Option 2: Request Graph Re-Evaluation Loop</span>
                </h5>
                <p className="text-[#66655C] leading-relaxed">
                  Appends physician feedback notes to graph state, increments iteration counter, and re-invokes multi-agent execution pipeline.
                </p>
              </div>

              <div>
                <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1 font-bold">
                  Physician Feedback Instructions for Graph Re-Run
                </label>
                <textarea
                  rows={3}
                  value={reevalNotes}
                  onChange={(e) => setReevalNotes(e.target.value)}
                  className="w-full bg-white border border-[#DCD8BE] rounded-xl p-3 text-xs text-black focus:outline-none focus:ring-2 focus:ring-black"
                />
              </div>

              <button
                onClick={handleReevaluate}
                disabled={submitting}
                className="w-full bg-[#2A2B2E] text-white py-3.5 rounded-full font-mono text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 hover:bg-black transition shadow-lg"
              >
                <RotateCcw size={15} className="text-[#E19B4C]" />
                <span>{submitting ? 'Re-Invoking LangGraph Pipeline...' : 'Submit Feedback & Re-Evaluate'}</span>
              </button>
            </div>
          )}

          {/* Tab 3: Reject & Manual Takeover */}
          {activeActionTab === 'REJECT' && (
            <div className="space-y-4 text-xs font-sans">
              <div className="p-4 rounded-xl border border-[#EAAFA0] bg-[#F7D8D8] space-y-1">
                <h5 className="font-bold text-[#8C2A2A] uppercase tracking-wider flex items-center gap-1.5">
                  <XCircle size={15} />
                  <span>Option 3: Reject AI CDS & Manual Takeover</span>
                </h5>
                <p className="text-[#8C2A2A]/80 leading-relaxed">
                  Overrides AI decision support recommendations entirely and transfers patient session directly to manual attending physician management.
                </p>
              </div>

              <div>
                <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1 font-bold">
                  Rejection & Manual Takeover Rationale
                </label>
                <textarea
                  rows={3}
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  placeholder="State reason for overriding decision support recommendations..."
                  className="w-full bg-white border border-[#DCD8BE] rounded-xl p-3 text-xs text-black focus:outline-none focus:ring-2 focus:ring-black"
                />
              </div>

              <button
                onClick={handleReject}
                disabled={submitting || session.status === 'REJECTED_MANUAL_TAKEOVER'}
                className="w-full bg-[#8C2A2A] text-white py-3.5 rounded-full font-mono text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 hover:bg-black transition shadow-lg"
              >
                <XCircle size={15} />
                <span>{submitting ? 'Processing Manual Takeover...' : session.status === 'REJECTED_MANUAL_TAKEOVER' ? 'Session Rejected (Manual Takeover)' : 'Reject Recommendations & Take Over'}</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* FHIR EHR Export Modal */}
      <EhrExportModal
        isOpen={isEhrModalOpen}
        onClose={() => setIsEhrModalOpen(false)}
        session={session}
      />
    </div>
  );
};
