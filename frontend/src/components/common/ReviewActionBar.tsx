import React, { useState } from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { ShieldAlert, CheckCircle, XCircle, RotateCcw } from 'lucide-react';

export const ReviewActionBar: React.FC = () => {
  const { session, approveSession, rejectSession, reevaluateSession } = useWorkflow();
  const [showNotesModal, setShowNotesModal] = useState<'APPROVE' | 'REJECT' | 'REEVAL' | null>(null);
  const [clinicianNotes, setClinicianNotes] = useState('');

  const activeOverride = session.state.symbolic_overrides?.[0];
  const isApproved = session.status === 'APPROVED';
  const isRejected = session.status === 'REJECTED_MANUAL_TAKEOVER';

  const handleConfirmAction = async () => {
    if (showNotesModal === 'APPROVE') {
      await approveSession(clinicianNotes);
    } else if (showNotesModal === 'REJECT') {
      await rejectSession(clinicianNotes);
    } else if (showNotesModal === 'REEVAL') {
      await reevaluateSession(clinicianNotes);
    }
    setShowNotesModal(null);
    setClinicianNotes('');
  };

  return (
    <div className="sticky bottom-0 z-40 w-full px-4 md:px-8 pb-6 pt-3 pointer-events-none">
      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4 pointer-events-auto">
        {/* Left: Symbolic Override Callout Box */}
        {activeOverride ? (
          <div className="flex-1 bg-white/95 backdrop-blur border-2 border-black rounded-xl p-3 md:p-4 shadow-xl flex flex-col md:flex-row items-start md:items-center gap-3">
            <div className="bg-[#2A2B2E] text-white text-[10px] font-mono tracking-wider font-bold px-3 py-1 rounded uppercase flex-shrink-0 flex items-center gap-1.5">
              <ShieldAlert size={12} className="text-[#E19B4C]" />
              <span>SYMBOLIC OVERRIDE</span>
            </div>
            <p className="text-xs font-sans text-[#1A1A1C] font-medium leading-tight">
              <strong className="font-bold">{activeOverride.rule_id}:</strong> {activeOverride.message}
            </p>
          </div>
        ) : (
          <div className="flex-1 bg-[#FAF8F2]/90 backdrop-blur border border-[#E2DFC9] rounded-xl p-3 text-xs text-[#66655C] italic">
            Deterministic safety guardrails passed clean. No critical symbolic overrides triggered.
          </div>
        )}

        {/* Right: Floating Review Action Buttons */}
        <div className="bg-[#FAF8F2]/95 backdrop-blur border-2 border-black rounded-full p-2 shadow-2xl flex items-center gap-2 justify-center flex-wrap">
          {isApproved ? (
            <div className="bg-[#B8C8A5] text-[#2C421C] font-bold text-xs px-6 py-2.5 rounded-full flex items-center gap-2 border border-[#98A885]">
              <CheckCircle size={16} />
              <span>CLINICIAN APPROVED & PERSISTED (EHR EXPORTED)</span>
            </div>
          ) : isRejected ? (
            <div className="bg-[#F7D8D8] text-[#8C2A2A] font-bold text-xs px-6 py-2.5 rounded-full flex items-center gap-2 border border-[#EAAFA0]">
              <XCircle size={16} />
              <span>REJECTED — MANUAL TAKEOVER ACTIVE</span>
            </div>
          ) : (
            <>
              {/* Request Re-Eval Button */}
              <button
                onClick={() => setShowNotesModal('REEVAL')}
                className="bg-[#2A2B2E] hover:bg-black text-white text-xs font-semibold uppercase tracking-wider px-5 py-2.5 rounded-full transition-all duration-150 flex items-center gap-1.5 shadow-md"
              >
                <RotateCcw size={14} />
                <span>REQUEST RE-EVAL</span>
              </button>

              {/* Reject / Manual Takeover Button */}
              <button
                onClick={() => setShowNotesModal('REJECT')}
                className="bg-[#F7D8D8] hover:bg-[#F2C6C6] text-[#8C2A2A] border border-[#EAAFA0] text-xs font-semibold uppercase tracking-wider px-5 py-2.5 rounded-full transition-all duration-150 flex items-center gap-1.5 shadow-sm"
              >
                <XCircle size={14} />
                <span>REJECT SUPPORT</span>
              </button>

              {/* Approve & Persist Button */}
              <button
                onClick={() => setShowNotesModal('APPROVE')}
                className="bg-[#B8C8A5] hover:bg-[#A6B892] text-[#2C421C] border border-[#98A885] text-xs font-bold uppercase tracking-wider px-6 py-2.5 rounded-full transition-all duration-150 flex items-center gap-1.5 shadow-md"
              >
                <CheckCircle size={15} />
                <span>APPROVE & PERSIST</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Confirmation & Feedback Notes Modal */}
      {showNotesModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 pointer-events-auto">
          <div className="bg-[#FAF8F2] border-2 border-black rounded-2xl p-6 max-w-lg w-full shadow-2xl">
            <h3 className="font-serif italic text-2xl font-bold text-[#1A1A1C] mb-2">
              {showNotesModal === 'APPROVE' && 'Approve & Persist Clinical CDS Payload'}
              {showNotesModal === 'REJECT' && 'Initiate Manual Physician Takeover'}
              {showNotesModal === 'REEVAL' && 'Request Pipeline Re-Evaluation Loop'}
            </h3>
            <p className="text-xs text-[#66655C] mb-4">
              Enter any clinical justification notes or guidance for audit record keeping.
            </p>

            <textarea
              value={clinicianNotes}
              onChange={(e) => setClinicianNotes(e.target.value)}
              placeholder="Add physician review rationale, feedback notes, or specific differential requests..."
              rows={4}
              className="w-full bg-white border border-[#DCD8BE] rounded-xl p-3 text-xs font-sans text-black focus:outline-none focus:ring-2 focus:ring-black mb-5"
            />

            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setShowNotesModal(null)}
                className="px-4 py-2 rounded-full text-xs font-semibold text-[#66655C] hover:text-black hover:bg-[#EAE7DA]"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAction}
                className={`px-6 py-2 rounded-full text-xs font-bold text-white shadow-md uppercase tracking-wider ${
                  showNotesModal === 'APPROVE' ? 'bg-[#2C421C] hover:bg-[#1E3012]' :
                  showNotesModal === 'REJECT' ? 'bg-[#8C2A2A] hover:bg-[#6D1F1F]' :
                  'bg-[#2A2B2E] hover:bg-black'
                }`}
              >
                Confirm {showNotesModal}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
