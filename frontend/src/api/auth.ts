import { apiClient } from './client';
import type { Doctor } from '../types/clinical';

export interface LoginPayload {
  doctor_id: string;
  password: string;
}

export interface SignupPayload {
  doctor_id: string;
  full_name: string;
  email: string;
  department: string;
  password: string;
  role?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  doctor: Doctor;
}

export const authApi = {
  login: async (payload: LoginPayload): Promise<AuthResponse> => {
    const response = await apiClient.post('/auth/login', payload);
    return response.data;
  },

  signup: async (payload: SignupPayload): Promise<Doctor> => {
    const response = await apiClient.post('/doctors', payload);
    return response.data;
  },

  getCurrentDoctor: async (): Promise<Doctor> => {
    const response = await apiClient.get('/doctors/me');
    return response.data;
  }
};
