import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { ShieldCheck, Lock, AlertOctagon, CheckSquare, Terminal } from 'lucide-react';
import './SymbolicGuardPage.css';

import { Link } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';

export const SymbolicGuardPage: React.FC = () => {
  const { session, activePatient } = useWorkflow();

  if (!activePatient || !session) {
    return (
      <div className="bg-white border-2 border-black rounded-2xl p-12 text-center max-w-2xl mx-auto my-12 shadow-sm font-sans">
        <AlertTriangle size={36} className="mx-auto text-[#E19B4C] mb-3" />
        <h2 className="font-serif text-2xl font-bold text-black">No Active Patient Selected</h2>
        <p className="text-sm text-[#66655C] mt-2">
          Please select or register a patient from the Physician Patient Directory to view deterministic symbolic guardrails.
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

  const overrides = session.state.symbolic_overrides || [];


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
          {overrides && overrides.length > 0 ? (
            overrides.map((rule, idx) => (
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
            ))
          ) : (
            <div className="bg-white border border-[#DCD8BE] rounded-2xl p-12 text-center text-xs font-mono text-[#8C8A7B]">
              No deterministic symbolic rule overrides triggered for this patient session.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
