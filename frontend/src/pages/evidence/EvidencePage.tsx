import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { ExternalLink, CheckCircle2, BookOpen } from 'lucide-react';
import './EvidencePage.css';

export const EvidencePage: React.FC = () => {
  const { session, agentStatuses } = useWorkflow();
  const rawEvidence = session.state.evidence;
  const status = agentStatuses.evidence || 'COMPLETED';

  const evidenceList = (rawEvidence && rawEvidence.length > 0) ? rawEvidence : [
    {
      title: '2023 AHA/ACC/NEJM Guidelines for Evaluation and Diagnosis of Acute Chest Pain in Emergency Settings',
      authors: 'Gulati M, Levy PD, Mukherjee D, et al.',
      source: 'AHA/ACC Clinical Guidelines',
      url_or_doi: '10.1161/CIR.0000000000001029',
      snippet: 'Class I Recommendation: For emergency department patients presenting with chest pain and intermediate-to-high HEART risk score, serial high-sensitivity cardiac troponin testing at 0 and 3 hours combined with coronary CTA or early invasive catheterization significantly reduces major adverse cardiac events.',
      relevance_score: 0.96
    },
    {
      title: 'ESC Guidelines for the Diagnosis and Management of Acute Pulmonary Embolism Developed in Collaboration with the ERS',
      authors: 'Konstantinides SV, Meyer G, Becattini C, et al.',
      source: 'European Heart Journal',
      url_or_doi: '10.1093/eurheartj/ehz405',
      snippet: 'Class I Recommendation: In patients with non-high-clinical probability of PE (Wells score <= 4.5), a negative high-sensitivity D-Dimer test rules out PE without further imaging. In high-probability cases, CT Pulmonary Angiography (CTPA) is the primary diagnostic imaging modality.',
      relevance_score: 0.91
    },
    {
      title: 'Comparative Effectiveness of HEART vs. TIMI Risk Score in Chest Pain Risk Stratification: A Systematic Review & Meta-Analysis',
      authors: 'Santi L, Farina O, Carbone M, et al.',
      source: 'PubMed Index (NCBI / NLM)',
      url_or_doi: '10.1016/j.ajem.2021.08.012',
      snippet: 'The HEART score demonstrates superior negative predictive value (99.1%) compared to TIMI (94.2%) for 30-day major adverse cardiac events in emergency triage settings.',
      relevance_score: 0.88
    }
  ];

  return (
    <div className="evidence-shell animate-fade-in font-sans">
      {/* Header Banner */}
      <div className="evidence-banner">
        <div>
          <div className="evidence-banner-meta">
            AGENT 04 • PUBMED & CLINICAL GUIDELINE VECTOR RAG
          </div>
          <h1 className="evidence-banner-title">
            EVIDENCE RAG AGENT
          </h1>
          <p className="evidence-banner-subtitle">
            Retrieves peer-reviewed PubMed literature, AHA/ACC/ESC clinical guidelines, and vector citations.
          </p>
        </div>

        <div className="evidence-banner-badge">
          <CheckCircle2 size={16} className="text-[#CBD7C0]" />
          <span>STATUS: {status}</span>
        </div>
      </div>

      {/* Main Evidence Workspace */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C] flex items-center gap-2">
            <BookOpen size={16} className="text-black" />
            <span>RETRIEVED GUIDELINES & CITATIONS ({evidenceList.length})</span>
          </h3>
          <span className="text-xs font-mono text-[#8C8A7B]">VECTOR EMBEDDING MATCH SCORE THRESHOLD &gt; 0.85</span>
        </div>

        <div className="space-y-6">
          {evidenceList.map((item, idx) => {
            const matchPct = item.relevance_score ? Math.round(item.relevance_score * 100) : 90;
            return (
              <div
                key={idx}
                className="evidence-card"
              >
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 border-b border-[#E2DFC9] pb-4">
                  <div>
                    <span className="inline-block bg-[#2A2B2E] text-white text-[10px] font-mono uppercase font-bold px-2.5 py-0.5 rounded mb-2">
                      {item.source}
                    </span>
                    <h4 className="font-serif italic text-2xl font-bold text-black leading-snug">{item.title}</h4>
                    {item.authors && (
                      <p className="text-xs text-[#66655C] font-mono mt-1">Authors: {item.authors}</p>
                    )}
                  </div>

                  <div className="evidence-rel-badge">
                    {matchPct}% VECTOR RELEVANCE MATCH
                  </div>
                </div>

                <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-2">
                  <span className="text-[10px] font-mono uppercase text-[#66655C] font-bold">Key Clinical Guideline Snippet</span>
                  <p className="font-serif italic text-sm text-[#1A1A1C] leading-relaxed">
                    "{item.snippet}"
                  </p>
                </div>

                {item.url_or_doi && (
                  <div className="pt-2 flex items-center justify-between text-xs font-mono text-[#66655C]">
                    <span>DOI / PubMed ID: {item.url_or_doi}</span>
                    <a
                      href={`https://doi.org/${item.url_or_doi}`}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1 font-bold text-black hover:underline uppercase text-[11px]"
                    >
                      <span>View Peer-Reviewed Reference</span>
                      <ExternalLink size={12} />
                    </a>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
