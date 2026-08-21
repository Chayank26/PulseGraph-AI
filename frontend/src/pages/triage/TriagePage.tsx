import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { CheckCircle2, Activity, Heart, AlertTriangle } from 'lucide-react';
import './TriagePage.css';

export const TriagePage: React.FC = () => {
  const { session, agentStatuses } = useWorkflow();
  const state = session.state;
  const status = agentStatuses.triage || 'COMPLETED';

  // Default HEART & Wells risk scores if none calculated yet
  const heartScore = state.risk_scores.find(s => s.score_name.includes('HEART')) || {
    score_name: 'HEART Score for Major Cardiac Events',
    score_value: 6,
    risk_level: 'HIGH_RISK',
    recommendation: 'High risk (50-65% MACE risk at 6 weeks). Immediate admission, telemetry, and early invasive strategy recommended.',
    parameters_used: { history_score: 2, ecg_score: 1, age_score: 2, risk_factors_score: 1, troponin_score: 0 }
  };

  const wellsScore = state.risk_scores.find(s => s.score_name.includes('Wells')) || {
    score_name: 'Wells PE Score',
    score_value: 4.5,
    risk_level: 'MODERATE_RISK',
    recommendation: 'Moderate probability of Pulmonary Embolism. High-sensitivity D-Dimer test or CT Pulmonary Angiography indicated.',
    parameters_used: { clinical_dvt_signs: 3.0, pe_likely: 1.5, heart_rate_over_100: 0 }
  };

  return (
    <div className="triage-shell animate-fade-in font-sans">
      {/* Header Banner */}
      <div className="triage-banner">
        <div>
          <div className="triage-banner-meta">
            AGENT 01 • STAGE PRIORITY ALPHA
          </div>
          <h1 className="triage-banner-title">
            TRIAGE & RISK STRATIFICATION AGENT
          </h1>
          <p className="triage-banner-subtitle">
            Ingests chief complaints, vital signs, and calculates objective HEART and Wells clinical risk scores.
          </p>
        </div>

        <div className="triage-banner-badge">
          <CheckCircle2 size={16} className="text-[#E19B4C]" />
          <span>STATUS: {status}</span>
        </div>
      </div>

      {/* Main Analysis Layout */}
      <div className="triage-grid">
        {/* Left Column: Intake Demographics & Vitals Monitor */}
        <div className="triage-left-panel">
          <div className="triage-input-panel">
            <h3 className="triage-panel-title flex items-center gap-2">
              <Activity size={16} className="text-[#E19B4C]" />
              <span>INGESTED CLINICAL INPUTS</span>
            </h3>

            <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-2">
              <span className="text-[10px] font-mono uppercase text-[#66655C] font-bold">Presenting Complaint</span>
              <p className="text-xs font-semibold text-black leading-relaxed">
                {state.demographics?.chief_complaint || 'Acute retrosternal chest pain radiating to left jaw with severe diaphoresis.'}
              </p>
            </div>

            {/* Vitals Clinical Range Card */}
            <div className="space-y-2">
              <span className="text-[10px] font-mono uppercase text-[#66655C] font-bold">VITAL SIGNS MONITOR</span>
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="bg-white border border-[#DCD8BE] rounded-lg p-2.5">
                  <span className="text-[9px] text-[#66655C] uppercase block">Heart Rate</span>
                  <span className="font-bold text-black text-sm">{state.vitals?.heart_rate_bpm || 98} bpm</span>
                </div>
                <div className="bg-white border border-[#DCD8BE] rounded-lg p-2.5">
                  <span className="text-[9px] text-[#66655C] uppercase block">Blood Pressure</span>
                  <span className="font-bold text-black text-sm">{state.vitals?.systolic_bp_mmhg || 154}/{state.vitals?.diastolic_bp_mmhg || 92}</span>
                </div>
                <div className="bg-white border border-[#DCD8BE] rounded-lg p-2.5">
                  <span className="text-[9px] text-[#66655C] uppercase block">SpO2</span>
                  <span className="font-bold text-black text-sm">{state.vitals?.spo2_percent || 94}%</span>
                </div>
                <div className="bg-white border border-[#DCD8BE] rounded-lg p-2.5">
                  <span className="text-[9px] text-[#66655C] uppercase block">Resp Rate</span>
                  <span className="font-bold text-black text-sm">{state.vitals?.resp_rate_bpm || 22}/min</span>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <span className="text-[10px] font-mono uppercase text-[#66655C] font-bold">Raw Clinical Notes</span>
              <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 font-mono text-xs space-y-1 text-[#4A4943] max-h-48 overflow-y-auto">
                {state.raw_notes.map((note, i) => (
                  <p key={i} className="leading-snug">{note}</p>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Calculated Risk Scores & Scoring Engine Breakdowns */}
        <div className="triage-right-panel">
          <h3 className="triage-panel-title">
            OBJECTIVE CLINICAL RISK CALCULATORS
          </h3>

          <div className="space-y-6">
            {/* HEART Score Breakdown Card */}
            <div className="triage-score-card">
              <div className="triage-score-header">
                <div>
                  <div className="flex items-center gap-2">
                    <Heart size={18} className="text-red-700" />
                    <h4 className="triage-score-title">{heartScore.score_name}</h4>
                  </div>
                  <p className="text-xs font-mono text-[#66655C] mt-0.5">Calculated 6-Week Major Adverse Cardiac Event (MACE) Risk</p>
                </div>
                <span className="triage-score-value">
                  HEART SCORE: {heartScore.score_value} / 10
                </span>
              </div>

              <div className="flex items-center gap-3">
                <span className="bg-[#F7D8D8] text-[#8C2A2A] border border-[#EAAFA0] text-xs font-mono font-bold uppercase px-3 py-1 rounded-full">
                  RISK: {heartScore.risk_level}
                </span>
              </div>

              <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-1">
                <span className="text-[10px] font-mono uppercase text-[#66655C] font-bold">Clinical Directive</span>
                <p className="text-xs font-semibold text-black leading-relaxed">
                  {heartScore.recommendation}
                </p>
              </div>

              {/* Parameter Breakdown */}
              <div className="space-y-2 pt-2">
                <span className="text-[10px] font-mono uppercase text-[#66655C] font-bold">Scoring Component Breakdown</span>
                <div className="triage-param-grid">
                  {Object.entries(heartScore.parameters_used || {}).map(([key, val]) => (
                    <div key={key} className="triage-param-chip">
                      <span className="triage-param-key">{key.replace('_score', '')}</span>
                      <span className="triage-param-val">+{val}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Wells PE Score Breakdown Card */}
            <div className="triage-score-card">
              <div className="triage-score-header">
                <div>
                  <div className="flex items-center gap-2">
                    <AlertTriangle size={18} className="text-[#E19B4C]" />
                    <h4 className="triage-score-title">{wellsScore.score_name}</h4>
                  </div>
                  <p className="text-xs font-mono text-[#66655C] mt-0.5">Calculated Pulmonary Embolism Likelihood Score</p>
                </div>
                <span className="triage-score-value">
                  WELLS SCORE: {wellsScore.score_value}
                </span>
              </div>

              <div className="flex items-center gap-3">
                <span className="bg-[#FFF3C4] text-[#8C6D00] border border-[#E6C200] text-xs font-mono font-bold uppercase px-3 py-1 rounded-full">
                  RISK: {wellsScore.risk_level}
                </span>
              </div>

              <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-1">
                <span className="text-[10px] font-mono uppercase text-[#66655C] font-bold">Diagnostic Workup Recommendation</span>
                <p className="text-xs font-semibold text-black leading-relaxed">
                  {wellsScore.recommendation}
                </p>
              </div>

              {/* Parameter Breakdown */}
              <div className="space-y-2 pt-2">
                <span className="text-[10px] font-mono uppercase text-[#66655C] font-bold">Scoring Component Breakdown</span>
                <div className="triage-param-grid">
                  {Object.entries(wellsScore.parameters_used || {}).map(([key, val]) => (
                    <div key={key} className="triage-param-chip">
                      <span className="triage-param-key">{key.replace(/_/g, ' ')}</span>
                      <span className="triage-param-val">+{val}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
