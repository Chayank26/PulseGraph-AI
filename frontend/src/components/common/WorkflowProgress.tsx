import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { CheckCircle2, Clock, PlayCircle, UserCheck } from 'lucide-react';

interface WorkflowProgressProps {
  compact?: boolean;
}

export const WorkflowProgress: React.FC<WorkflowProgressProps> = ({ compact = false }) => {
  const { agentStatuses, runningAgentId, session } = useWorkflow();

  const steps = [
    { id: 'triage', label: 'TRIAGE', short: 'Triage' },
    { id: 'imaging', label: 'IMAGING', short: 'Imaging' },
    { id: 'diagnostic', label: 'DIFF. DX', short: 'Differential' },
    { id: 'evidence', label: 'EVIDENCE', short: 'Evidence' },
    { id: 'safety', label: 'SAFETY', short: 'Safety' },
    { id: 'symbolic-guard', label: 'SYMBOLIC GUARD', short: 'Symbolic' },
    { id: 'human-review', label: 'CLINICIAN REVIEW', short: 'Review' }
  ];

  return (
    <div className={`w-full ${compact ? 'py-2' : 'py-4 px-6 bg-[#FAF8F2] border-b border-[#E2DFC9]'}`}>
      <div className="flex items-center justify-between overflow-x-auto no-scrollbar gap-2 min-w-[650px]">
        {steps.map((step, idx) => {
          const isRunning = runningAgentId === step.id;
          const status = agentStatuses[step.id] || 'IDLE';
          const isReview = step.id === 'human-review';
          const isApproved = session.status === 'APPROVED';

          let stateColor = 'bg-[#EAE7DA] text-[#66655C] border-[#DCD8BE]';
          if (isRunning) {
            stateColor = 'bg-[#D6E3F5] text-[#1E3A8A] border-[#93C5FD] ring-2 ring-[#2563EB] animate-pulse';
          } else if (status === 'COMPLETED' || (isReview && isApproved)) {
            stateColor = 'bg-[#CBD7C0] text-[#1C3829] border-[#9DB08F]';
          } else if (isReview && session.status === 'WAITING_FOR_CLINICIAN_REVIEW') {
            stateColor = 'bg-[#E19B4C] text-black border-black ring-2 ring-black';
          }

          return (
            <React.Fragment key={step.id}>
              <div className="flex items-center gap-2 flex-shrink-0">
                <div
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold uppercase tracking-wider font-sans shadow-2xs transition-all ${stateColor}`}
                >
                  {isRunning ? (
                    <PlayCircle size={14} className="animate-spin text-[#2563EB]" />
                  ) : status === 'COMPLETED' || isApproved ? (
                    <CheckCircle2 size={14} className="text-[#1C3829]" />
                  ) : isReview ? (
                    <UserCheck size={14} />
                  ) : (
                    <Clock size={14} />
                  )}
                  <span>{compact ? step.short : step.label}</span>
                </div>
              </div>

              {idx < steps.length - 1 && (
                <div className="flex-1 h-[2px] min-w-[20px] bg-[#DCD8BE] relative">
                  {(status === 'COMPLETED' || isRunning) && (
                    <div className="h-full bg-black transition-all duration-500" style={{ width: status === 'COMPLETED' ? '100%' : '50%' }} />
                  )}
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
