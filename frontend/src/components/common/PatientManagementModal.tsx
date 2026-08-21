import React, { useState } from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { User, Plus, Edit2, X, AlertCircle, Play } from 'lucide-react';

interface PatientModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PatientManagementModal: React.FC<PatientModalProps> = ({ isOpen, onClose }) => {
  const { activePatient, createPatient, updatePatient, createClinicalSession } = useWorkflow();

  const [mode, setMode] = useState<'VIEW' | 'CREATE' | 'EDIT'>('VIEW');
  const [patientId, setPatientId] = useState(activePatient?.patient_id || 'PAT-88291');
  const [age, setAge] = useState<number>(activePatient?.age || 58);
  const [gender, setGender] = useState<string>(activePatient?.gender || 'Male');
  const [bloodType, setBloodType] = useState<string>(activePatient?.blood_type || 'A+');
  const [allergies, setAllergies] = useState<string>(activePatient?.allergies?.join(', ') || 'Penicillin');
  const [chronicConditions, setChronicConditions] = useState<string>(activePatient?.chronic_conditions?.join(', ') || 'Hypertension, Type 2 Diabetes');
  const [currentMedications, setCurrentMedications] = useState<string>(activePatient?.current_medications?.join(', ') || 'Metformin 500mg, Lisinopril 10mg');

  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!patientId.trim()) {
      setError('Patient Identifier / MRN is required.');
      return;
    }

    try {
      setLoading(true);
      await createPatient({
        patient_id: patientId,
        age: Number(age),
        gender,
        blood_type: bloodType,
        allergies: allergies.split(',').map(s => s.trim()).filter(Boolean),
        chronic_conditions: chronicConditions.split(',').map(s => s.trim()).filter(Boolean),
        current_medications: currentMedications.split(',').map(s => s.trim()).filter(Boolean)
      });
      setMode('VIEW');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create patient record.');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      setLoading(true);
      await updatePatient(patientId, {
        age: Number(age),
        gender,
        blood_type: bloodType,
        allergies: allergies.split(',').map(s => s.trim()).filter(Boolean),
        chronic_conditions: chronicConditions.split(',').map(s => s.trim()).filter(Boolean),
        current_medications: currentMedications.split(',').map(s => s.trim()).filter(Boolean)
      });
      setMode('VIEW');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update patient record.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartSession = async () => {
    setError('');
    try {
      setLoading(true);
      await createClinicalSession(patientId, [
        "Patient presents with acute chest discomfort.",
        "Requires HEART score calculation, CheXNet radiograph scan analysis, and safety audit."
      ]);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to initialize clinical session.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[#FAF8F2] border-2 border-black rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl animate-fade-in font-sans">
        {/* Header */}
        <div className="bg-[#2A2B2E] text-white p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <User size={22} className="text-[#E19B4C]" />
            <div>
              <h2 className="font-serif italic text-2xl font-bold">Patient Management</h2>
              <p className="text-xs text-gray-400 font-mono uppercase tracking-wider">
                {mode === 'VIEW' ? 'Current Patient Record' : mode === 'CREATE' ? 'Register New Patient' : 'Edit Patient Demographics'}
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

        {/* Modal Body */}
        <div className="p-6 space-y-6">
          {error && (
            <div className="bg-[#F7D8D8] border border-[#EAAFA0] text-[#8C2A2A] rounded-xl p-3 text-xs flex items-center gap-2 font-mono">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          {mode === 'VIEW' && activePatient && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-white border border-[#DCD8BE] rounded-xl p-4 text-xs font-mono">
                <div>
                  <span className="text-[10px] text-[#66655C] uppercase">PATIENT ID</span>
                  <p className="font-bold text-black text-sm">{activePatient.patient_id}</p>
                </div>
                <div>
                  <span className="text-[10px] text-[#66655C] uppercase">AGE</span>
                  <p className="font-bold text-black text-sm">{activePatient.age} YRS</p>
                </div>
                <div>
                  <span className="text-[10px] text-[#66655C] uppercase">GENDER</span>
                  <p className="font-bold text-black text-sm">{activePatient.gender}</p>
                </div>
                <div>
                  <span className="text-[10px] text-[#66655C] uppercase">BLOOD TYPE</span>
                  <p className="font-bold text-black text-sm">{activePatient.blood_type || 'A+'}</p>
                </div>
              </div>

              <div className="space-y-3 text-xs">
                <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-1">
                  <span className="text-[10px] font-mono text-[#66655C] uppercase font-bold">Documented Allergies</span>
                  <p className="text-black font-semibold">
                    {activePatient.allergies?.length ? activePatient.allergies.join(', ') : 'None documented'}
                  </p>
                </div>

                <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-1">
                  <span className="text-[10px] font-mono text-[#66655C] uppercase font-bold">Chronic Conditions</span>
                  <p className="text-black font-semibold">
                    {activePatient.chronic_conditions?.length ? activePatient.chronic_conditions.join(', ') : 'None documented'}
                  </p>
                </div>

                <div className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-1">
                  <span className="text-[10px] font-mono text-[#66655C] uppercase font-bold">Current Medications</span>
                  <p className="text-black font-semibold">
                    {activePatient.current_medications?.length ? activePatient.current_medications.join(', ') : 'None documented'}
                  </p>
                </div>
              </div>

              <div className="pt-4 border-t border-[#E2DFC9] flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setMode('CREATE')}
                    className="bg-white border-2 border-black text-black px-4 py-2 rounded-full font-mono text-xs font-bold uppercase flex items-center gap-1.5 hover:bg-[#FAF8F2]"
                  >
                    <Plus size={14} />
                    <span>New Patient</span>
                  </button>
                  <button
                    onClick={() => setMode('EDIT')}
                    className="bg-white border-2 border-black text-black px-4 py-2 rounded-full font-mono text-xs font-bold uppercase flex items-center gap-1.5 hover:bg-[#FAF8F2]"
                  >
                    <Edit2 size={14} />
                    <span>Edit Profile</span>
                  </button>
                </div>

                <button
                  onClick={handleStartSession}
                  disabled={loading}
                  className="bg-[#2A2B2E] text-white px-6 py-2.5 rounded-full font-mono text-xs font-bold uppercase flex items-center gap-2 hover:bg-black shadow-md"
                >
                  <Play size={14} className="text-[#E19B4C]" />
                  <span>{loading ? 'Initializing Session...' : 'Start Clinical Session'}</span>
                </button>
              </div>
            </div>
          )}

          {(mode === 'CREATE' || mode === 'EDIT') && (
            <form onSubmit={mode === 'CREATE' ? handleCreate : handleUpdate} className="space-y-4 text-xs font-sans">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div>
                  <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1">Patient ID / MRN</label>
                  <input
                    type="text"
                    value={patientId}
                    onChange={(e) => setPatientId(e.target.value)}
                    disabled={mode === 'EDIT'}
                    placeholder="PAT-88291"
                    required
                    className="w-full bg-white border border-[#DCD8BE] rounded-lg px-3 py-2 font-mono font-bold text-black"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1">Age (Years)</label>
                  <input
                    type="number"
                    value={age}
                    onChange={(e) => setAge(Number(e.target.value))}
                    required
                    className="w-full bg-white border border-[#DCD8BE] rounded-lg px-3 py-2 font-bold text-black"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1">Gender</label>
                  <select
                    value={gender}
                    onChange={(e) => setGender(e.target.value)}
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
                    value={bloodType}
                    onChange={(e) => setBloodType(e.target.value)}
                    placeholder="A+"
                    className="w-full bg-white border border-[#DCD8BE] rounded-lg px-3 py-2 font-mono font-bold text-black"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1">Documented Allergies (Comma Separated)</label>
                <input
                  type="text"
                  value={allergies}
                  onChange={(e) => setAllergies(e.target.value)}
                  placeholder="e.g. Penicillin, Sulfa"
                  className="w-full bg-white border border-[#DCD8BE] rounded-lg px-3 py-2 text-black font-semibold"
                />
              </div>

              <div>
                <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1">Chronic Conditions (Comma Separated)</label>
                <input
                  type="text"
                  value={chronicConditions}
                  onChange={(e) => setChronicConditions(e.target.value)}
                  placeholder="e.g. Hypertension, Chronic Kidney Disease"
                  className="w-full bg-white border border-[#DCD8BE] rounded-lg px-3 py-2 text-black font-semibold"
                />
              </div>

              <div>
                <label className="block text-[10px] font-mono uppercase text-[#66655C] mb-1">Current Medications (Comma Separated)</label>
                <input
                  type="text"
                  value={currentMedications}
                  onChange={(e) => setCurrentMedications(e.target.value)}
                  placeholder="e.g. Warfarin 5mg, Metoprolol 25mg"
                  className="w-full bg-white border border-[#DCD8BE] rounded-lg px-3 py-2 text-black font-semibold"
                />
              </div>

              <div className="pt-4 border-t border-[#E2DFC9] flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setMode('VIEW')}
                  className="text-xs font-mono text-[#66655C] underline uppercase"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={loading}
                  className="bg-[#2A2B2E] text-white px-6 py-2.5 rounded-full font-mono text-xs font-bold uppercase hover:bg-black"
                >
                  {loading ? 'Saving Record...' : mode === 'CREATE' ? 'Register Patient' : 'Save Changes'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
