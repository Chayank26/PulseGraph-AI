import React, { createContext, useContext, useState, useEffect } from 'react';
import type { Doctor } from '../types/clinical';
import { authApi } from '../api/auth';
import type { SignupPayload } from '../api/auth';

interface AuthContextType {
  doctor: Doctor | null;
  isAuthenticated: boolean;
  loading: boolean;
  authError: string | null;
  login: (doctorId: string, password: string) => Promise<void>;
  signup: (details: SignupPayload) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [authError, setAuthError] = useState<string | null>(null);

  const isAuthenticated = !!doctor && !!localStorage.getItem('pulsegraph_jwt_token');

  // Verify stored JWT and fetch doctor profile on app load
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('pulsegraph_jwt_token');
      if (token) {
        try {
          const currentDoc = await authApi.getCurrentDoctor();
          setDoctor(currentDoc);
        } catch (err) {
          console.warn('Session expired or invalid token on startup:', err);
          localStorage.removeItem('pulsegraph_jwt_token');
          setDoctor(null);
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (doctorId: string, password: string) => {
    setAuthError(null);
    setLoading(true);
    try {
      const tokenResp = await authApi.login({ doctor_id: doctorId, password });
      localStorage.setItem('pulsegraph_jwt_token', tokenResp.access_token);
      
      const docProfile: Doctor = {
        doctor_id: tokenResp.doctor_id,
        full_name: tokenResp.full_name,
        department: tokenResp.department,
        role: tokenResp.role
      };
      setDoctor(docProfile);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Authentication failed. Please check credentials.';
      setAuthError(errorMsg);
      throw new Error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const signup = async (details: SignupPayload) => {
    setAuthError(null);
    setLoading(true);
    try {
      await authApi.signup(details);
      // Automatically authenticate after successful registration
      await login(details.doctor_id, details.password);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Registration failed.';
      setAuthError(errorMsg);
      throw new Error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setDoctor(null);
    setAuthError(null);
    localStorage.removeItem('pulsegraph_jwt_token');
  };

  const clearError = () => setAuthError(null);

  return (
    <AuthContext.Provider
      value={{
        doctor,
        isAuthenticated,
        loading,
        authError,
        login,
        signup,
        logout,
        clearError
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
