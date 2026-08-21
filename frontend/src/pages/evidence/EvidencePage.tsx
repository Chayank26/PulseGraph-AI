import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { ExternalLink, CheckCircle2 } from 'lucide-react';
import './EvidencePage.css';

export const EvidencePage: React.FC = () => {
  const { session, agentStatuses } = useWorkflow();
  const evidenceList = session.state.evidence || [];
  const status = agentStatuses.evidence || 'COMPLETED';

  return (
    <div className="evidence-shell animate-fade-in">
      {/* Header Banner */}
      <div className="evidence-banner">
        <div>
          <div className="evidence-banner-meta">
            AGENT 04 • PUBMED & CLINICAL GUIDELINE RAG
          </div>
          <h1 className="evidence-banner-title">
            EVIDENCE RAG AGENT
          </h1>
          <p className="evidence-banner-subtitle">
            Retrieves peer-reviewed literature, AHA/ACC guidelines, and UpToDate citations.
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
          <h3 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C]">
            RETRIEVED GUIDELINES & CITATIONS ({evidenceList.length})
          </h3>
          <span className="text-xs font-mono text-[#8C8A7B]">VECTOR RAG RELEVANCE SCORE THRESHOLD &gt; 0.85</span>
        </div>

        <div className="space-y-6">
          {evidenceList.map((item, idx) => (
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

                {item.relevance_score && (
                  <div className="evidence-rel-badge">
                    {(item.relevance_score * 100).toFixed(0)}% RELEVANCE
                  </div>
                )}
              </div>

              <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-2">
                <span className="text-[10px] font-mono uppercase text-[#66655C] font-bold">Key Guideline Snippet</span>
                <p className="font-serif italic text-sm text-[#1A1A1C] leading-relaxed">
                  "{item.snippet}"
                </p>
              </div>

              {item.url_or_doi && (
                <div className="pt-2 flex items-center justify-between text-xs font-mono text-[#66655C]">
                  <span>DOI / Identifier: {item.url_or_doi}</span>
                  <a
                    href={`https://doi.org/${item.url_or_doi}`}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 font-bold text-black hover:underline uppercase text-[11px]"
                  >
                    <span>View Reference</span>
                    <ExternalLink size={12} />
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
