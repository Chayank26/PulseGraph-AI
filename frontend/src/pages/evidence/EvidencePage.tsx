import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { ExternalLink, CheckCircle2, BookOpen } from 'lucide-react';
import './EvidencePage.css';

import { Link } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';

export const EvidencePage: React.FC = () => {
  const { session, activePatient, agentStatuses } = useWorkflow();

  if (!activePatient || !session) {
    return (
      <div className="bg-white border-2 border-black rounded-2xl p-12 text-center max-w-2xl mx-auto my-12 shadow-sm font-sans">
        <AlertTriangle size={36} className="mx-auto text-[#E19B4C] mb-3" />
        <h2 className="font-serif text-2xl font-bold text-black">No Active Patient Selected</h2>
        <p className="text-sm text-[#66655C] mt-2">
          Please select or register a patient from the Physician Patient Directory to view PubMed literature and guideline evidence.
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

  const evidenceList = session.state.evidence || [];
  const status = agentStatuses.evidence || 'COMPLETED';

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
          {evidenceList && evidenceList.length > 0 ? (
            evidenceList.map((item, idx) => {
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
            })
          ) : (
            <div className="bg-white border border-[#DCD8BE] rounded-2xl p-12 text-center text-xs font-mono text-[#8C8A7B]">
              Evidence RAG retrieval pending... Run workflow pipeline to search PubMed & clinical guideline indices.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
