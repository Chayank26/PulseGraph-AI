import React, { useEffect, useState } from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { AuditTimeline } from '../../components/common/AuditTimeline';
import { PatientSelectionModal } from '../../components/common/PatientSelectionModal';
import { patientsApi } from '../../api/patients';
import type { PatientDemographics } from '../../types/clinical';
import { Activity, PlayCircle, User, PlusCircle, Search, ArrowRight, RotateCcw, Stethoscope } from 'lucide-react';
import './DashboardPage.css';

export const DashboardPage: React.FC = () => {
  const { session, activePatient, selectPatient, clearActivePatient, runningAgentId, currentAgentProgressMessage } = useWorkflow();

  const [patients, setPatients] = useState<PatientDemographics[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Load existing patients from backend on mount
  useEffect(() => {
    loadPatients();
  }, [activePatient]);

  const loadPatients = async () => {
    setLoading(true);
    try {
      const list = await patientsApi.listPatients();
      setPatients(list);
    } catch (err) {
      console.warn('Notice loading patients:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredPatients = patients.filter(p =>
    p.patient_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (p.gender && p.gender.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (p.chief_complaint && p.chief_complaint.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  // STATE A: NO ACTIVE PATIENT CHOSEN -> SHOW PHYSICIAN PATIENT DIRECTORY
  if (!activePatient) {
    return (
      <div className="dashboard-shell animate-fade-in max-w-7xl mx-auto py-6 px-4">
        {/* Physician Directory Header Banner */}
        <div className="bg-[#FFFFFF] border-2 border-black rounded-2xl p-6 shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-2.5 h-2.5 rounded-full bg-[#E19B4C] animate-pulse"></span>
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#66655C]">Physician Patient Directory</span>
            </div>
            <h1 className="font-serif italic text-3xl md:text-4xl text-[#1A1A1C] font-bold">
              Select or Register a Patient
            </h1>
            <p className="text-sm text-[#4A4943] mt-1 max-w-2xl">
              Choose an existing patient to launch their multi-agent clinical workspace or register a new patient to initialize CDS analysis.
            </p>
          </div>

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="bg-[#1A1A1C] text-white hover:bg-black font-mono text-sm font-bold uppercase tracking-wider px-6 py-3 rounded-full flex items-center gap-2 shadow-lg transition transform hover:-translate-y-0.5 cursor-pointer flex-shrink-0"
          >
            <PlusCircle size={18} className="text-[#E19B4C]" />
            <span>Create New Patient</span>
          </button>
        </div>

        {/* Filter & Search Toolbar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-6">
          <div className="relative w-full sm:w-96">
            <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search Patient ID / MRN, Gender..."
              className="w-full bg-white border border-[#DCD8BE] rounded-xl pl-10 pr-4 py-2.5 text-sm font-sans focus:outline-none focus:border-black transition"
            />
          </div>

          <span className="text-xs font-mono text-[#66655C] font-semibold">
            {filteredPatients.length} PATIENTS FOUND
          </span>
        </div>

        {/* Patients Grid */}
        {loading ? (
          <div className="py-16 text-center text-sm font-mono text-gray-500">
            Loading physician patient records...
          </div>
        ) : filteredPatients.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-6">
            {filteredPatients.map((patient) => (
              <div
                key={patient.patient_id}
                className="bg-white border-2 border-black rounded-2xl p-6 shadow-sm flex flex-col justify-between hover:shadow-md transition group"
              >
                <div>
                  <div className="flex items-center justify-between border-b border-[#E2DFC9] pb-3 mb-4">
                    <div className="flex items-center gap-2.5">
                      <div className="w-10 h-10 rounded-xl bg-[#2A2B2E] text-white flex items-center justify-center font-mono font-bold text-sm">
                        <User size={18} className="text-[#E19B4C]" />
                      </div>
                      <div>
                        <h3 className="font-mono font-bold text-base text-black">
                          {patient.patient_id}
                        </h3>
                        <p className="text-xs text-[#66655C]">
                          Age {patient.age || 'N/A'} • {patient.gender || 'Unspecified'} {patient.blood_type ? `• Blood ${patient.blood_type}` : ''}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Complaint & History */}
                  <div className="space-y-3 mb-6">
                    {patient.chief_complaint && (
                      <div>
                        <span className="text-[10px] font-mono uppercase font-bold text-[#8C8A7B]">Chief Complaint</span>
                        <p className="font-serif italic text-sm text-[#1A1A1C] line-clamp-2">
                          "{patient.chief_complaint}"
                        </p>
                      </div>
                    )}

                    {patient.chronic_conditions && patient.chronic_conditions.length > 0 && (
                      <div>
                        <span className="text-[10px] font-mono uppercase font-bold text-[#8C8A7B]">Chronic Conditions</span>
                        <div className="flex flex-wrap gap-1.5 mt-1">
                          {patient.chronic_conditions.map((c, i) => (
                            <span key={i} className="bg-[#F5F3EB] border border-[#E2DFC9] text-[11px] px-2 py-0.5 rounded-md font-sans text-[#1A1A1C]">
                              {c}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Card Action Button */}
                <button
                  onClick={() => selectPatient(patient)}
                  className="w-full bg-[#FAF8F2] border-2 border-black hover:bg-[#1A1A1C] hover:text-white font-mono text-xs font-bold uppercase tracking-wider py-3 rounded-xl flex items-center justify-center gap-2 transition cursor-pointer"
                >
                  <span>Select & Open Workspace</span>
                  <ArrowRight size={14} />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white border-2 border-dashed border-[#DCD8BE] rounded-2xl p-12 text-center mt-6">
            <Stethoscope size={36} className="mx-auto text-gray-400 mb-3" />
            <h3 className="font-serif text-xl font-bold text-black">No Patients Registered Yet</h3>
            <p className="text-xs text-[#66655C] mt-1 max-w-md mx-auto">
              You do not have any patient records registered in your directory. Click below to register your first patient and launch CDS analysis.
            </p>
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="mt-5 bg-[#1A1A1C] text-white font-mono text-xs font-bold uppercase px-6 py-2.5 rounded-full inline-flex items-center gap-2 hover:bg-black transition cursor-pointer"
            >
              <PlusCircle size={15} className="text-[#E19B4C]" />
              <span>Create First Patient Record</span>
            </button>
          </div>
        )}

        {/* Patient Selection Modal */}
        <PatientSelectionModal
          isOpen={isCreateModalOpen}
          onClose={() => {
            setIsCreateModalOpen(false);
            loadPatients();
          }}
        />
      </div>
    );
  }

  // STATE B: PATIENT IS SELECTED -> RENDER ACTIVE MULTI-AGENT WORKSPACE
  const state = session?.state || {
    patient_id: activePatient.patient_id,
    demographics: activePatient,
    vitals: null,
    risk_scores: [],
    differentials: [],
    imaging_data: null,
    audit_trail: []
  };

  const topRiskScore = state.risk_scores?.[0];

  return (
    <div className="dashboard-shell animate-fade-in">
      {/* Active Patient Switch Bar */}
      <div className="bg-white border-2 border-black rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-[#2A2B2E] text-white flex items-center justify-center font-mono font-bold text-xs">
            <User size={16} className="text-[#E19B4C]" />
          </div>
          <div>
            <h2 className="font-mono font-bold text-sm text-black uppercase">
              ACTIVE PATIENT WORKSPACE: {activePatient.patient_id}
            </h2>
            <p className="text-xs text-[#66655C]">
              Age {activePatient.age || 'N/A'} • {activePatient.gender || 'Unspecified'} {activePatient.blood_type ? `• Blood ${activePatient.blood_type}` : ''}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={clearActivePatient}
            className="bg-[#FAF8F2] border border-black hover:bg-[#E2DFC9] text-black font-mono text-xs font-bold uppercase px-4 py-2 rounded-full flex items-center gap-1.5 transition cursor-pointer"
          >
            <RotateCcw size={13} />
            <span>Switch / Select Patient</span>
          </button>
        </div>
      </div>

      {/* Running Agent Active Banner */}
      {runningAgentId && (
        <div className="dashboard-running-banner animate-pulse">
          <div className="dashboard-running-left">
            <PlayCircle size={20} className="text-[#1E3A8A] animate-spin" />
            <div>
              <p className="dashboard-running-title">
                AGENT PIPELINE EXECUTING — {runningAgentId.toUpperCase()}
              </p>
              <p className="dashboard-running-msg">
                {currentAgentProgressMessage}
              </p>
            </div>
          </div>
          <span className="dashboard-running-badge">
            PROCESSING
          </span>
        </div>
      )}

      {/* Main Layout Container */}
      <div className="dashboard-main-grid">
        {/* Left 8-Column Main Dashboard Area */}
        <div className="dashboard-left-col">
          {/* Hero Headline */}
          <div className="pt-2">
            <h1 className="dashboard-hero-title">
              PULSE DEVIATION
            </h1>
            <p className="dashboard-hero-complaint">
              {state.demographics?.chief_complaint || 'Patient clinical session initialized. Run pipeline to process clinical notes and vitals.'}
            </p>
          </div>

          {/* Three-Column Editorial Data Row */}
          <div className="dashboard-editorial-row">
            {/* Column 1: DIFFERENTIAL DIAGNOSIS */}
            <div className="dashboard-editorial-col">
              <h3 className="dashboard-col-title">
                DIFFERENTIAL DIAGNOSIS
              </h3>
              {state.differentials && state.differentials.length > 0 ? (
                <ol className="dashboard-diff-list">
                  {state.differentials.slice(0, 3).map((diff, idx) => (
                    <li key={idx} className="dashboard-diff-item">
                      <span className="dashboard-diff-num">{idx + 1}.</span>
                      <span>{diff.disease_name.split(' (')[0]}</span>{' '}
                      <span className="dashboard-diff-pct">
                        ({diff.likelihood_percentage}%)
                      </span>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="text-xs text-[#8C8A7B] italic">Awaiting pipeline differential analysis...</p>
              )}
            </div>

            {/* Column 2: IMAGING FINDINGS */}
            <div className="dashboard-editorial-col">
              <h3 className="dashboard-col-title">
                IMAGING FINDINGS
              </h3>
              <p className="dashboard-imaging-text">
                {state.imaging_data?.impression ||
                  'No radiograph scan processed yet. Upload or path CXR file in patient intake.'}
              </p>
            </div>

            {/* Column 3: RISK SCORE */}
            <div className="dashboard-editorial-col">
              <h3 className="dashboard-col-title">
                RISK SCORE
              </h3>
              {topRiskScore ? (
                <div className="dashboard-risk-score-box">
                  <p className="dashboard-risk-score-name">
                    {topRiskScore.score_name}: {topRiskScore.score_value}{' '}
                    <span className="dashboard-risk-score-level">
                      ({topRiskScore.risk_level.replace('_', ' ')})
                    </span>
                  </p>
                  <p className="dashboard-risk-rec">
                    <strong className="font-semibold text-black">Recommendation:</strong> {topRiskScore.recommendation}
                  </p>
                </div>
              ) : (
                <p className="text-xs text-[#8C8A7B] italic">Awaiting risk score computation...</p>
              )}
            </div>
          </div>

          {/* Patient Overview & Vitals Panel */}
          <div className="dashboard-patient-panel">
            <div className="dashboard-patient-panel-header">
              <h3 className="dashboard-patient-panel-title">
                <Activity size={16} className="text-[#E19B4C]" />
                <span>Patient Clinical Profile & Vital Signs</span>
              </h3>
              <span className="text-xs font-mono text-[#66655C] font-medium">
                MRN: {activePatient.patient_id} • Age {activePatient.age || 'N/A'} ({activePatient.gender || 'Unspecified'})
              </span>
            </div>

            {/* Vital Signs Grid */}
            <div className="dashboard-vitals-grid">
              <div className="dashboard-vital-card">
                <span className="dashboard-vital-label">Heart Rate</span>
                <p className="dashboard-vital-value">
                  {state.vitals?.heart_rate_bpm ? `${state.vitals.heart_rate_bpm} bpm` : '--'}
                </p>
              </div>

              <div className="dashboard-vital-card">
                <span className="dashboard-vital-label">Blood Pressure</span>
                <p className="dashboard-vital-value">
                  {state.vitals?.systolic_bp_mmhg ? `${state.vitals.systolic_bp_mmhg}/${state.vitals.diastolic_bp_mmhg} mmHg` : '--'}
                </p>
              </div>

              <div className="dashboard-vital-card">
                <span className="dashboard-vital-label">SpO2 Saturation</span>
                <p className="dashboard-vital-value">
                  {state.vitals?.spo2_percent ? `${state.vitals.spo2_percent}%` : '--'}
                </p>
              </div>

              <div className="dashboard-vital-card">
                <span className="dashboard-vital-label">Resp Rate</span>
                <p className="dashboard-vital-value">
                  {state.vitals?.resp_rate_bpm ? `${state.vitals.resp_rate_bpm} /min` : '--'}
                </p>
              </div>
            </div>

            {/* Medical History & Current Medications */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#1A1A1C] mb-2">
                  Chronic Conditions
                </h4>
                {activePatient.chronic_conditions && activePatient.chronic_conditions.length > 0 ? (
                  <ul className="space-y-1 text-xs text-[#4A4943] list-disc list-inside">
                    {activePatient.chronic_conditions.map((h, i) => (
                      <li key={i}>{h}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-[#8C8A7B] italic">No chronic conditions recorded.</p>
                )}
              </div>

              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#1A1A1C] mb-2">
                  Active Medications
                </h4>
                {activePatient.current_medications && activePatient.current_medications.length > 0 ? (
                  <ul className="space-y-1 text-xs text-[#4A4943] list-disc list-inside font-mono">
                    {activePatient.current_medications.map((m, i) => (
                      <li key={i}>{m}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-[#8C8A7B] italic">No active medications recorded.</p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Right 4-Column Audit Trail Panel */}
        <div className="dashboard-right-col">
          <AuditTimeline />
        </div>
      </div>
    </div>
  );
};
