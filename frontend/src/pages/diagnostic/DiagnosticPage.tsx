import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { CheckCircle2, AlertTriangle } from 'lucide-react';
import './DiagnosticPage.css';

export const DiagnosticPage: React.FC = () => {
  const { session, agentStatuses } = useWorkflow();
  const differentials = session.state.differentials || [];
  const status = agentStatuses.diagnostic || 'COMPLETED';

  return (
    <div className="diagnostic-shell animate-fade-in">
      {/* Header Banner */}
      <div className="diagnostic-banner">
        <div>
          <div className="diagnostic-banner-meta">
            AGENT 03 • PROBABILISTIC CLINICAL REASONING
          </div>
          <h1 className="diagnostic-banner-title">
            DIFFERENTIAL DIAGNOSIS AGENT
          </h1>
          <p className="diagnostic-banner-subtitle">
            Synthesizes Bayesian probabilistic likelihoods, ICD-10 disease candidates, and rationale.
          </p>
        </div>

        <div className="diagnostic-banner-badge">
          <CheckCircle2 size={16} className="text-[#D6E3F5]" />
          <span>STATUS: {status}</span>
        </div>
      </div>

      {/* Disclaimers Bar */}
      <div className="bg-[#FAF8F2] border border-[#E2DFC9] rounded-xl p-4 flex items-center gap-3 text-xs text-[#66655C]">
        <AlertTriangle size={18} className="text-[#E19B4C] flex-shrink-0" />
        <p>
          <strong className="font-bold text-black uppercase">Decision Support Disclaimer:</strong> These differential candidates are AI-generated probabilistic estimations based on multimodal state inputs. Final diagnosis requires attending physician evaluation.
        </p>
      </div>

      {/* Differentials List */}
      <div className="space-y-6">
        {differentials.map((diff, idx) => (
          <div
            key={idx}
            className="diagnostic-card"
          >
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 border-b border-[#E2DFC9] pb-4">
              <div className="flex items-center gap-3">
                <span className="w-8 h-8 rounded-full bg-[#2A2B2E] text-white font-mono text-sm font-bold flex items-center justify-center">
                  {idx + 1}
                </span>
                <div>
                  <h3 className="font-serif italic text-2xl font-bold text-black">{diff.disease_name}</h3>
                  <span className="font-mono text-xs font-semibold text-[#66655C]">ICD-10: {diff.icd10_code}</span>
                </div>
              </div>

              <div className="diagnostic-pct-badge">
                {diff.likelihood_percentage}% LIKELIHOOD
              </div>
            </div>

            <div className="space-y-3 font-sans">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#66655C]">
                Clinical Rationale
              </h4>
              <p className="text-xs text-[#1A1A1C] leading-relaxed font-normal bg-white border border-[#DCD8BE] rounded-xl p-4">
                {diff.clinical_rationale}
              </p>
            </div>

            <div className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#66655C]">
                Recommended Diagnostic Workup
              </h4>
              <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs font-semibold text-black">
                {diff.recommended_workup.map((w, i) => (
                  <li key={i} className="bg-white border border-[#DCD8BE] rounded-lg p-2.5 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#E19B4C]"></span>
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
