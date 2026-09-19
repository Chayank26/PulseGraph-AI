import React, { useState } from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { ShieldCheck, Terminal, UserCheck, Activity, Eye, X } from 'lucide-react';

export const AuditTimeline: React.FC = () => {
  const { session } = useWorkflow();
  const auditTrail = session?.state?.audit_trail || [];
  const [filterCategory, setFilterCategory] = useState<'ALL' | 'AGENTS' | 'CLINICIAN' | 'SAFETY'>('ALL');
  const [selectedEntry, setSelectedEntry] = useState<any | null>(null);

  const filteredEntries = auditTrail.filter((entry) => {
    if (filterCategory === 'AGENTS') return entry.agent_name.includes('Agent');
    if (filterCategory === 'CLINICIAN') return entry.agent_name.includes('Clinician') || entry.agent_name.includes('Doctor') || entry.action.includes('CLINICIAN');
    if (filterCategory === 'SAFETY') return entry.agent_name.includes('Safety') || entry.agent_name.includes('Symbolic') || entry.action.includes('SAFETY');
    return true;
  });

  return (
    <div className="w-full bg-[#FAF8F2] font-sans">
      {/* Header & Filter Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-[#E2DFC9]">
        <div>
          <h2 className="font-serif uppercase tracking-[0.2em] text-xs text-[#66655C] font-semibold flex items-center gap-2">
            <ShieldCheck size={16} className="text-black" />
            <span>IMMUTABLE SYSTEM TRAIL ({auditTrail.length} ENTRIES)</span>
          </h2>
          <p className="text-xs text-[#8C8A7B] font-mono mt-0.5">PostgreSQL Append-Only Audit Log Engine</p>
        </div>

        {/* Filter Category Chips */}
        <div className="flex items-center gap-1 bg-[#EAE7DA] p-1 rounded-xl text-xs font-mono font-bold">
          {(['ALL', 'AGENTS', 'CLINICIAN', 'SAFETY'] as const).map((cat) => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              className={`px-3 py-1.5 rounded-lg transition ${
                filterCategory === cat ? 'bg-[#2A2B2E] text-white shadow-sm' : 'text-[#66655C] hover:text-black'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Audit Event Timeline List */}
      {filteredEntries.length === 0 ? (
        <p className="text-xs text-[#8C8A7B] italic py-12 text-center">No matching audit log entries recorded in state timeline.</p>
      ) : (
        <div className="relative py-6 space-y-6">
          {/* Vertical Timeline Line */}
          <div className="absolute top-8 bottom-8 left-4 w-0.5 bg-[#DCD8BE]"></div>

          {filteredEntries.map((entry, idx) => {
            const isClinician = entry.agent_name.includes('Clinician') || entry.action?.includes('CLINICIAN');
            const isSafety = entry.agent_name.includes('Safety') || entry.agent_name.includes('Symbolic');

            let icon = <Activity size={14} className="text-black" />;
            let badgeBg = 'bg-[#2A2B2E] text-white';

            if (isClinician) {
              icon = <UserCheck size={14} className="text-green-800" />;
              badgeBg = 'bg-[#E8EFE2] text-[#1C3829] border-[#BDCCA6]';
            } else if (isSafety) {
              icon = <Terminal size={14} className="text-amber-800" />;
              badgeBg = 'bg-[#FFF3C4] text-[#8C6D00] border-[#E6C200]';
            }

            return (
              <div key={idx} className="relative pl-10 group">
                {/* Timeline Dot */}
                <div className="absolute left-2.5 top-1.5 -translate-x-1/2 w-4 h-4 rounded-full bg-[#FAF8F2] border-2 border-black flex items-center justify-center group-hover:scale-125 transition-transform">
                  <div className="w-1.5 h-1.5 rounded-full bg-[#E19B4C]"></div>
                </div>

                <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 shadow-sm hover:border-black transition">
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-[#E2DFC9] pb-2">
                    <div className="flex items-center gap-2">
                      {icon}
                      <span className="font-bold text-sm text-black">{entry.agent_name}</span>
                      <span className={`text-[10px] font-mono font-bold uppercase px-2.5 py-0.5 rounded border ${badgeBg}`}>
                        {entry.action || 'INVOCATION'}
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-[11px] font-mono text-[#8C8A7B]">
                        {entry.timestamp}
                      </span>
                      <button
                        onClick={() => setSelectedEntry(entry)}
                        className="text-[10px] font-mono font-bold uppercase text-[#66655C] hover:text-black flex items-center gap-1 bg-[#FAF8F2] border border-[#DCD8BE] px-2 py-0.5 rounded"
                      >
                        <Eye size={10} />
                        <span>Inspect Payload</span>
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-[#1A1A1C] leading-relaxed font-sans pt-2">
                    {entry.details}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* JSON Metadata Inspector Modal */}
      {selectedEntry && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[#FAF8F2] border-2 border-black rounded-2xl max-w-xl w-full p-6 shadow-2xl animate-fade-in font-sans">
            <div className="flex items-center justify-between pb-3 border-b border-[#E2DFC9]">
              <div>
                <h3 className="font-serif italic text-xl font-bold text-black">{selectedEntry.agent_name} Payload</h3>
                <p className="text-xs text-[#66655C] font-mono">{selectedEntry.action} • {selectedEntry.timestamp}</p>
              </div>
              <button
                onClick={() => setSelectedEntry(null)}
                className="text-gray-500 hover:text-black"
              >
                <X size={18} />
              </button>
            </div>

            <div className="my-4 bg-[#1A1A1C] text-[#E19B4C] font-mono text-xs p-4 rounded-xl border border-black max-h-72 overflow-y-auto">
              <pre>{JSON.stringify(selectedEntry, null, 2)}</pre>
            </div>

            <div className="text-right">
              <button
                onClick={() => setSelectedEntry(null)}
                className="bg-[#2A2B2E] text-white px-5 py-2 rounded-full font-mono text-xs font-bold uppercase hover:bg-black"
              >
                Close Payload Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
