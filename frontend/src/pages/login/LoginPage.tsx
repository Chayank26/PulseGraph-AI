import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { LogIn, User, Lock, AlertCircle } from 'lucide-react';
import './LoginPage.css';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [doctorId, setDoctorId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!doctorId.trim()) {
      setError('Please enter your Doctor ID.');
      return;
    }
    if (!password) {
      setError('Please enter your password.');
      return;
    }

    try {
      setLoading(true);
      await login(doctorId, password);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="login-box-header">
        <h2 className="login-title">Physician Sign In</h2>
        <p className="login-subtitle">
          Access your PulseGraph multi-agent CDS session workspace.
        </p>
      </div>

      {error && (
        <div className="login-error-alert">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="login-form">
        <div className="login-field-group">
          <label className="login-label">
            Doctor ID
          </label>
          <div className="login-input-wrapper">
            <User size={16} className="login-input-icon" />
            <input
              type="text"
              value={doctorId}
              onChange={(e) => setDoctorId(e.target.value)}
              placeholder="e.g. DOC-88204"
              required
              className="login-input"
            />
          </div>
        </div>

        <div className="login-field-group">
          <label className="login-label">
            Password
          </label>
          <div className="login-input-wrapper">
            <Lock size={16} className="login-input-icon" />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              className="login-input"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="login-btn-submit"
        >
          <LogIn size={15} />
          <span>{loading ? 'Authenticating Physician...' : 'Sign In to Workspace'}</span>
        </button>
      </form>

      <div className="login-footer-text">
        Don't have an account?{' '}
        <Link to="/signup" className="login-link">
          Register Doctor Profile
        </Link>
      </div>
    </div>
  );
};
