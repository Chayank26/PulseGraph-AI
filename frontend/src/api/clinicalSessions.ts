import { apiClient } from './client';
import type { ClinicalSession, ClinicalDataRequest } from '../types/clinical';

export interface CreateSessionPayload {
  patient_id: string;
  raw_notes?: string[];
}

export interface ResolveDataRequestPayload {
  response_data: Record<string, any>;
}

export interface ReviewActionPayload {
  notes?: string;
}

export const clinicalSessionsApi = {
  createSession: async (payload: CreateSessionPayload): Promise<ClinicalSession> => {
    const response = await apiClient.post('/clinical/sessions', payload);
    return response.data;
  },

  runSession: async (sessionId: string): Promise<any> => {
    const response = await apiClient.post(`/clinical/sessions/${sessionId}/run`);
    return response.data;
  },

  getDataRequests: async (sessionId: string): Promise<ClinicalDataRequest[]> => {
    const response = await apiClient.get(`/clinical/sessions/${sessionId}/data-requests`);
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

  reevaluateSession: async (sessionId: string, payload?: ReviewActionPayload): Promise<any> => {
    const response = await apiClient.post(`/clinical/sessions/${sessionId}/reevaluate`, payload || {});
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
