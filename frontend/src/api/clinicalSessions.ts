import { apiClient } from './client';
import type { ClinicalSession, ClinicalDataRequest } from '../types/clinical';

export interface CreateSessionPayload {
  patient_id: string;
  raw_notes?: string[];
  vitals?: {
    heart_rate_bpm?: number;
    blood_pressure_sys?: number;
    blood_pressure_dia?: number;
    temperature_c?: number;
    respiratory_rate?: number;
    spo2_percent?: number;
  };
  image_path?: string;
}

export interface ResolveDataRequestPayload {
  response_data: Record<string, any>;
}

export interface ReviewActionPayload {
  notes?: string;
}

export interface ReevaluatePayload {
  notes: string;
}

export const clinicalSessionsApi = {
  createSession: async (payload: CreateSessionPayload): Promise<ClinicalSession> => {
    const response = await apiClient.post<ClinicalSession>('/clinical/sessions', payload);
    return response.data;
  },

  getSession: async (sessionId: string): Promise<ClinicalSession> => {
    const response = await apiClient.get<ClinicalSession>(`/clinical/sessions/${sessionId}`);
    return response.data;
  },

  listSessions: async (): Promise<ClinicalSession[]> => {
    const response = await apiClient.get<ClinicalSession[]>('/clinical/sessions');
    return response.data;
  },

  runSession: async (sessionId: string, raw_notes?: string[], image_path?: string): Promise<any> => {
    const response = await apiClient.post(`/clinical/sessions/${sessionId}/run`, null, {
      params: { raw_notes, image_path }
    });
    return response.data;
  },

  getDataRequests: async (sessionId: string): Promise<ClinicalDataRequest[]> => {
    const response = await apiClient.get<ClinicalDataRequest[]>(`/clinical/sessions/${sessionId}/data-requests`);
    return response.data;
  },

  resolveDataRequest: async (sessionId: string, requestId: string, payload: ResolveDataRequestPayload): Promise<any> => {
    const response = await apiClient.post(`/clinical/sessions/${sessionId}/data-requests/${requestId}/resolve`, payload);
    return response.data;
  },

  getReviewPackage: async (sessionId: string): Promise<any> => {
    const response = await apiClient.get(`/clinical/sessions/${sessionId}/review`);
    return response.data;
  },

  approveSession: async (sessionId: string, payload?: ReviewActionPayload): Promise<any> => {
    const response = await apiClient.post(`/clinical/sessions/${sessionId}/approve`, payload || {});
    return response.data;
  },

  rejectSession: async (sessionId: string, payload?: ReviewActionPayload): Promise<any> => {
    const response = await apiClient.post(`/clinical/sessions/${sessionId}/reject`, payload || {});
    return response.data;
  },

  reevaluateSession: async (sessionId: string, payload: ReevaluatePayload): Promise<any> => {
    const response = await apiClient.post(`/clinical/sessions/${sessionId}/reevaluate`, payload);
    return response.data;
  },

  getAuditTrail: async (sessionId: string): Promise<any[]> => {
    const response = await apiClient.get(`/clinical/sessions/${sessionId}/audit-trail`);
    return response.data;
  },

  getCDSResults: async (sessionId: string): Promise<any> => {
    const response = await apiClient.get(`/clinical/sessions/${sessionId}/results`);
    return response.data;
  }
};
