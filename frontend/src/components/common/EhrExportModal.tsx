import React, { useState } from 'react';
import type { ClinicalSession } from '../../types/clinical';
import { FileCode, Copy, Check, Download, X, Server } from 'lucide-react';

interface EhrExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  session: ClinicalSession;
}

export const EhrExportModal: React.FC<EhrExportModalProps> = ({ isOpen, onClose, session }) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const topDifferential = session.state.differentials?.[0] || {
    disease_name: 'Diagnostic Synthesis Pending',
    icd10_code: 'R69',
    likelihood_percentage: 0
  };

  const topRiskScore = session.state.risk_scores?.[0] || {
    score_name: 'Clinical Risk Score',
    score_value: 0,
    risk_level: 'PENDING'
  };

  // Generate valid FHIR R4 DiagnosticReport / Bundle payload
  const fhirPayload = {
    resourceType: "Bundle",
    id: `fhir-bundle-${session.session_id}`,
    type: "document",
    timestamp: new Date().toISOString(),
    entry: [
      {
        resource: {
          resourceType: "DiagnosticReport",
          id: `report-${session.session_id}`,
          status: session.status === 'APPROVED' ? 'final' : 'preliminary',
          category: [
            {
              coding: [
                {
                  system: "http://terminology.hl7.org/CodeSystem/v2-0074",
                  code: "CDS",
                  display: "Clinical Decision Support"
                }
              ]
            }
          ],
          code: {
            coding: [
              {
                system: "http://loinc.org",
                code: "11526-1",
                display: "Pathology study diagnostic study report"
              }
            ],
            text: "PulseGraph Multimodal Neuro-Symbolic CDS Recommendation"
          },
          subject: {
            reference: `Patient/${session.patient_id}`,
            display: `Patient ${session.patient_id}`
          },
          performer: [
            {
              reference: `Practitioner/${session.doctor_id}`,
              display: `Attending Physician ${session.doctor_id}`
            }
          ],
          conclusion: `Primary Hypothesis: ${topDifferential.disease_name} (ICD-10: ${topDifferential.icd10_code}, Likelihood: ${topDifferential.likelihood_percentage}%). Calculated ${topRiskScore.score_name}: ${topRiskScore.score_value} (${topRiskScore.risk_level}).`,
          conclusionCode: [
            {
              coding: [
                {
                  system: "http://hl7.org/fhir/sid/icd-10",
                  code: topDifferential.icd10_code,
                  display: topDifferential.disease_name
                }
              ]
            }
          ]
        }
      },
      {
        resource: {
          resourceType: "RiskAssessment",
          id: `risk-${session.session_id}`,
          status: "final",
          subject: { reference: `Patient/${session.patient_id}` },
          prediction: [
            {
              outcome: { text: topRiskScore.score_name },
              qualitativeRisk: {
                coding: [
                  {
                    system: "http://terminology.hl7.org/CodeSystem/risk-probability",
                    code: topRiskScore.risk_level.toLowerCase(),
                    display: topRiskScore.risk_level
                  }
                ]
              }
            }
          ]
        }
      }
    ]
  };

  const jsonString = JSON.stringify(fhirPayload, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `FHIR_R4_Bundle_${session.session_id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-[#FAF8F2] border-2 border-black rounded-2xl max-w-3xl w-full p-6 md:p-8 shadow-2xl animate-fade-in font-sans flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#E2DFC9]">
          <div className="flex items-center gap-3">
            <Server size={22} className="text-[#E19B4C]" />
            <div>
              <h3 className="font-serif italic text-2xl font-bold text-black">FHIR R4 EHR Export Payload</h3>
              <p className="text-xs text-[#66655C] font-mono">HL7 FHIR R4 JSON Bundle • Session {session.session_id}</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-gray-500 hover:text-black p-1 rounded-lg transition"
          >
            <X size={20} />
          </button>
        </div>

        {/* JSON Display Screen */}
        <div className="my-4 flex-1 overflow-hidden flex flex-col space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-[#66655C]">
            <span className="flex items-center gap-1.5 font-bold text-black">
              <FileCode size={14} className="text-[#E19B4C]" />
              <span>Standard: HL7 FHIR R4 (JSON)</span>
            </span>
            <span>{jsonString.length} Bytes</span>
          </div>

          <div className="bg-[#1A1A1C] text-[#E19B4C] font-mono text-xs p-4 rounded-xl border border-black overflow-y-auto flex-1 max-h-[380px]">
            <pre className="leading-relaxed">{jsonString}</pre>
          </div>
        </div>

        {/* Action Controls */}
        <div className="pt-4 border-t border-[#E2DFC9] flex items-center justify-between gap-3">
          <span className="text-xs font-mono text-[#8C8A7B]">
            Status: {session.status === 'APPROVED' ? 'Persisted to EHR' : 'Pending Sign-Off'}
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="bg-white border-2 border-black text-black px-4 py-2 rounded-full font-mono text-xs font-bold uppercase flex items-center gap-1.5 hover:bg-[#FAF8F2]"
            >
              {copied ? <Check size={14} className="text-green-700" /> : <Copy size={14} />}
              <span>{copied ? 'Copied to Clipboard' : 'Copy JSON'}</span>
            </button>

            <button
              onClick={handleDownload}
              className="bg-[#2A2B2E] text-white px-5 py-2.5 rounded-full font-mono text-xs font-bold uppercase flex items-center gap-1.5 hover:bg-black shadow-md"
            >
              <Download size={14} className="text-[#E19B4C]" />
              <span>Download FHIR Bundle</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
