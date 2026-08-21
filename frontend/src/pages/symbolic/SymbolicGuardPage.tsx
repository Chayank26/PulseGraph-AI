import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { ShieldCheck, Lock, AlertOctagon, CheckSquare, Terminal } from 'lucide-react';
import './SymbolicGuardPage.css';

export const SymbolicGuardPage: React.FC = () => {
  const { session } = useWorkflow();
  const rawOverrides = session.state.symbolic_overrides;

  const overrides = (rawOverrides && rawOverrides.length > 0) ? rawOverrides : [
    {
      rule_id: 'SYM-001-HEPARIN-CAP',
      severity: 'CRITICAL' as const,
      message: 'Unfractionated Heparin initial IV bolus capped at 4,000 Units due to HAS-BLED bleeding risk score >= 3.',
      deterministic_rule: 'IF (has_bled_score >= 3 AND patient_age >= 65) THEN MAX_INITIAL_HEPARIN_BOLUS = 4000_UNITS AND REQUIRE_ATTENDING_SIGN_OFF = TRUE',
      action_required: 'Attending physician must explicitly confirm reduced initial heparin bolus weight before EHR order export.',
      triggered_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      governance_status: 'PENDING_PEER_REVIEW' as const
    },
    {
      rule_id: 'SYM-002-CONTRAST-NEPHRO',
      severity: 'HIGH' as const,
      message: 'CT Pulmonary Angiogram IV contrast protocol requires pre-procedural normal saline hydration due to eGFR < 60 mL/min.',
      deterministic_rule: 'IF (eGFR < 60 AND planned_procedure == "CT_ANGIOGRAPHY") THEN ENFORCE_NS_HYDRATION_PROTOCOL = TRUE',
      action_required: 'Order 0.9% Normal Saline IV infusion at 1 mL/kg/h for 6 hours pre-and-post imaging scan.',
      triggered_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      governance_status: 'APPROVED' as const
    },
    {
      rule_id: 'SYM-003-BRADYCARDIA-BLOCK',
      severity: 'CRITICAL' as const,
      message: 'Absolute hard-stop: Metoprolol administration BLOCKED due to HR < 50 bpm.',
      deterministic_rule: 'IF (heart_rate < 50_BPM) THEN BLOCK_BETA_BLOCKER_ADMINISTRATION = TRUE AND NOTIFY_CARDIOLOGY = TRUE',
      action_required: 'Immediate discontinuation of negative chronotropic agents; obtain urgent 12-lead ECG.',
      triggered_at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      governance_status: 'APPROVED' as const
    }
  ];

  return (
    <div className="symbolic-shell animate-fade-in font-sans">
      {/* Header Banner */}
      <div className="symbolic-banner">
        <div>
          <div className="symbolic-banner-meta">
            <Lock size={14} />
            <span>NEURO-SYMBOLIC DETERMINISTIC LAYER</span>
          </div>
          <h1 className="symbolic-banner-title">
            SYMBOLIC GUARDRAIL AGENT
          </h1>
          <p className="symbolic-banner-subtitle">
            Evaluates non-negotiable deterministic safety rules independently of probabilistic LLMs.
          </p>
        </div>

        <div className="symbolic-banner-badge">
          <ShieldCheck size={16} />
          <span>STATUS: ACTIVE & ENFORCED</span>
        </div>
      </div>

      {/* Concept Explanation Banner */}
      <div className="symbolic-concept-box">
        <h3 className="font-serif italic text-2xl font-bold text-black">
          Why Deterministic Symbolic Guardrails?
        </h3>
        <p className="text-xs text-[#4A4943] leading-relaxed font-sans font-normal max-w-4xl">
          Unlike pure Large Language Model systems that rely solely on probabilistic pattern matching, PulseGraph enforces strict symbolic rule engines. If a probabilistic LLM recommendation violates a deterministic medical safety threshold (such as heparin dosage caps, absolute allergy contraindications, or organ clearance limits), the Symbolic Guardrail automatically triggers a mandatory override and requires explicit clinician authorization.
        </p>
      </div>

      {/* Active Symbolic Rules List */}
      <div className="space-y-6">
        <h3 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C] flex items-center gap-2">
          <Terminal size={16} className="text-black" />
          <span>EVALUATED DETERMINISTIC SYMBOLIC RULES ({overrides.length})</span>
        </h3>

        <div className="space-y-6">
          {overrides.map((rule, idx) => (
            <div
              key={idx}
              className="symbolic-rule-card"
            >
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-[#E2DFC9] pb-4">
                <div className="flex items-center gap-3">
                  <span className="bg-[#2A2B2E] text-white font-mono text-xs font-bold px-3 py-1.5 rounded-md uppercase">
                    RULE ID: {rule.rule_id}
                  </span>
                  <span className="bg-red-800 text-white text-[10px] font-mono font-bold uppercase tracking-wider px-3 py-1 rounded-full">
                    {rule.severity} OVERRIDE
                  </span>
                </div>

                <div className="bg-[#CBD7C0] text-[#1C3829] border border-[#9DB08F] px-4 py-1.5 rounded-full font-mono text-xs font-bold uppercase flex items-center gap-1.5">
                  <CheckSquare size={14} />
                  <span>GOVERNANCE: {rule.governance_status}</span>
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-[10px] font-mono uppercase text-[#66655C] font-bold">Deterministic Logic Statement</span>
                <div className="symbolic-code-block">
                  <code>{rule.deterministic_rule}</code>
                </div>
              </div>

              <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-1">
                <span className="text-[10px] font-mono uppercase text-[#66655C] font-bold">Clinical Safety Message</span>
                <p className="font-serif italic text-sm text-black font-semibold">
                  "{rule.message}"
                </p>
              </div>

              <div className="bg-[#FFF3C4] border border-[#E6C200] rounded-xl p-4 text-xs text-[#8C6D00] font-semibold flex items-center gap-2">
                <AlertOctagon size={16} className="flex-shrink-0" />
                <span>Mandatory Action Required: {rule.action_required}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
