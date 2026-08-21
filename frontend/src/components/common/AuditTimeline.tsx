import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';

export const AuditTimeline: React.FC = () => {
  const { session } = useWorkflow();
  const auditTrail = session.state.audit_trail || [];

  return (
    <div className="w-full h-full bg-[#FAF8F2] border-l-0 lg:border-l border-[#E2DFC9] p-6 font-sans">
      {/* Editorial Header */}
      <h2 className="font-serif uppercase tracking-[0.2em] text-xs text-[#66655C] font-semibold mb-6">
        AUDIT TRAIL
      </h2>

      {auditTrail.length === 0 ? (
        <p className="text-xs text-[#8C8A7B] italic">No audit trail entries recorded yet.</p>
      ) : (
        <div className="space-y-6">
          {auditTrail.map((entry, idx) => (
            <div key={idx} className="pt-4 first:pt-0 border-t first:border-t-0 border-[#E2DFC9]">
              <div className="text-[11px] font-mono text-[#8C8A7B] font-medium mb-1">
                {entry.timestamp}
              </div>
              <div className="font-sans font-bold text-sm text-[#1A1A1C] mb-1">
                {entry.agent_name}
              </div>
              <p className="text-xs text-[#4A4943] leading-relaxed font-sans font-normal">
                {entry.details}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
