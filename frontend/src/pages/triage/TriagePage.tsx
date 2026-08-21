import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { CheckCircle2 } from 'lucide-react';
import './TriagePage.css';

export const TriagePage: React.FC = () => {
  const { session, agentStatuses } = useWorkflow();
  const state = session.state;
  const status = agentStatuses.triage || 'COMPLETED';

  return (
    <div className="triage-shell animate-fade-in">
      {/* Header Banner matching reference image */}
      <div className="triage-banner">
        <div>
          <div className="triage-banner-meta">
            AGENT 01 • STAGE PRIORITY ALPHA
          </div>
          <h1 className="triage-banner-title">
            TRIAGE AGENT
          </h1>
          <p className="triage-banner-subtitle">
            Ingests chief complaints, vital signs, and calculates objective clinical risk scores.
          </p>
        </div>

        <div className="triage-banner-badge">
          <CheckCircle2 size={16} className="text-[#E19B4C]" />
          <span>STATUS: {status}</span>
        </div>
      </div>

      {/* Main Analysis Grid */}
      <div className="triage-grid">
        {/* Left Column: Input Data */}
        <div className="triage-input-panel">
          <h3 className="triage-panel-title">
            INGESTED CLINICAL INPUTS
          </h3>

          <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-2">
            <span className="text-[10px] font-mono uppercase text-[#66655C]">Chief Complaint</span>
            <p className="text-xs font-semibold text-black leading-relaxed">
              {state.demographics?.chief_complaint}
            </p>
          </div>

          <div className="space-y-2">
            <span className="text-[10px] font-mono uppercase text-[#66655C]">Raw Clinical Notes</span>
            <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 font-mono text-xs space-y-1 text-[#4A4943] max-h-60 overflow-y-auto">
              {state.raw_notes.map((note, i) => (
                <p key={i} className="leading-snug">{note}</p>
              ))}
            </div>
          </div>
        </div>

        {/* Center & Right Column: Calculated Risk Scores & Triage Analysis */}
        <div className="lg:col-span-2 space-y-6">
          <h3 className="triage-panel-title">
            CALCULATED CLINICAL RISK SCORES
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {state.risk_scores.map((score, idx) => (
              <div key={idx} className="triage-score-card">
                <div className="triage-score-header">
                  <h4 className="triage-score-title">{score.score_name}</h4>
                  <span className="triage-score-value">
                    SCORE: {score.score_value}
                  </span>
                </div>

                <div className="triage-risk-badge">
                  RISK LEVEL: {score.risk_level}
                </div>

                <p className="triage-rec-text">
                  <strong className="font-bold text-black">Recommendation:</strong> {score.recommendation}
                </p>

                <div className="pt-3 border-t border-[#E2DFC9] text-[10px] font-mono text-[#8C8A7B]">
                  Parameters Used: {JSON.stringify(score.parameters_used)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
