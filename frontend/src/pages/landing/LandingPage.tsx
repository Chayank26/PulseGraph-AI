import React from 'react';
import { Link } from 'react-router-dom';
import { Activity, ArrowRight } from 'lucide-react';
import { agentsList } from '../../data/mockClinicalSession';
import './LandingPage.css';

export const LandingPage: React.FC = () => {
  return (
    <div className="landing-page-shell">
      {/* Header Bar */}
      <header className="landing-header">
        <div className="landing-brand-box">
          <div className="landing-brand-avatar">
            PG
          </div>
          <div>
            <h1 className="landing-brand-title">PulseGraph</h1>
            <p className="landing-brand-subtitle">Neuro-Symbolic Engine</p>
          </div>
        </div>

        <div className="landing-auth-nav">
          <Link to="/login" className="landing-btn-signin">
            Sign In
          </Link>
          <Link to="/signup" className="landing-btn-signup">
            Create Account
          </Link>
        </div>
      </header>

      {/* Main Editorial Hero Section */}
      <main className="landing-main">
        {/* Editorial Title Block */}
        <div className="landing-hero-block">
          <div className="landing-subtitle-tag">
            <Activity size={14} className="landing-icon-accent" />
            <span>Clinical Decision Support Platform</span>
          </div>

          <h1 className="landing-title">
            PulseGraph
          </h1>

          <p className="landing-description">
            "Assist clinical reasoning with multimodal analysis, evidence retrieval, deterministic safety guardrails, and clinician-controlled decision making."
          </p>

          <div className="landing-cta-group">
            <Link to="/dashboard" className="landing-btn-launch group">
              <span>Launch Clinical Workspace</span>
              <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
            </Link>

            <Link to="/login" className="landing-btn-physician">
              Physician Sign In
            </Link>
          </div>
        </div>

        {/* Workflow Agent Pipeline Grid */}
        <div className="landing-pipeline-section">
          <div className="landing-pipeline-header">
            <h2 className="landing-pipeline-title">
              MULTI-AGENT CLINICAL REASONING STAGES
            </h2>
            <span className="landing-pipeline-badge">5 AGENTS • SEQUENTIAL BREAKPOINTS</span>
          </div>

          <div className="landing-agents-grid">
            {agentsList.map((agent) => (
              <div
                key={agent.id}
                style={{ backgroundColor: agent.color }}
                className="landing-agent-card"
              >
                <div>
                  <div className="landing-agent-num">
                    AGENT {agent.number}
                  </div>
                  <h3 className="landing-agent-name">
                    {agent.name}
                  </h3>
                  <p className="landing-agent-tagline">
                    {agent.tagline}
                  </p>
                </div>

                <div className="landing-agent-footer">
                  <span>STAGE {agent.number}</span>
                  <span>VERIFIED</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="landing-footer">
        PulseGraph AI Clinical Decision Support Engine — Human Clinical Review Mandatory.
      </footer>
    </div>
  );
};
