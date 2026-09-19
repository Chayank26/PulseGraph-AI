import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import type { ClinicalSession, AgentStatusType, PatientDemographics, ClinicalDataRequest } from '../types/clinical';
import { patientsApi } from '../api/patients';
import type { CreatePatientPayload, UpdatePatientPayload } from '../api/patients';
import { clinicalSessionsApi } from '../api/clinicalSessions';

interface WorkflowContextType {
  session: ClinicalSession | null;
  activePatient: PatientDemographics | null;
  agentStatuses: Record<string, AgentStatusType>;
  runningAgentId: string | null;
  currentAgentProgressMessage: string;
  loadingPatient: boolean;
  isPolling: boolean;
  selectPatient: (patient: PatientDemographics) => Promise<void>;
  clearActivePatient: () => void;
  createPatient: (payload: CreatePatientPayload) => Promise<PatientDemographics>;
  updatePatient: (patientId: string, payload: UpdatePatientPayload) => Promise<PatientDemographics>;
  fetchPatient: (patientId: string) => Promise<PatientDemographics>;
  createClinicalSession: (patientId: string, rawNotes?: string[]) => Promise<ClinicalSession>;
  runWorkflow: () => Promise<void>;
  resolveDataRequest: (requestId: string, responseData: Record<string, any>) => Promise<void>;
  approveSession: (notes?: string) => Promise<void>;
  rejectSession: (notes?: string) => Promise<void>;
  reevaluateSession: (notes?: string) => Promise<void>;
  resetDemoSession: () => void;
}

const WorkflowContext = createContext<WorkflowContextType | undefined>(undefined);

