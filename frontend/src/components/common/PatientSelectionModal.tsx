import React, { useState, useEffect } from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { patientsApi } from '../../api/patients';
import type { PatientDemographics } from '../../types/clinical';
import { User, Plus, Search, CheckCircle, Play, X, AlertCircle } from 'lucide-react';

interface PatientSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PatientSelectionModal: React.FC<PatientSelectionModalProps> = ({ isOpen, onClose }) => {
  const { createPatient, createClinicalSession, runWorkflow } = useWorkflow();

  const [patients, setPatients] = useState<PatientDemographics[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPatient, setSelectedPatient] = useState<PatientDemographics | null>(null);
  const [viewMode, setViewMode] = useState<'SELECT' | 'CREATE'>('SELECT');

  // Intake Form fields for starting a new clinical session
  const [intakeNotes, setIntakeNotes] = useState('Patient presents with acute chest discomfort radiating to left arm with diaphoresis.');
  const [heartRate, setHeartRate] = useState<number>(98);
  const [sysBP, setSysBP] = useState<number>(154);
  const [diaBP, setDiaBP] = useState<number>(92);
  const [spo2, setSpo2] = useState<number>(94);
  const [respRate, setRespRate] = useState<number>(22);
  const [imagePath, setImagePath] = useState('data/mock_patients/patient_001_cxr.png');

  // New Patient Form fields
  const [newPatientId, setNewPatientId] = useState('');
  const [newAge, setNewAge] = useState<number>(55);
  const [newGender, setNewGender] = useState('Male');
  const [newBloodType, setNewBloodType] = useState('A+');
  const [newAllergies, setNewAllergies] = useState('Penicillin');
  const [newConditions, setNewConditions] = useState('Hypertension');
  const [newMeds, setNewMeds] = useState('Aspirin 81mg');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Load existing patients from backend on mount
  useEffect(() => {
    if (isOpen) {
      loadPatients();
    }
  }, [isOpen]);

