import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { AuditTimeline } from '../../components/common/AuditTimeline';
import { Activity, PlayCircle } from 'lucide-react';
import './DashboardPage.css';

export const DashboardPage: React.FC = () => {
  const { session, runningAgentId, currentAgentProgressMessage } = useWorkflow();
  const state = session.state;

  const topRiskScore = state.risk_scores?.[0];

  return (
    <div className="dashboard-shell animate-fade-in">
      {/* Running Agent Active Banner */}
      {runningAgentId && (
        <div className="dashboard-running-banner animate-pulse">
          <div className="dashboard-running-left">
            <PlayCircle size={20} className="text-[#1E3A8A] animate-spin" />
            <div>
              <p className="dashboard-running-title">
                AGENT PIPELINE EXECUTING — {runningAgentId.toUpperCase()}
              </p>
              <p className="dashboard-running-msg">
                {currentAgentProgressMessage}
              </p>
            </div>
          </div>
          <span className="dashboard-running-badge">
            PROCESSING
          </span>
        </div>
      )}

      {/* Main Reference Image Layout Container */}
      <div className="dashboard-main-grid">
        {/* Left 8-Column Main Dashboard Area */}
        <div className="dashboard-left-col">
          {/* Hero Presentation Headline (Matching attached image "PULSE DEVIATION") */}
          <div className="pt-2">
            <h1 className="dashboard-hero-title">
              PULSE DEVIATION
            </h1>
            <p className="dashboard-hero-complaint">
              {state.demographics?.chief_complaint || 'Acute retrosternal chest pain radiating to jaw with diaphoresis.'}
            </p>
          </div>

          {/* Three-Column Editorial Data Row (Directly from reference image!) */}
          <div className="dashboard-editorial-row">
            {/* Column 1: DIFFERENTIAL DIAGNOSIS */}
            <div className="dashboard-editorial-col">
              <h3 className="dashboard-col-title">
                DIFFERENTIAL DIAGNOSIS
              </h3>
              {state.differentials && state.differentials.length > 0 ? (
                <ol className="dashboard-diff-list">
                  {state.differentials.slice(0, 3).map((diff, idx) => (
                    <li key={idx} className="dashboard-diff-item">
                      <span className="dashboard-diff-num">{idx + 1}.</span>
                      <span>{diff.disease_name.split(' (')[0]}</span>{' '}
                      <span className="dashboard-diff-pct">
                        ({diff.likelihood_percentage}%)
                      </span>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="text-xs text-[#8C8A7B] italic">Formulating differentials...</p>
              )}
            </div>

            {/* Column 2: IMAGING FINDINGS */}
            <div className="dashboard-editorial-col">
              <h3 className="dashboard-col-title">
                IMAGING FINDINGS
              </h3>
              <p className="dashboard-imaging-text">
                {state.imaging_data?.impression ||
                  'Sub-segmental filling defect noted in right lower lobe. Requires contrast-enhanced confirmation.'}
              </p>
            </div>

            {/* Column 3: RISK SCORE */}
            <div className="dashboard-editorial-col">
              <h3 className="dashboard-col-title">
                RISK SCORE
              </h3>
              {topRiskScore ? (
                <div className="dashboard-risk-score-box">
                  <p className="dashboard-risk-score-name">
                    {topRiskScore.score_name}: {topRiskScore.score_value}{' '}
                    <span className="dashboard-risk-score-level">
                      ({topRiskScore.risk_level.replace('_', ' ')})
                    </span>
                  </p>
                  <p className="dashboard-risk-rec">
                    <strong className="font-semibold text-black">Recommendation:</strong> {topRiskScore.recommendation}
                  </p>
                </div>
              ) : (
                <p className="text-xs text-[#8C8A7B] italic">Calculating risk scores...</p>
              )}
            </div>
          </div>

          {/* Patient Overview & Vitals Panel */}
          <div className="dashboard-patient-panel">
            <div className="dashboard-patient-panel-header">
              <h3 className="dashboard-patient-panel-title">
                <Activity size={16} className="text-[#E19B4C]" />
                <span>Patient Clinical Profile & Vital Signs</span>
              </h3>
              <span className="text-xs font-mono text-[#66655C] font-medium">
                MRN: {state.patient_id} • Age {state.demographics?.age} ({state.demographics?.gender})
              </span>
            </div>

            {/* Vital Signs Grid */}
            <div className="dashboard-vitals-grid">
              <div className="dashboard-vital-card">
                <span className="dashboard-vital-label">Heart Rate</span>
                <p className="dashboard-vital-value">
                  {state.vitals?.heart_rate_bpm || 98} <span className="text-xs font-normal">bpm</span>
                </p>
              </div>

              <div className="dashboard-vital-card">
                <span className="dashboard-vital-label">Blood Pressure</span>
                <p className="dashboard-vital-value">
                  {state.vitals?.systolic_bp_mmhg || 154}/{state.vitals?.diastolic_bp_mmhg || 92} <span className="text-xs font-normal">mmHg</span>
                </p>
              </div>

              <div className="dashboard-vital-card">
                <span className="dashboard-vital-label">SpO2 Saturation</span>
                <p className="dashboard-vital-value">
                  {state.vitals?.spo2_percent || 94}%
                </p>
              </div>

              <div className="dashboard-vital-card">
                <span className="dashboard-vital-label">Resp Rate</span>
                <p className="dashboard-vital-value">
                  {state.vitals?.resp_rate_bpm || 22} <span className="text-xs font-normal">/min</span>
                </p>
              </div>
            </div>

            {/* Medical History & Current Medications */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#1A1A1C] mb-2">
                  Relevant Clinical History
                </h4>
                <ul className="space-y-1 text-xs text-[#4A4943] list-disc list-inside">
                  {state.demographics?.relevant_history?.map((h, i) => (
                    <li key={i}>{h}</li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#1A1A1C] mb-2">
                  Active Medications
                </h4>
                <ul className="space-y-1 text-xs text-[#4A4943] list-disc list-inside font-mono">
                  {state.demographics?.current_medications?.map((m, i) => (
                    <li key={i}>{m}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Right 4-Column Audit Trail Panel */}
        <div className="dashboard-right-col">
          <AuditTimeline />
        </div>
      </div>
    </div>
  );
};
