import React from 'react';
import { AuditTimeline } from '../../components/common/AuditTimeline';
import { ShieldCheck, History } from 'lucide-react';
import './AuditPage.css';

export const AuditPage: React.FC = () => {
  return (
    <div className="audit-shell animate-fade-in font-sans">
      <div className="audit-banner">
        <div>
          <div className="audit-banner-meta">
            <History size={14} />
            <span>EXPLAINABILITY & COMPLIANCE LOG</span>
          </div>
          <h1 className="audit-banner-title">
            AUDIT TRAIL & TRACEABILITY
          </h1>
          <p className="audit-banner-subtitle">
            Append-only, immutable event log documenting every agent invocation, tool execution, and clinician decision.
          </p>
        </div>

        <div className="audit-banner-badge">
          <ShieldCheck size={16} className="text-[#E19B4C]" />
          <span>POSTGRES PERSISTED</span>
        </div>
      </div>

      <div className="audit-content-card">
        <AuditTimeline />
      </div>
    </div>
  );
};
