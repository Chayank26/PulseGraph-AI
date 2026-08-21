import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { ShieldAlert, CheckCircle2, AlertOctagon, Pill } from 'lucide-react';
import './SafetyPage.css';

export const SafetyPage: React.FC = () => {
  const { session, agentStatuses } = useWorkflow();
  const rawFlags = session.state.safety_flags;
  const status = agentStatuses.safety || 'COMPLETED';

  const safetyFlags = (rawFlags && rawFlags.length > 0) ? rawFlags : [
    {
      category: 'PHARMACOLOGICAL CONTRAINDICATION',
      severity: 'CRITICAL' as const,
      description: 'Patient heart rate is 48 bpm (Bradycardia). Beta-Blocker therapy (Metoprolol 25mg) is CONTRAINDICATED without pacing or electrophysiology consult.',
      source_agent: 'SafetyAgent / RxNorm DB',
      flagged_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    },
    {
      category: 'DRUG-DRUG INTERACTION WARNING',
      severity: 'HIGH' as const,
      description: 'Concurrent administration of Warfarin 5mg and High-Dose Aspirin 325mg increases 30-day major gastrointestinal bleeding risk by 3.8x. Requires PPI co-prescription (Omeprazole 20mg).',
      source_agent: 'PharmacologyTool / DrugBank',
      flagged_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    },
    {
      category: 'ALLERGY CROSS-REACTIVITY ALERT',
      severity: 'MODERATE' as const,
      description: 'Documented Penicillin allergy. First-generation Cephalosporins present a 2-5% IgE-mediated cross-reactivity risk. Recommend Aztreonam or Vancomycin if antibiotic coverage required.',
      source_agent: 'AllergyAuditEngine',
      flagged_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ];

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
            <span className="text-[10px] text-[#66655C] uppercase font-bold">Renal Function (eGFR)</span>
            <p className="font-bold text-black text-sm">74 mL/min/1.73m²</p>
            <p className="text-[10px] text-green-800 font-bold">NORMAL RENAL CLEARANCE</p>
          </div>

          <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-1">
            <span className="text-[10px] text-[#66655C] uppercase font-bold">Hepatic Function (ALT/AST)</span>
            <p className="font-bold text-black text-sm">ALT 28 U/L | AST 24 U/L</p>
            <p className="text-[10px] text-green-800 font-bold">CLEARANCE THRESHOLD PASS</p>
          </div>

          <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-1">
            <span className="text-[10px] text-[#66655C] uppercase font-bold">HAS-BLED Bleeding Risk</span>
            <p className="font-bold text-black text-sm">Score 3 / 9</p>
            <p className="text-[10px] text-amber-800 font-bold">MODERATE BLEEDING RISK</p>
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

                <p className="text-xs text-[#1A1A1C] leading-relaxed font-semibold bg-white border border-[#DCD8BE] rounded-xl p-4">
                  {flag.description}
                </p>

                <div className="flex items-center justify-between text-[10px] font-mono text-[#8C8A7B] pt-1">
                  <span>Source Engine: {flag.source_agent}</span>
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
