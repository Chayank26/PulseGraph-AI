import React, { createContext, useContext, useState } from 'react';
import type { ClinicalSession, AgentStatusType } from '../types/clinical';
import { mockClinicalSession } from '../data/mockClinicalSession';

interface WorkflowContextType {
  session: ClinicalSession;
  agentStatuses: Record<string, AgentStatusType>;
  runningAgentId: string | null;
  currentAgentProgressMessage: string;
  runWorkflow: () => Promise<void>;
  resolveDataRequest: (requestId: string, responseData: Record<string, any>) => Promise<void>;
  approveSession: (notes?: string) => Promise<void>;
  rejectSession: (notes?: string) => Promise<void>;
  reevaluateSession: (notes?: string) => Promise<void>;
  resetDemoSession: () => void;
}

const WorkflowContext = createContext<WorkflowContextType | undefined>(undefined);

export const WorkflowProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<ClinicalSession>(mockClinicalSession);
  const [agentStatuses, setAgentStatuses] = useState<Record<string, AgentStatusType>>({
    triage: 'COMPLETED',
    imaging: 'COMPLETED',
    diagnostic: 'COMPLETED',
    evidence: 'COMPLETED',
    safety: 'COMPLETED'
  });
  const [runningAgentId, setRunningAgentId] = useState<string | null>(null);
  const [currentAgentProgressMessage, setCurrentAgentProgressMessage] = useState<string>('');

  // Simulates step-by-step workflow execution
  const runWorkflow = async () => {
    setSession(prev => ({
      ...prev,
      status: 'RUNNING',
      current_step: 'running'
    }));

    const stages = [
      { id: 'triage', msg: 'Ingesting presenting symptoms & calculating clinical risk scores (HEART, Wells PE)...' },
      { id: 'imaging', msg: 'CheXNet Multimodal Vision model analyzing Chest X-Ray DICOM scans...' },
      { id: 'diagnostic', msg: 'Formulating differential diagnosis candidates & ICD-10 likelihood percentages...' },
      { id: 'evidence', msg: 'Retrieving medical guidelines & PubMed research citations via RAG pipeline...' },
      { id: 'safety', msg: 'Auditing drug-drug interactions & evaluating deterministic symbolic safety rules...' }
    ];

    // Reset statuses to IDLE
    setAgentStatuses({
      triage: 'IDLE',
      imaging: 'IDLE',
      diagnostic: 'IDLE',
      evidence: 'IDLE',
      safety: 'IDLE'
    });

    for (const stage of stages) {
      setRunningAgentId(stage.id);
      setCurrentAgentProgressMessage(stage.msg);
      setAgentStatuses(prev => ({ ...prev, [stage.id]: 'RUNNING' }));

      // Pause for visual workflow progress demonstration
      await new Promise(resolve => setTimeout(resolve, 900));

      setAgentStatuses(prev => ({ ...prev, [stage.id]: 'COMPLETED' }));
    }

    setRunningAgentId(null);
    setCurrentAgentProgressMessage('');
    setSession(prev => ({
      ...prev,
      status: 'WAITING_FOR_CLINICIAN_REVIEW',
      current_step: 'human_review'
    }));
  };

  const resolveDataRequest = async (requestId: string, responseData: Record<string, any>) => {
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const formattedNote = `[ACQUIRED CLINICAL DATA]: ${Object.entries(responseData).map(([k, v]) => `${k} = ${v}`).join(', ')}`;
    
    setSession(prev => {
      const updatedPending = prev.state.pending_data_requests.filter(r => r.request_id !== requestId);
      return {
        ...prev,
        status: updatedPending.length > 0 ? 'WAITING_FOR_CLINICAL_DATA' : 'WAITING_FOR_CLINICIAN_REVIEW',
        state: {
          ...prev.state,
          raw_notes: [...prev.state.raw_notes, formattedNote],
          pending_data_requests: updatedPending,
          audit_trail: [
            ...prev.state.audit_trail,
            {
              timestamp,
              agent_name: 'Clinician_Input',
              action: `Resolved ClinicalDataRequest [${requestId}]`,
              details: `Acquired fields: ${JSON.stringify(responseData)}`
            }
          ]
        }
      };
    });
  };

  const approveSession = async (notes?: string) => {
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setSession(prev => ({
      ...prev,
      status: 'APPROVED',
      current_step: 'ehr_exported',
      state: {
        ...prev.state,
        approved_by_clinician: true,
        audit_trail: [
          ...prev.state.audit_trail,
          {
            timestamp,
            agent_name: 'Clinician_Review',
            action: 'APPROVED & PERSISTED CDS RESULT',
            details: notes || 'Clinician verified and approved PulseGraph recommendation payload for EHR Export.'
          }
        ]
      }
    }));
  };

  const rejectSession = async (notes?: string) => {
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setSession(prev => ({
      ...prev,
      status: 'REJECTED_MANUAL_TAKEOVER',
      current_step: 'rejected_manual_takeover',
      state: {
        ...prev.state,
        approved_by_clinician: false,
        audit_trail: [
          ...prev.state.audit_trail,
          {
            timestamp,
            agent_name: 'Clinician_Review',
            action: 'REJECTED — MANUAL PHYSICIAN TAKEOVER',
            details: notes || 'Clinician rejected automated recommendations and initiated manual patient management.'
          }
        ]
      }
    }));
  };

  const reevaluateSession = async (notes?: string) => {
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setSession(prev => ({
      ...prev,
      status: 'RUNNING',
      current_step: 'reevaluating',
      state: {
        ...prev.state,
        iteration_count: prev.state.iteration_count + 1,
        re_evaluation_requested: true,
        audit_trail: [
          ...prev.state.audit_trail,
          {
            timestamp,
            agent_name: 'Clinician_Review',
            action: 'REQUESTED RE-EVALUATION LOOP',
            details: `Clinician Feedback: ${notes || 'Re-evaluate differential diagnosis with updated imaging parameters.'}`
          }
        ]
      }
    }));

    // Trigger workflow re-run
    await runWorkflow();
  };

  const resetDemoSession = () => {
    setSession(mockClinicalSession);
    setAgentStatuses({
      triage: 'COMPLETED',
      imaging: 'COMPLETED',
      diagnostic: 'COMPLETED',
      evidence: 'COMPLETED',
      safety: 'COMPLETED'
    });
    setRunningAgentId(null);
    setCurrentAgentProgressMessage('');
  };

  return (
    <WorkflowContext.Provider
      value={{
        session,
        agentStatuses,
        runningAgentId,
        currentAgentProgressMessage,
        runWorkflow,
        resolveDataRequest,
        approveSession,
        rejectSession,
        reevaluateSession,
        resetDemoSession
      }}
    >
      {children}
    </WorkflowContext.Provider>
  );
};

export const useWorkflow = (): WorkflowContextType => {
  const context = useContext(WorkflowContext);
  if (!context) {
    throw new Error('useWorkflow must be used within a WorkflowProvider');
  }
  return context;
};
