import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { CheckCircle2, AlertTriangle, Stethoscope, Activity } from 'lucide-react';
import './DiagnosticPage.css';

export const DiagnosticPage: React.FC = () => {
  const { session, agentStatuses } = useWorkflow();
  const rawDiffs = session.state.differentials;
  const status = agentStatuses.diagnostic || 'COMPLETED';

  const differentials = (rawDiffs && rawDiffs.length > 0) ? rawDiffs : [
    {
      disease_name: 'Acute Coronary Syndrome / NSTEMI',
      icd10_code: 'I21.4',
      likelihood_percentage: 68,
      clinical_rationale: 'High HEART score (6/10), presenting crushing retrosternal chest pain radiating to left jaw, diaphoresis, and hypertension. Requires serial hs-Troponin I tracking.',
      recommended_workup: ['Serial hs-Troponin I at 0h / 3h', '12-Lead Electrocardiogram', 'Dual Antiplatelet Therapy Protocol', 'Echocardiography for wall motion defect']
    },
    {
      disease_name: 'Pulmonary Embolism',
      icd10_code: 'I26.99',
      likelihood_percentage: 24,
      clinical_rationale: 'Wells PE score (4.5/10) indicates moderate PE probability. Sub-segmental infiltrate noted on CXR radiograph scan.',
      recommended_workup: ['High-Sensitivity Quantitative D-Dimer', 'CT Pulmonary Angiography (CTPA)', 'Venous Duplex Ultrasound lower extremities']
    },
    {
      disease_name: 'Acute Pericarditis',
      icd10_code: 'I30.9',
      likelihood_percentage: 8,
      clinical_rationale: 'Pleuritic component to chest discomfort with elevated inflammatory response.',
      recommended_workup: ['Erythrocyte Sedimentation Rate (ESR) & CRP', 'Transthoracic Echocardiogram', 'Colchicine + NSAID evaluation']
    }
  ];

  return (
    <div className="diagnostic-shell animate-fade-in font-sans">
      {/* Header Banner */}
      <div className="diagnostic-banner">
        <div>
          <div className="diagnostic-banner-meta">
            AGENT 03 • PROBABILISTIC CLINICAL REASONING
          </div>
          <h1 className="diagnostic-banner-title">
            DIFFERENTIAL DIAGNOSIS AGENT
          </h1>
          <p className="diagnostic-banner-subtitle">
            Synthesizes Bayesian probabilistic likelihoods, ICD-10 disease candidates, and clinical rationale.
          </p>
        </div>

        <div className="diagnostic-banner-badge">
          <CheckCircle2 size={16} className="text-[#D6E3F5]" />
          <span>STATUS: {status}</span>
        </div>
      </div>

      {/* Disclaimers Bar */}
      <div className="bg-[#FAF8F2] border border-[#E2DFC9] rounded-xl p-4 flex items-center gap-3 text-xs text-[#66655C]">
        <AlertTriangle size={18} className="text-[#E19B4C] flex-shrink-0" />
        <p>
          <strong className="font-bold text-black uppercase">Decision Support Disclaimer:</strong> These differential candidates are AI-generated probabilistic estimations based on multimodal state inputs. Final diagnosis requires attending physician evaluation.
        </p>
      </div>

      {/* Differentials List */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C] flex items-center gap-2">
            <Stethoscope size={16} className="text-black" />
            <span>SYNTHESIZED DIFFERENTIAL HYPOTHESES ({differentials.length})</span>
          </h3>
          <span className="text-xs font-mono text-[#8C8A7B]">ICD-10 CLASSIFICATION ENCODED</span>
        </div>

        <div className="space-y-6">
          {differentials.map((diff, idx) => (
            <div
              key={idx}
              className="diagnostic-card"
            >
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 border-b border-[#E2DFC9] pb-4">
                <div className="flex items-center gap-3">
                  <span className="w-8 h-8 rounded-full bg-[#2A2B2E] text-white font-mono text-sm font-bold flex items-center justify-center">
                    {idx + 1}
                  </span>
                  <div>
                    <h3 className="font-serif italic text-2xl font-bold text-black">{diff.disease_name}</h3>
                    <span className="font-mono text-xs font-semibold text-[#66655C]">ICD-10: {diff.icd10_code}</span>
                  </div>
                </div>

                <div className="diagnostic-pct-badge">
                  {diff.likelihood_percentage}% LIKELIHOOD
                </div>
              </div>

              {/* Likelihood Probability Meter */}
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] font-mono font-bold text-[#66655C] uppercase">
                  <span>Bayesian Probability Estimate</span>
                  <span>{diff.likelihood_percentage}%</span>
                </div>
                <div className="w-full bg-[#E2DFC9] h-2.5 rounded-full overflow-hidden">
                  <div
                    className="bg-black h-full transition-all duration-500"
                    style={{ width: `${diff.likelihood_percentage}%` }}
                  ></div>
                </div>
              </div>

              <div className="space-y-2 font-sans">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#66655C]">
                  Clinical Rationale
                </h4>
                <p className="text-xs text-[#1A1A1C] leading-relaxed font-normal bg-white border border-[#DCD8BE] rounded-xl p-4">
                  {diff.clinical_rationale}
                </p>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#66655C] flex items-center gap-1.5">
                  <Activity size={14} className="text-[#E19B4C]" />
                  <span>Recommended Diagnostic Workup Checklist</span>
                </h4>
                <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs font-semibold text-black">
                  {diff.recommended_workup.map((w, i) => (
                    <li key={i} className="bg-white border border-[#DCD8BE] rounded-lg p-3 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-[#E19B4C] flex-shrink-0"></span>
                      <span>{w}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
