import { apiClient } from './client';
import type { PatientDemographics } from '../types/clinical';

export const patientsApi = {
  createPatient: async (patient: PatientDemographics): Promise<PatientDemographics> => {
    const response = await apiClient.post('/patients', patient);
    return response.data;
  },

  getPatient: async (patientId: string): Promise<PatientDemographics> => {
    const response = await apiClient.get(`/patients/${patientId}`);
    return response.data;
  }
};
