import { apiClient } from './client';
import type { Doctor } from '../types/clinical';

export const doctorsApi = {
  getCurrentProfile: async (): Promise<Doctor> => {
    const response = await apiClient.get<Doctor>('/doctors/me');
    return response.data;
  },

  listDoctors: async (): Promise<Doctor[]> => {
    const response = await apiClient.get<Doctor[]>('/doctors');
    return response.data;
  }
};
