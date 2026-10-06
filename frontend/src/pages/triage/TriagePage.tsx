import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { CheckCircle2, Activity, AlertTriangle } from 'lucide-react';
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
            Ingests chief complaints, vital signs, and calculates supported HEART, CURB-65, and Wells clinical risk scores.
          </p>
        </div>

        <div className="triage-banner-badge">
          <CheckCircle2 size={16} className="text-[#E19B4C]" />
          <span>STATUS: {status}</span>
        </div>
      </div>

      {state.presentation?.back_pain_assessment && (
        <section className="bg-white border border-[#DCD8BE] rounded-xl p-5 space-y-3" aria-label="Low-back assessment">
          <h2 className="font-bold">Low-back clinician assessment</h2>
          <p>{state.presentation.back_pain_assessment.status.replaceAll('_', ' ')}</p>
          {Object.entries(state.presentation.back_pain_assessment.answers).map(([key, value]) => <p key={key}>{key.replace('back_review_', '').replaceAll('_', ' ')}: {value.replaceAll('_', ' ')}</p>)}
          {state.presentation.back_pain_assessment.limitations.map(text => <p className="text-sm" key={text}>{text}</p>)}
          <a href={state.presentation.back_pain_assessment.source} target="_blank" rel="noreferrer" className="underline">Assessment source: NICE NG59</a>
        </section>
      )}
      {state.presentation?.routing && (
        <section className="bg-white border border-[#DCD8BE] rounded-xl p-5 space-y-3" aria-label="Assessment routing">
          <h3 className="triage-panel-title">ASSESSMENT ROUTING</h3>
          <p className="text-sm">Presentation groups: {Object.keys(state.presentation.routing.groups).map(group => group.replace(/_/g, ' ')).join(', ') || 'Undifferentiated'}</p>
          {state.presentation.routing.pathways.map(pathway => (
            <div key={pathway.key} className="text-sm border-t pt-2">
              <strong>{pathway.name} — {pathway.status.replace(/_/g, ' ')}</strong>
              <p className="text-xs">{pathway.rationale}</p>
              {pathway.unavailable_fields.length > 0 && <p className="text-xs">Unavailable: {pathway.unavailable_fields.join(', ')}</p>}
            </div>
          ))}
          {state.presentation.routing.requires_clinician_assessment && (
            <div role="status" className="bg-amber-50 border border-amber-600 rounded p-3">
              <strong>Clinician assessment required</strong>
              {state.presentation.routing.handoff_reasons.map(reason => <p className="text-sm" key={reason}>{reason}</p>)}
              <p className="text-xs">Supported assessments may continue; unresolved concerns remain outside automated coverage.</p>
            </div>
          )}
        </section>
      )}

      {state.presentation && (
        <section className="bg-white border border-[#DCD8BE] rounded-xl p-5 space-y-3" aria-label="Structured presentation">
          <h3 className="triage-panel-title">STRUCTURED PRESENTATION</h3>
          <p className="text-xs text-[#66655C]">Review extracted statements against their source. Missing information remains unknown.</p>
          {state.presentation.symptoms.length === 0 && <p className="text-sm">No supported symptom phrases recognized. Review the original complaint and notes.</p>}
          {state.presentation.symptoms.map(symptom => (
            <div key={symptom.symptom} className="border-t border-[#DCD8BE] pt-3">
              <p className="text-sm font-bold">{symptom.symptom.replace(/_/g, ' ')} — {symptom.status.replace(/_/g, ' ')}</p>
              {symptom.clarification_source && <p className="text-xs">Current status confirmed by clinician.</p>}
              {symptom.mentions.map((mention, index) => (
                <div key={`${mention.source_id}-${mention.start}-${index}`} className="text-xs mt-2">
                  <blockquote className="whitespace-pre-wrap">“{mention.context}”</blockquote>
                  <p className="text-[#66655C]">Source: {mention.source_id} · {mention.status.replace(/_/g, ' ')}</p>
                  <p>{[mention.time_course, mention.severity, mention.location].filter(Boolean).join(' · ')}</p>
                </div>
              ))}
            </div>
          ))}
          {state.presentation.unrecognized_sources.length > 0 && <p className="text-xs">Some source text has no recognized symptoms. Review: {state.presentation.unrecognized_sources.join(', ')}.</p>}
          {state.presentation.limitations.map(limit => <p key={limit} className="text-xs text-[#66655C]">{limit}</p>)}
        </section>
      )}

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
            {state.risk_scores.length ? state.risk_scores.map((score) => (
              <div className="triage-score-card" key={score.score_name}>
                <div className="triage-score-header">
                  <h4 className="triage-score-title">{score.score_name}</h4>
                  <span className="triage-score-value">{score.score_value} points</span>
                </div>
                <p className="text-xs text-black">{score.recommendation}</p>
                <div className="space-y-2 pt-2">
                  <span className="text-[10px] font-mono uppercase text-[#66655C] font-bold">Inputs used</span>
                  <div className="triage-param-grid">
                    {Object.entries(score.parameters_used || {}).map(([key, value]) => (
                      <div key={key} className="triage-param-chip">
                        <span className="triage-param-key">{key.replace(/_/g, ' ')}</span>
                        <span className="triage-param-val">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )) : (
              <div className="bg-white border border-[#DCD8BE] rounded-xl p-6 text-xs font-mono text-[#8C8A7B]">
                No risk scores are available. This does not establish low risk.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
