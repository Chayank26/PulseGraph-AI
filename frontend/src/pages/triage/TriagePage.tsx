import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { CheckCircle2, Activity, Heart, AlertTriangle } from 'lucide-react';
import './TriagePage.css';

import { Link } from 'react-router-dom';

export const TriagePage: React.FC = () => {
  const { session, activePatient, agentStatuses } = useWorkflow();

  if (!activePatient || !session) {
    return (
      <div className="bg-white border-2 border-black rounded-2xl p-12 text-center max-w-2xl mx-auto my-12 shadow-sm">
        <AlertTriangle size={36} className="mx-auto text-[#E19B4C] mb-3" />
        <h2 className="font-serif text-2xl font-bold text-black">No Active Patient Selected</h2>
        <p className="text-sm text-[#66655C] mt-2">
          Please select or register a patient from the Physician Patient Directory to view triage risk scores and CDS evaluation.
        </p>
        <Link
          to="/dashboard"
          className="mt-6 inline-flex items-center gap-2 bg-[#1A1A1C] text-white font-mono text-xs font-bold uppercase px-6 py-3 rounded-full hover:bg-black transition"
        >
          <span>Go to Patient Directory &rarr;</span>
        </Link>
      </div>
    );
  }

  const state = session.state;
  const status = agentStatuses.triage || 'COMPLETED';

  const heartScore = state.risk_scores?.find(s => s.score_name.includes('HEART'));
  const wellsScore = state.risk_scores?.find(s => s.score_name.includes('Wells'));

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
                {state.demographics?.chief_complaint || 'No presenting complaint recorded.'}
              </p>
            </div>

            {/* Vitals Clinical Range Card */}
            <div className="space-y-2">
              <span className="text-[10px] font-mono uppercase text-[#66655C] font-bold">VITAL SIGNS MONITOR</span>
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="bg-white border border-[#DCD8BE] rounded-lg p-2.5">
                  <span className="text-[9px] text-[#66655C] uppercase block">Heart Rate</span>
                  <span className="font-bold text-black text-sm">{state.vitals?.heart_rate_bpm ? `${state.vitals.heart_rate_bpm} bpm` : '--'}</span>
                </div>
                <div className="bg-white border border-[#DCD8BE] rounded-lg p-2.5">
                  <span className="text-[9px] text-[#66655C] uppercase block">Blood Pressure</span>
                  <span className="font-bold text-black text-sm">{state.vitals?.systolic_bp_mmhg ? `${state.vitals.systolic_bp_mmhg}/${state.vitals.diastolic_bp_mmhg}` : '--'}</span>
                </div>
                <div className="bg-white border border-[#DCD8BE] rounded-lg p-2.5">
                  <span className="text-[9px] text-[#66655C] uppercase block">SpO2</span>
                  <span className="font-bold text-black text-sm">{state.vitals?.spo2_percent ? `${state.vitals.spo2_percent}%` : '--'}</span>
                </div>
                <div className="bg-white border border-[#DCD8BE] rounded-lg p-2.5">
                  <span className="text-[9px] text-[#66655C] uppercase block">Resp Rate</span>
                  <span className="font-bold text-black text-sm">{state.vitals?.resp_rate_bpm ? `${state.vitals.resp_rate_bpm}/min` : '--'}</span>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <span className="text-[10px] font-mono uppercase text-[#66655C] font-bold">Raw Clinical Notes</span>
              <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 font-mono text-xs space-y-1 text-[#4A4943] max-h-48 overflow-y-auto">
                {state.raw_notes && state.raw_notes.length > 0 ? (
                  state.raw_notes.map((note, i) => (
                    <p key={i} className="leading-snug">{note}</p>
                  ))
                ) : (
                  <p className="text-xs text-[#8C8A7B] italic">No raw clinical notes recorded.</p>
                )}
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
            {heartScore ? (
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
            ) : (
              <div className="bg-white border border-[#DCD8BE] rounded-xl p-6 text-center text-xs font-mono text-[#8C8A7B]">
                HEART score calculation pending... Run workflow pipeline to compute risk scores.
              </div>
            )}

            {/* Wells PE Score Breakdown Card */}
            {wellsScore ? (
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
            ) : (
              <div className="bg-white border border-[#DCD8BE] rounded-xl p-6 text-center text-xs font-mono text-[#8C8A7B]">
                Wells PE score calculation pending... Run workflow pipeline to compute risk scores.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
