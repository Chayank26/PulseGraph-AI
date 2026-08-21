import React, { createContext, useContext, useState, useEffect } from 'react';
import type { Doctor } from '../types/clinical';
import { mockDoctor } from '../data/mockClinicalSession';

interface AuthContextType {
  doctor: Doctor | null;
  isAuthenticated: boolean;
  login: (doctorId: string, password?: string) => Promise<void>;
  signup: (details: Partial<Doctor>) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [doctor, setDoctor] = useState<Doctor | null>(() => {
    const saved = localStorage.getItem('pulsegraph_doctor');
    return saved ? JSON.parse(saved) : mockDoctor; // Default to mock doctor for Phase 1 demo
  });

  const isAuthenticated = !!doctor;

  useEffect(() => {
    if (doctor) {
      localStorage.setItem('pulsegraph_doctor', JSON.stringify(doctor));
    } else {
      localStorage.removeItem('pulsegraph_doctor');
    }
  }, [doctor]);

  const login = async (doctorId: string, _password?: string) => {
    // Phase 1 Mock Auth
    const activeDoc: Doctor = {
      ...mockDoctor,
      doctor_id: doctorId || mockDoctor.doctor_id
    };
    setDoctor(activeDoc);
    localStorage.setItem('pulsegraph_jwt_token', 'mock_jwt_token_2026');
  };

  const signup = async (details: Partial<Doctor>) => {
    const newDoc: Doctor = {
      doctor_id: details.doctor_id || `DOC-${Math.floor(10000 + Math.random() * 90000)}`,
      full_name: details.full_name || 'Dr. Physician',
      email: details.email || 'doctor@hospital.org',
      department: details.department || 'Emergency Medicine',
      role: details.role || 'Attending Physician'
    };
    setDoctor(newDoc);
    localStorage.setItem('pulsegraph_jwt_token', 'mock_jwt_token_2026');
  };

  const logout = () => {
    setDoctor(null);
    localStorage.removeItem('pulsegraph_doctor');
    localStorage.removeItem('pulsegraph_jwt_token');
  };

  return (
    <AuthContext.Provider value={{ doctor, isAuthenticated, login, signup, logout }}>
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