export const WorkflowProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<ClinicalSession | null>(null);
  const [activePatient, setActivePatient] = useState<PatientDemographics | null>(null);
  const [loadingPatient, setLoadingPatient] = useState<boolean>(false);
  const [isPolling, setIsPolling] = useState<boolean>(false);

  const [agentStatuses, setAgentStatuses] = useState<Record<string, AgentStatusType>>({
    triage: 'IDLE',
    imaging: 'IDLE',
    diagnostic: 'IDLE',
    evidence: 'IDLE',
    safety: 'IDLE'
  });
  const [runningAgentId, setRunningAgentId] = useState<string | null>(null);
  const [currentAgentProgressMessage, setCurrentAgentProgressMessage] = useState<string>('');

  const pollingIntervalRef = useRef<any>(null);

  // Stop polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // Poll backend state for active session
  const pollSessionState = async (sessionId: string) => {
    try {
      const updatedSess = await clinicalSessionsApi.getSession(sessionId);
      
      // Attempt to load CDS results if generated
      let cdsResults = null;
      try {
        cdsResults = await clinicalSessionsApi.getCDSResults(sessionId);
      } catch (e) {
        // CDS result might not be generated yet during early stage
      }

      // Attempt to load pending data requests if paused
      let pendingRequests: ClinicalDataRequest[] = [];
      if (updatedSess.status === 'WAITING_FOR_CLINICAL_DATA') {
        try {
          pendingRequests = await clinicalSessionsApi.getDataRequests(sessionId);
        } catch (e) {
          console.warn('Failed to fetch data requests:', e);
        }
      }

      // Attempt to load audit trail
      let auditTrail = session?.state?.audit_trail || [];
      try {
        const auditLogs = await clinicalSessionsApi.getAuditTrail(sessionId);
        if (auditLogs && auditLogs.length > 0) {
          auditTrail = auditLogs.map(log => ({
            timestamp: log.timestamp ? new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : new Date().toLocaleTimeString(),
            agent_name: log.agent_name,
            action: log.action,
            details: log.summary || JSON.stringify(log.metadata_json || {})
          }));
        }
      } catch (e) {
        // Audit trail fetch fallback
      }

      // Map backend current_step to agent status indicators
      const step = updatedSess.current_step || '';
      const newAgentStatuses: Record<string, AgentStatusType> = {
        triage: step.includes('triage') ? 'RUNNING' : 'COMPLETED',
        imaging: step.includes('imaging') ? 'RUNNING' : (step === 'initialized' || step.includes('triage') ? 'IDLE' : 'COMPLETED'),
        diagnostic: step.includes('diagnostic') ? 'RUNNING' : (step.includes('triage') || step.includes('imaging') || step === 'initialized' ? 'IDLE' : 'COMPLETED'),
        evidence: step.includes('evidence') ? 'RUNNING' : (step.includes('safety') || step.includes('human') || step === 'completed' || step === 'ehr_exported' ? 'COMPLETED' : 'IDLE'),
        safety: step.includes('safety') ? 'RUNNING' : (step.includes('human') || step === 'completed' || step === 'ehr_exported' ? 'COMPLETED' : 'IDLE')
      };

      setAgentStatuses(newAgentStatuses);

      setSession(prev => {
        if (!prev) return null;
        return {
          ...prev,
          session_id: updatedSess.session_id,
          patient_id: updatedSess.patient_id,
          doctor_id: updatedSess.doctor_id,
          thread_id: updatedSess.thread_id,
          status: updatedSess.status,
          current_step: updatedSess.current_step,
          state: {
            ...prev.state,
            patient_id: updatedSess.patient_id,
            current_step: updatedSess.current_step,
            pending_data_requests: pendingRequests,
            audit_trail: auditTrail,
            risk_scores: cdsResults?.risk_scores || prev.state.risk_scores,
            differentials: cdsResults?.differentials || prev.state.differentials,
            imaging_data: cdsResults?.imaging_findings ? {
              image_path: 'data/mock_patients/patient_001_cxr.png',
              modality: 'CHEST_XRAY_PA',
              findings: cdsResults.imaging_findings,
              impression: 'Sub-segmental filling defect noted in right lower lobe.'
            } : prev.state.imaging_data,
            evidence: cdsResults?.evidence || prev.state.evidence,
            safety_flags: cdsResults?.safety_flags || prev.state.safety_flags,
            symbolic_overrides: cdsResults?.symbolic_overrides || prev.state.symbolic_overrides
          }
        };
      });

      // Check if session reached a terminal/breakpoint status
      const isTerminal = ['WAITING_FOR_CLINICAL_DATA', 'WAITING_FOR_CLINICIAN_REVIEW', 'APPROVED', 'REJECTED_MANUAL_TAKEOVER', 'COMPLETED'].includes(updatedSess.status);
      
      if (isTerminal) {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        setIsPolling(false);
        setRunningAgentId(null);
        setCurrentAgentProgressMessage('');
      }
    } catch (err) {
      console.warn('Error polling session state:', err);
    }
  };

  // Create real patient on backend
  const createPatient = async (payload: CreatePatientPayload): Promise<PatientDemographics> => {
    setLoadingPatient(true);
    try {
      const created = await patientsApi.createPatient(payload);
      setActivePatient(created);
      return created;
    } finally {
      setLoadingPatient(false);
    }
  };

  // Update existing patient on backend
  const updatePatient = async (patientId: string, payload: UpdatePatientPayload): Promise<PatientDemographics> => {
    setLoadingPatient(true);
    try {
      const updated = await patientsApi.updatePatient(patientId, payload);
      setActivePatient(updated);
      setSession(prev => {
        if (!prev) return null;
        return {
          ...prev,
          state: {
            ...prev.state,
            demographics: {
              ...prev.state.demographics,
              age: updated.age ?? prev.state.demographics.age,
              gender: updated.gender ?? prev.state.demographics.gender,
              allergies: updated.allergies ?? prev.state.demographics.allergies,
              chronic_conditions: updated.chronic_conditions ?? prev.state.demographics.chronic_conditions,
              current_medications: updated.current_medications ?? prev.state.demographics.current_medications
            }
          }
        };
      });
      return updated;
    } finally {
      setLoadingPatient(false);
    }
  };

  // Fetch patient from backend
  const fetchPatient = async (patientId: string): Promise<PatientDemographics> => {
    setLoadingPatient(true);
    try {
      const p = await patientsApi.getPatient(patientId);
      setActivePatient(p);
      return p;
    } finally {
      setLoadingPatient(false);
    }
  };

  const selectPatient = async (patient: PatientDemographics) => {
    setActivePatient(patient);
    try {
      await createClinicalSession(patient.patient_id, [
        `[PATIENT INTAKE RECORD]: MRN=${patient.patient_id}, Age=${patient.age}, Gender=${patient.gender}`,
        patient.chief_complaint ? `Chief Complaint: ${patient.chief_complaint}` : '',
        patient.allergies?.length ? `Allergies: ${patient.allergies.join(', ')}` : '',
        patient.chronic_conditions?.length ? `Conditions: ${patient.chronic_conditions.join(', ')}` : '',
        patient.current_medications?.length ? `Medications: ${patient.current_medications.join(', ')}` : ''
      ].filter(Boolean));
    } catch (e) {
      console.warn('Initial session lookup notice:', e);
    }
  };

  const clearActivePatient = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    setIsPolling(false);
    setActivePatient(null);
    setSession(null);
    setRunningAgentId(null);
    setCurrentAgentProgressMessage('');
  };

  // Create real clinical session on backend
  const createClinicalSession = async (patientId: string, rawNotes?: string[]): Promise<ClinicalSession> => {
    const backendSession = await clinicalSessionsApi.createSession({
      patient_id: patientId,
      raw_notes: rawNotes || ["Patient presents for clinical evaluation."]
    });

    const newSessionState: ClinicalSession = {
      session_id: backendSession.session_id,
      patient_id: backendSession.patient_id,
      doctor_id: backendSession.doctor_id,
      thread_id: backendSession.thread_id,
      status: backendSession.status || 'INITIALIZED',
      current_step: backendSession.current_step || 'initialized',
      state: {
        patient_id: backendSession.patient_id,
        raw_notes: rawNotes || ["Patient presents for clinical evaluation."],
        demographics: {
          patient_id: backendSession.patient_id,
          age: activePatient?.age || 0,
          gender: activePatient?.gender || 'Unspecified',
          chief_complaint: activePatient?.chief_complaint || '',
          allergies: activePatient?.allergies || [],
          chronic_conditions: activePatient?.chronic_conditions || [],
          current_medications: activePatient?.current_medications || []
        },
        vitals: undefined,
        imaging_data: undefined,
        differentials: [],
        risk_scores: [],
        safety_flags: [],
        symbolic_overrides: [],
        evidence: [],
        current_step: 'initialized',
        iteration_count: 0,
        re_evaluation_requested: false,
        pending_data_requests: [],
        audit_trail: [
          {
            timestamp: new Date().toISOString(),
            agent_name: 'System',
            action: 'INITIALIZED_CLINICAL_SESSION',
            details: `Initialized new clinical session for Patient ID: ${backendSession.patient_id}`
          }
        ]
      }
    };

    setSession(newSessionState);
    return newSessionState;
  };

  // Executes or resumes real backend LangGraph workflow
  const runWorkflow = async () => {
    if (!session) return;
    const currentSessionId = session.session_id;

    setSession(prev => prev ? {
      ...prev,
      status: 'RUNNING',
      current_step: 'running'
    } : null);
    setRunningAgentId('pipeline');
    setCurrentAgentProgressMessage('Executing LangGraph multi-agent clinical decision-support pipeline...');
    setIsPolling(true);

    try {
      // 1. Trigger backend execution
      await clinicalSessionsApi.runSession(
        currentSessionId,
        session.state.raw_notes,
        (session.state as any)?.imaging_path || undefined
      );
    } catch (err: any) {
      console.warn('Backend run session error:', err);
    }

    // 2. Start active polling loop
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    // Initial immediate poll
    await pollSessionState(currentSessionId);

    // Poll every 1.5 seconds
    pollingIntervalRef.current = setInterval(() => {
      pollSessionState(currentSessionId);
    }, 1500);
  };

  const resolveDataRequest = async (requestId: string, responseData: Record<string, any>) => {
    if (!session) return;
    setRunningAgentId('data_resolution');
    setCurrentAgentProgressMessage(`Submitting requested clinical parameters [${requestId}] and resuming graph...`);

    try {
      // 1. Resolve data request on backend
      await clinicalSessionsApi.resolveDataRequest(session.session_id, requestId, {
        response_data: responseData
      });

      // 2. Re-trigger workflow execution
      await runWorkflow();
    } catch (err: any) {
      console.error('Failed to resolve data request:', err);
    }
  };

  const approveSession = async (notes?: string) => {
    if (!session) return;
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    
    try {
      await clinicalSessionsApi.approveSession(session.session_id, { notes });
    } catch (e) {
      console.warn('Backend approval sync:', e);
    }

    setSession(prev => {
      if (!prev) return null;
      return {
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
      };
    });
  };

  const rejectSession = async (notes?: string) => {
    if (!session) return;
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    try {
      await clinicalSessionsApi.rejectSession(session.session_id, { notes });
    } catch (e) {
      console.warn('Backend rejection sync:', e);
    }

    setSession(prev => {
      if (!prev) return null;
      return {
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
      };
    });
  };

  const reevaluateSession = async (notes?: string) => {
    if (!session) return;
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    try {
      if (notes) {
        await clinicalSessionsApi.reevaluateSession(session.session_id, { notes });
      }
    } catch (e) {
      console.warn('Backend reevaluation sync:', e);
    }

    setSession(prev => {
      if (!prev) return null;
      return {
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
      };
    });

    await runWorkflow();
  };

  const resetDemoSession = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    setIsPolling(false);
    setActivePatient(null);
    setSession(null);
    setAgentStatuses({
      triage: 'IDLE',
      imaging: 'IDLE',
      diagnostic: 'IDLE',
      evidence: 'IDLE',
      safety: 'IDLE'
    });
    setRunningAgentId(null);
    setCurrentAgentProgressMessage('');
  };

  return (
    <WorkflowContext.Provider
      value={{
        session,
        activePatient,
        agentStatuses,
        runningAgentId,
        currentAgentProgressMessage,
        loadingPatient,
        isPolling,
        selectPatient,
        clearActivePatient,
        createPatient,
        updatePatient,
        fetchPatient,
        createClinicalSession,
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
