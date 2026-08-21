import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { UserPlus, User, Mail, AlertCircle } from 'lucide-react';
import './SignupPage.css';

export const SignupPage: React.FC = () => {
  const navigate = useNavigate();
  const { signup } = useAuth();

  const [fullName, setFullName] = useState('Dr. Sarah Chen');
  const [doctorId, setDoctorId] = useState('DOC-88204');
  const [email, setEmail] = useState('sarah.chen@hospital.org');
  const [department, setDepartment] = useState('Emergency Medicine');
  const [password, setPassword] = useState('Password123!');
  const [confirmPassword, setConfirmPassword] = useState('Password123!');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    try {
      setLoading(true);
      await signup({
        full_name: fullName,
        doctor_id: doctorId,
        department,
        password,
        role: 'Attending Physician'
      });
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="signup-box-header">
        <h2 className="signup-title">Register Doctor Profile</h2>
        <p className="signup-subtitle">
          Create an authenticated physician account for clinical decision support.
        </p>
      </div>

      {error && (
        <div className="signup-error-alert">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="signup-form">
        <div className="signup-field-group">
          <label className="signup-label">
            Full Name
          </label>
          <div className="signup-input-wrapper">
            <User size={15} className="signup-input-icon" />
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Dr. Sarah Chen, MD"
              required
              className="signup-input"
            />
          </div>
        </div>

        <div className="signup-grid-2">
          <div className="signup-field-group">
            <label className="signup-label">
              Doctor ID
            </label>
            <input
              type="text"
              value={doctorId}
              onChange={(e) => setDoctorId(e.target.value)}
              placeholder="DOC-88204"
              required
              className="signup-input font-mono"
            />
          </div>

          <div className="signup-field-group">
            <label className="signup-label">
              Department
            </label>
            <input
              type="text"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              placeholder="e.g. Emergency Medicine"
              required
              className="signup-input"
            />
          </div>
        </div>

        <div className="signup-field-group">
          <label className="signup-label">
            Hospital Email
          </label>
          <div className="signup-input-wrapper">
            <Mail size={15} className="signup-input-icon" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="sarah.chen@hospital.org"
              required
              className="signup-input"
            />
          </div>
        </div>

        <div className="signup-grid-2">
          <div className="signup-field-group">
            <label className="signup-label">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              className="signup-input font-mono"
            />
          </div>

          <div className="signup-field-group">
            <label className="signup-label">
              Confirm Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              className="signup-input font-mono"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="signup-btn-submit"
        >
          <UserPlus size={15} />
          <span>{loading ? 'Creating Doctor Account...' : 'Register Physician Profile'}</span>
        </button>
      </form>

      <div className="signup-footer-text">
        Already registered?{' '}
        <Link to="/login" className="signup-link">
          Sign In Here
        </Link>
      </div>
    </div>
  );
};
