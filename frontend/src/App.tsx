import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { WorkflowProvider } from './context/WorkflowContext';

import { AppLayout } from './layouts/AppLayout';
import { AuthLayout } from './layouts/AuthLayout';

import { LandingPage } from './pages/landing/LandingPage';
import { LoginPage } from './pages/login/LoginPage';
import { SignupPage } from './pages/signup/SignupPage';
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { TriagePage } from './pages/triage/TriagePage';
import { ImagingPage } from './pages/imaging/ImagingPage';
import { DiagnosticPage } from './pages/diagnostic/DiagnosticPage';
import { EvidencePage } from './pages/evidence/EvidencePage';
import { SafetyPage } from './pages/safety/SafetyPage';
import { SymbolicGuardPage } from './pages/symbolic/SymbolicGuardPage';
import { AuditPage } from './pages/audit/AuditPage';
import { ReviewPage } from './pages/review/ReviewPage';

// Protected Route Guard
const ProtectedRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

export const App: React.FC = () => {
  return (
    <Router>
      <AuthProvider>
        <WorkflowProvider>
          <Routes>
            {/* Public Landing Page */}
            <Route path="/" element={<LandingPage />} />

            {/* Auth Layout Routes */}
            <Route element={<AuthLayout />}>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/signup" element={<SignupPage />} />
            </Route>

            {/* Authenticated Clinical Application Shell Routes */}
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/triage" element={<TriagePage />} />
              <Route path="/imaging" element={<ImagingPage />} />
              <Route path="/diagnostic" element={<DiagnosticPage />} />
              <Route path="/evidence" element={<EvidencePage />} />
              <Route path="/safety" element={<SafetyPage />} />
              <Route path="/symbolic-guard" element={<SymbolicGuardPage />} />
              <Route path="/audit" element={<AuditPage />} />
              <Route path="/review" element={<ReviewPage />} />
            </Route>

            {/* Fallback route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </WorkflowProvider>
      </AuthProvider>
    </Router>
  );
};

export default App;