  const loadPatients = async () => {
    setLoading(true);
    setError('');
    try {
      const list = await patientsApi.listPatients();
      setPatients(list);
      if (list.length > 0 && !selectedPatient) {
        setSelectedPatient(list[0]);
      }
    } catch (err: any) {
      console.warn('Failed to load patients list from backend:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const filteredPatients = patients.filter(p =>
    p.patient_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (p.gender && p.gender.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const handleCreatePatientSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!newPatientId.trim()) {
      setError('Patient ID / MRN is required.');
      return;
    }

    try {
      setLoading(true);
      const created = await createPatient({
        patient_id: newPatientId,
        age: Number(newAge),
        gender: newGender,
        blood_type: newBloodType,
        allergies: newAllergies.split(',').map(s => s.trim()).filter(Boolean),
        chronic_conditions: newConditions.split(',').map(s => s.trim()).filter(Boolean),
        current_medications: newMeds.split(',').map(s => s.trim()).filter(Boolean)
      });
      setSelectedPatient(created);
      setViewMode('SELECT');
      await loadPatients();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create patient record.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartAnalysis = async () => {
    if (!selectedPatient) {
      setError('Please select or create a patient first.');
      return;
    }
    setError('');
    setLoading(true);

    try {
      // 1. Create real backend clinical session
      await createClinicalSession(selectedPatient.patient_id, [
        intakeNotes,
        `[INTAKE VITALS]: HR=${heartRate}bpm, BP=${sysBP}/${diaBP}mmHg, SpO2=${spo2}%, RR=${respRate}/min`,
        imagePath ? `cxr_path=${imagePath}` : ''
      ].filter(Boolean));

      onClose();

      // 2. Trigger real LangGraph execution workflow
      await runWorkflow();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to initialize clinical session.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[#FAF8F2] border-2 border-black rounded-2xl w-full max-w-4xl overflow-hidden shadow-2xl animate-fade-in font-sans max-h-[90vh] flex flex-col">
        {/* Modal Header */}
        <div className="bg-[#2A2B2E] text-white p-6 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <User size={22} className="text-[#E19B4C]" />
            <div>
              <h2 className="font-serif italic text-2xl font-bold">Clinical Session & Patient Selection</h2>
              <p className="text-xs text-gray-400 font-mono uppercase tracking-wider">
                Select patient & initialize real-time LangGraph multi-agent analysis
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white p-1 rounded-lg transition"
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {error && (
            <div className="bg-[#F7D8D8] border border-[#EAAFA0] text-[#8C2A2A] rounded-xl p-3 text-xs flex items-center gap-2 font-mono">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          {viewMode === 'SELECT' ? (
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
              {/* Left Column: Patient List & Search */}
              <div className="md:col-span-5 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C]">
                    REGISTERED PATIENTS ({patients.length})
                  </h3>
                  <button
                    onClick={() => setViewMode('CREATE')}
                    className="text-xs font-mono font-bold text-black uppercase flex items-center gap-1 hover:underline"
                  >
                    <Plus size={14} className="text-[#E19B4C]" />
                    <span>+ New Patient</span>
                  </button>
                </div>

                <div className="relative">
                  <Search size={14} className="absolute left-3 top-3 text-[#8C8A7B]" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search Patient ID / Gender..."
                    className="w-full bg-white border border-[#DCD8BE] rounded-xl pl-9 pr-4 py-2 text-xs font-mono font-semibold text-black focus:outline-none focus:ring-2 focus:ring-black"
                  />
                </div>

                <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                  {filteredPatients.map((p) => {
                    const isSelected = selectedPatient?.patient_id === p.patient_id;
                    return (
                      <div
                        key={p.patient_id}
                        onClick={() => setSelectedPatient(p)}
                        className={`p-3.5 rounded-xl border cursor-pointer transition flex items-center justify-between ${
                          isSelected
                            ? 'bg-[#2A2B2E] text-white border-black shadow-md'
                            : 'bg-white text-black border-[#DCD8BE] hover:border-black'
                        }`}
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-sm">{p.patient_id}</span>
                            {isSelected && <CheckCircle size={14} className="text-[#E19B4C]" />}
                          </div>
                          <p className={`text-xs ${isSelected ? 'text-gray-300' : 'text-[#66655C]'}`}>
                            Age {p.age || 'N/A'} • {p.gender || 'Unspecified'} • Blood: {p.blood_type || 'A+'}
                          </p>
                        </div>
                      </div>
                    );
                  })}

                  {filteredPatients.length === 0 && !loading && (
                    <div className="text-center p-6 bg-white border border-[#DCD8BE] rounded-xl text-xs text-[#66655C]">
                      No patients found. Click "+ New Patient" to register one.
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Selected Patient Intake Form */}
              <div className="md:col-span-7 space-y-4 border-l border-[#E2DFC9] pl-0 md:pl-6">
                {selectedPatient ? (
                  <div className="space-y-4">
                    <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-2">
                      <div className="flex items-center justify-between border-b border-[#E2DFC9] pb-2">
                        <span className="font-serif italic font-bold text-lg text-black">
                          Patient Profile: {selectedPatient.patient_id}
                        </span>
                        <span className="bg-[#E19B4C] text-black font-mono text-[10px] font-bold uppercase px-2.5 py-0.5 rounded-full">
                          SELECTED
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                        <div><span className="text-[10px] text-[#66655C]">Age:</span> {selectedPatient.age} Yrs</div>
                        <div><span className="text-[10px] text-[#66655C]">Gender:</span> {selectedPatient.gender}</div>
                        <div><span className="text-[10px] text-[#66655C]">Blood:</span> {selectedPatient.blood_type || 'A+'}</div>
                      </div>
                      <div className="text-xs pt-1">
                        <span className="font-bold text-[#66655C]">Allergies:</span> {selectedPatient.allergies?.join(', ') || 'None'}
                      </div>
                    </div>

                    <h4 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C]">
                      INITIAL CLINICAL INTAKE DATA
                    </h4>

                    <div className="space-y-3 text-xs">
                      <div>
                        <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1">
                          Chief Complaint & Presenting Symptoms
                        </label>
                        <textarea
                          rows={2}
                          value={intakeNotes}
                          onChange={(e) => setIntakeNotes(e.target.value)}
                          className="w-full bg-white border border-[#DCD8BE] rounded-xl p-3 text-xs text-black focus:outline-none focus:ring-2 focus:ring-black"
                        />
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono">
                        <div>
                          <label className="block text-[9px] uppercase text-[#66655C] mb-1">Heart Rate</label>
                          <input
                            type="number"
                            value={heartRate}
                            onChange={(e) => setHeartRate(Number(e.target.value))}
                            className="w-full bg-white border border-[#DCD8BE] rounded-lg px-2.5 py-1.5 font-bold text-black"
                          />
                        </div>
                        <div>
                          <label className="block text-[9px] uppercase text-[#66655C] mb-1">Blood Pressure</label>
                          <div className="flex items-center gap-1">
                            <input
                              type="number"
                              value={sysBP}
                              onChange={(e) => setSysBP(Number(e.target.value))}
                              className="w-full bg-white border border-[#DCD8BE] rounded-lg px-1.5 py-1.5 font-bold text-black"
                            />
                            <span>/</span>
                            <input
                              type="number"
                              value={diaBP}
                              onChange={(e) => setDiaBP(Number(e.target.value))}
                              className="w-full bg-white border border-[#DCD8BE] rounded-lg px-1.5 py-1.5 font-bold text-black"
                            />
                          </div>
                        </div>
                        <div>
                          <label className="block text-[9px] uppercase text-[#66655C] mb-1">SpO2 %</label>
                          <input
                            type="number"
                            value={spo2}
                            onChange={(e) => setSpo2(Number(e.target.value))}
                            className="w-full bg-white border border-[#DCD8BE] rounded-lg px-2.5 py-1.5 font-bold text-black"
                          />
                        </div>
                        <div>
                          <label className="block text-[9px] uppercase text-[#66655C] mb-1">Resp Rate</label>
                          <input
                            type="number"
                            value={respRate}
                            onChange={(e) => setRespRate(Number(e.target.value))}
                            className="w-full bg-white border border-[#DCD8BE] rounded-lg px-2.5 py-1.5 font-bold text-black"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1">
                          Chest X-Ray Radiograph DICOM / Image Path
                        </label>
                        <input
                          type="text"
                          value={imagePath}
                          onChange={(e) => setImagePath(e.target.value)}
                          placeholder="data/mock_patients/patient_001_cxr.png"
                          className="w-full bg-white border border-[#DCD8BE] rounded-lg p-2 font-mono text-xs text-black"
                        />
                      </div>
                    </div>

                    <div className="pt-3">
                      <button
                        onClick={handleStartAnalysis}
                        disabled={loading}
                        className="w-full bg-[#2A2B2E] text-white py-3 rounded-full font-mono text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 hover:bg-black shadow-lg"
                      >
                        <Play size={15} className="text-[#E19B4C]" />
                        <span>{loading ? 'Initializing Session & LangGraph...' : 'Start Clinical Analysis Workflow'}</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="text-center p-8 bg-white border border-[#DCD8BE] rounded-xl text-xs text-[#66655C]">
                    Select a patient from the list or create a new patient to initialize clinical session.
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* Create New Patient Sub-View */
            <form onSubmit={handleCreatePatientSubmit} className="space-y-4 text-xs font-sans max-w-xl mx-auto">
              <h3 className="font-serif italic text-xl font-bold text-black border-b border-[#E2DFC9] pb-2">
                Register New Patient Record in PostgreSQL
              </h3>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1">Patient ID / MRN *</label>
                  <input
                    type="text"
                    value={newPatientId}
                    onChange={(e) => setNewPatientId(e.target.value)}
                    placeholder="PAT-99120"
                    required
                    className="w-full bg-white border border-[#DCD8BE] rounded-lg px-3 py-2 font-mono font-bold text-black"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1">Age (Years) *</label>
                  <input
                    type="number"
                    value={newAge}
                    onChange={(e) => setNewAge(Number(e.target.value))}
                    required
                    className="w-full bg-white border border-[#DCD8BE] rounded-lg px-3 py-2 font-bold text-black"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1">Gender</label>
                  <select
                    value={newGender}
                    onChange={(e) => setNewGender(e.target.value)}
                    className="w-full bg-white border border-[#DCD8BE] rounded-lg px-3 py-2 font-bold text-black"
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1">Blood Type</label>
                  <input
                    type="text"
                    value={newBloodType}
                    onChange={(e) => setNewBloodType(e.target.value)}
                    placeholder="A+"
                    className="w-full bg-white border border-[#DCD8BE] rounded-lg px-3 py-2 font-mono font-bold text-black"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1">Documented Allergies</label>
                <input
                  type="text"
                  value={newAllergies}
                  onChange={(e) => setNewAllergies(e.target.value)}
                  placeholder="Penicillin, Sulfa"
                  className="w-full bg-white border border-[#DCD8BE] rounded-lg px-3 py-2 font-semibold text-black"
                />
              </div>

              <div>
                <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1">Chronic Conditions</label>
                <input
                  type="text"
                  value={newConditions}
                  onChange={(e) => setNewConditions(e.target.value)}
                  placeholder="Hypertension, Diabetes"
                  className="w-full bg-white border border-[#DCD8BE] rounded-lg px-3 py-2 font-semibold text-black"
                />
              </div>

              <div>
                <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1">Current Medications</label>
                <input
                  type="text"
                  value={newMeds}
                  onChange={(e) => setNewMeds(e.target.value)}
                  placeholder="Aspirin 81mg, Metoprolol 25mg"
                  className="w-full bg-white border border-[#DCD8BE] rounded-lg px-3 py-2 font-semibold text-black"
                />
              </div>

              <div className="pt-4 border-t border-[#E2DFC9] flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setViewMode('SELECT')}
                  className="text-xs font-mono text-[#66655C] underline uppercase"
                >
                  Back to Selection
                </button>

                <button
                  type="submit"
                  disabled={loading}
                  className="bg-[#2A2B2E] text-white px-6 py-2.5 rounded-full font-mono text-xs font-bold uppercase hover:bg-black"
                >
                  {loading ? 'Creating Record...' : 'Save & Select Patient'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
