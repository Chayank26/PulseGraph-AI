import { apiClient } from './client';
import type { Doctor } from '../types/clinical';

export interface LoginPayload {
  doctor_id: string;
  password: string;
}

export interface SignupPayload {
  doctor_id: string;
  full_name: string;
  department: string;
  password: string;
  role?: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  doctor_id: string;
  full_name: string;
  department: string;
  role: string;
}

export const authApi = {
  login: async (payload: LoginPayload): Promise<AuthTokenResponse> => {
    const response = await apiClient.post<AuthTokenResponse>('/auth/login', payload);
    return response.data;
  },

  signup: async (payload: SignupPayload): Promise<Doctor> => {
    const response = await apiClient.post<Doctor>('/doctors', payload);
    return response.data;
  },

  getCurrentDoctor: async (): Promise<Doctor> => {
    const response = await apiClient.get<Doctor>('/doctors/me');
    return response.data;
  }
};
