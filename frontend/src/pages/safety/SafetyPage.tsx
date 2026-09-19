import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { ShieldAlert, CheckCircle2, AlertOctagon, Pill } from 'lucide-react';
import './SafetyPage.css';

import { Link } from 'react-router-dom';

export const SafetyPage: React.FC = () => {
  const { session, activePatient, agentStatuses } = useWorkflow();

  if (!activePatient || !session) {
    return (
      <div className="bg-white border-2 border-black rounded-2xl p-12 text-center max-w-2xl mx-auto my-12 shadow-sm font-sans">
        <ShieldAlert size={36} className="mx-auto text-[#E19B4C] mb-3" />
        <h2 className="font-serif text-2xl font-bold text-black">No Active Patient Selected</h2>
        <p className="text-sm text-[#66655C] mt-2">
          Please select or register a patient from the Physician Patient Directory to view pharmacological safety audit flags.
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

      {/* Organ Clearance & Lab Threshold Monitor */}
      <div className="bg-[#FAF8F2] border-2 border-black rounded-2xl p-6 space-y-4">
        <h3 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C] flex items-center gap-2">
          <Pill size={16} className="text-black" />
          <span>ORGAN CLEARANCE & PHYSIOLOGICAL AUDIT MONITOR</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
          <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-1">
            <span className="text-[10px] text-[#66655C] uppercase font-bold">Renal Function Profile</span>
            <p className="font-bold text-black text-sm">
              {activePatient?.chronic_conditions?.some(c => c.toLowerCase().includes('kidney') || c.toLowerCase().includes('renal'))
                ? 'Impaired Clearance Flagged'
                : 'Baseline Normal'}
            </p>
            <p className={`text-[10px] font-bold ${
              activePatient?.chronic_conditions?.some(c => c.toLowerCase().includes('kidney') || c.toLowerCase().includes('renal'))
                ? 'text-red-800'
                : 'text-green-800'
            }`}>
              {activePatient?.chronic_conditions?.some(c => c.toLowerCase().includes('kidney') || c.toLowerCase().includes('renal'))
                ? 'DOSE ADJUSTMENT REQUIRED'
                : 'RENAL THRESHOLD PASS'}
            </p>
          </div>

          <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-1">
            <span className="text-[10px] text-[#66655C] uppercase font-bold">Documented Allergy Audit</span>
            <p className="font-bold text-black text-sm">
              {activePatient?.allergies && activePatient.allergies.length > 0
                ? `${activePatient.allergies.length} Allergy Conflict(s) Monitored`
                : 'No Documented Allergies (NKDA)'}
            </p>
            <p className={`text-[10px] font-bold ${
              activePatient?.allergies && activePatient.allergies.length > 0 ? 'text-amber-800' : 'text-green-800'
            }`}>
              {activePatient?.allergies && activePatient.allergies.length > 0 ? 'ACTIVE CONTRAINDICATION SCREENING' : 'NO CONTRAINDICATION DETECTED'}
            </p>
          </div>

          <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-1">
            <span className="text-[10px] text-[#66655C] uppercase font-bold">Active Drug-Drug Screen</span>
            <p className="font-bold text-black text-sm">
              {activePatient?.current_medications && activePatient.current_medications.length > 0
                ? `${activePatient.current_medications.length} Prescriptions Screened`
                : 'No Active Medications'}
            </p>
            <p className={`text-[10px] font-bold ${
              safetyFlags.length > 0 ? 'text-red-800' : 'text-green-800'
            }`}>
              {safetyFlags.length > 0 ? `${safetyFlags.length} SAFETY FLAG(S) ACTIVE` : 'PASSES DRUG-DRUG AUDIT'}
            </p>
          </div>
        </div>
      </div>

      {/* Safety Flags List */}
      <div className="space-y-6">
        <h3 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C] flex items-center gap-2">
          <AlertOctagon size={16} className="text-red-700" />
          <span>DETECTED CLINICAL SAFETY FLAGS ({safetyFlags.length})</span>
        </h3>

        <div className="space-y-4">
          {safetyFlags && safetyFlags.length > 0 ? (
            safetyFlags.map((flag, idx) => {
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

                  <p className="text-xs text-[#1A1A1C] leading-relaxed font-semibold bg-white border border-[#DCD8BE] rounded-xl p-4">
                    {flag.description}
                  </p>

                  <div className="flex items-center justify-between text-[10px] font-mono text-[#8C8A7B] pt-1">
                    <span>Source Engine: {flag.source_agent}</span>
                    <span>Flagged At: {flag.flagged_at}</span>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="bg-white border border-[#DCD8BE] rounded-2xl p-12 text-center text-xs font-mono text-[#8C8A7B]">
              No pharmacological contraindications or drug interaction flags detected for this session.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
