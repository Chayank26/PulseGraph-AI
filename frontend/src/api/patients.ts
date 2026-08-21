import { apiClient } from './client';
import type { PatientDemographics } from '../types/clinical';

export interface CreatePatientPayload {
  patient_id: string;
  age?: number;
  gender?: string;
  blood_type?: string;
  allergies?: string[];
  chronic_conditions?: string[];
  current_medications?: string[];
}

export interface UpdatePatientPayload {
  age?: number;
  gender?: string;
  blood_type?: string;
  allergies?: string[];
  chronic_conditions?: string[];
  current_medications?: string[];
}

export const patientsApi = {
  createPatient: async (payload: CreatePatientPayload): Promise<PatientDemographics> => {
    const response = await apiClient.post<PatientDemographics>('/patients', payload);
    return response.data;
  },

  listPatients: async (): Promise<PatientDemographics[]> => {
    const response = await apiClient.get<PatientDemographics[]>('/patients');
    return response.data;
  },

  getPatient: async (patientId: string): Promise<PatientDemographics> => {
    const response = await apiClient.get<PatientDemographics>(`/patients/${patientId}`);
    return response.data;
  },

  updatePatient: async (patientId: string, payload: UpdatePatientPayload): Promise<PatientDemographics> => {
    const response = await apiClient.put<PatientDemographics>(`/patients/${patientId}`, payload);
    return response.data;
  }
};
