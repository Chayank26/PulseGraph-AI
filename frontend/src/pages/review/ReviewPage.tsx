import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { UserCheck, CheckCircle, XCircle, RotateCcw } from 'lucide-react';
import './ReviewPage.css';

export const ReviewPage: React.FC = () => {
  const { session } = useWorkflow();
  const state = session.state;

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
            HUMAN-IN-THE-LOOP REVIEW
          </h1>
          <p className="review-banner-subtitle">
            The multi-agent graph is paused awaiting attending physician verification and sign-off.
          </p>
        </div>

        <div className="review-banner-badge">
          <span>STATUS: {session.status}</span>
        </div>
      </div>

      {/* Review Package Summary Grid */}
      <div className="review-grid">
        {/* Left Column: Differential Candidates Summary */}
        <div className="review-card">
          <h3 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C]">
            SUMMARY FOR PHYSICIAN APPROVAL
          </h3>

          <div className="space-y-3">
            <h4 className="font-serif italic text-xl font-bold text-black">Primary Diagnostic Hypothesis</h4>
            {state.differentials?.[0] && (
              <div className="bg-white border-2 border-black rounded-xl p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-base text-black">{state.differentials[0].disease_name}</span>
                  <span className="font-mono text-sm font-bold text-black bg-[#D6E3F5] px-3 py-1 rounded-full">
                    {state.differentials[0].likelihood_percentage}% Likelihood
                  </span>
                </div>
                <p className="text-xs text-[#4A4943] leading-relaxed font-sans">
                  {state.differentials[0].clinical_rationale}
                </p>
              </div>
            )}
          </div>

          <div className="space-y-3 pt-2">
            <h4 className="font-serif italic text-xl font-bold text-black">Safety & Guardrail Compliance</h4>
            <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-2 text-xs">
              <div className="flex items-center justify-between font-mono font-bold text-black">
                <span>Symbolic Overrides Evaluated:</span>
                <span>{state.symbolic_overrides?.length || 0} Rule(s)</span>
              </div>
              <div className="flex items-center justify-between font-mono font-bold text-black">
                <span>Pharmacological Safety Flags:</span>
                <span>{state.safety_flags?.length || 0} Flag(s)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Clinician Action Rationale */}
        <div className="review-card">
          <h3 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C]">
            CLINICIAN DECISION ACTIONS
          </h3>

          <div className="space-y-4 text-xs font-sans">
            <div className="p-4 rounded-xl border border-[#98A885] bg-[#E8EFE2] space-y-1">
              <h5 className="font-bold text-[#2C421C] uppercase tracking-wider flex items-center gap-1.5">
                <CheckCircle size={14} />
                <span>Option 1: Approve & Persist</span>
              </h5>
              <p className="text-[#2C421C]/80 leading-relaxed">
                Persists final CDS outputs to PostgreSQL, appends clinician digital signature to audit trail, and exports payload to hospital EHR (FHIR R4).
              </p>
            </div>

            <div className="p-4 rounded-xl border border-[#EAAFA0] bg-[#F7D8D8] space-y-1">
              <h5 className="font-bold text-[#8C2A2A] uppercase tracking-wider flex items-center gap-1.5">
                <XCircle size={14} />
                <span>Option 2: Reject & Manual Takeover</span>
              </h5>
              <p className="text-[#8C8A7B] leading-relaxed">
                Overrides AI decision support recommendations entirely and transfers patient session directly to manual attending physician management.
              </p>
            </div>

            <div className="p-4 rounded-xl border border-[#DCD8BE] bg-white space-y-1">
              <h5 className="font-bold text-black uppercase tracking-wider flex items-center gap-1.5">
                <RotateCcw size={14} />
                <span>Option 3: Request Re-Evaluation</span>
              </h5>
              <p className="text-[#66655C] leading-relaxed">
                Appends physician feedback notes to graph state and re-invokes multi-agent execution pipeline for secondary differential analysis.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
