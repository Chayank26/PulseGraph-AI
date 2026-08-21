import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { ShieldAlert, CheckCircle2 } from 'lucide-react';
import './SafetyPage.css';

export const SafetyPage: React.FC = () => {
  const { session, agentStatuses } = useWorkflow();
  const safetyFlags = session.state.safety_flags || [];
  const status = agentStatuses.safety || 'COMPLETED';

  return (
    <div className="safety-shell animate-fade-in font-sans">
      {/* Header Banner */}
      <div className="safety-banner">
        <div>
          <div className="safety-banner-meta">
            AGENT 05 • PHARMACOLOGICAL & CONTRAINDICATION AUDIT
          </div>
          <h1 className="safety-banner-title">
            SAFETY AGENT
          </h1>
          <p className="safety-banner-subtitle">
            Audits drug-drug interactions, allergy contraindications, and organ clearance thresholds.
          </p>
        </div>

        <div className="safety-banner-badge">
          <CheckCircle2 size={16} className="text-[#D5D4CD]" />
          <span>STATUS: {status}</span>
        </div>
      </div>

      {/* Safety Flags List */}
      <div className="space-y-6">
        <h3 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C]">
          DETECTED CLINICAL SAFETY FLAGS ({safetyFlags.length})
        </h3>

        <div className="space-y-4">
          {safetyFlags.map((flag, idx) => {
            let badgeStyle = 'bg-[#F7D8D8] text-[#8C2A2A] border-[#EAAFA0]';
            if (flag.severity === 'CRITICAL') {
              badgeStyle = 'bg-red-800 text-white border-black animate-pulse';
            } else if (flag.severity === 'MODERATE') {
              badgeStyle = 'bg-[#FFF3C4] text-[#8C6D00] border-[#E6C200]';
            }

            return (
              <div
                key={idx}
                className="safety-card"
              >
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-[#E2DFC9] pb-3">
                  <div className="flex items-center gap-2">
                    <ShieldAlert size={18} className="text-red-700" />
                    <h4 className="font-bold text-sm text-black">{flag.category}</h4>
                  </div>
                  <span className={`text-[10px] font-mono font-bold uppercase tracking-wider px-3 py-1 rounded-full border ${badgeStyle}`}>
                    {flag.severity} SEVERITY
                  </span>
                </div>

                <p className="text-xs text-[#1A1A1C] leading-relaxed font-normal bg-white border border-[#DCD8BE] rounded-xl p-4">
                  {flag.description}
                </p>

                <div className="flex items-center justify-between text-[10px] font-mono text-[#8C8A7B] pt-1">
                  <span>Source Agent: {flag.source_agent}</span>
                  <span>Flagged At: {flag.flagged_at}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
