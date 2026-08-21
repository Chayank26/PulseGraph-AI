import React, { useState } from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { HelpCircle, Send, FileText } from 'lucide-react';

export const DataRequestModal: React.FC = () => {
  const { session, resolveDataRequest } = useWorkflow();
  const pendingRequests = session.state.pending_data_requests || [];
  const activeRequest = pendingRequests[0];

  const [formData, setFormData] = useState<Record<string, any>>({});
  const [submitting, setSubmitting] = useState(false);

  if (!activeRequest) return null;

  const handleInputChange = (key: string, value: any) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await resolveDataRequest(activeRequest.request_id, formData);
    } finally {
      setSubmitting(false);
      setFormData({});
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-[#FAF8F2] border-2 border-black rounded-2xl max-w-xl w-full p-6 md:p-8 shadow-2xl animate-fade-in">
        {/* Header Badge */}
        <div className="flex items-center justify-between mb-4">
          <div className="bg-[#E19B4C] text-black text-xs font-mono font-bold uppercase tracking-wider px-3 py-1 rounded-full flex items-center gap-1.5">
            <HelpCircle size={14} />
            <span>CLINICAL DATA REQUIRED — {activeRequest.requesting_agent.toUpperCase()} AGENT</span>
          </div>
          <span className="text-[11px] font-mono text-[#66655C]">{activeRequest.request_id}</span>
        </div>

        <h3 className="font-serif italic text-2xl font-bold text-[#1A1A1C] mb-2">
          {activeRequest.pathway_name}
        </h3>
        <p className="text-xs text-[#4A4943] leading-relaxed mb-6 font-sans">
          {activeRequest.reason}
        </p>

        {/* Dynamic Form Fields */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {activeRequest.required_fields.map((field) => (
            <div key={field.field_key} className="bg-white border border-[#DCD8BE] rounded-xl p-4">
              <label className="block text-xs font-bold text-[#1A1A1C] uppercase tracking-wide mb-1">
                {field.label} {field.required && <span className="text-red-700">*</span>}
              </label>
              {field.description && (
                <p className="text-[11px] text-[#66655C] mb-2">{field.description}</p>
              )}

              {field.data_type === 'enum' && field.options ? (
                <select
                  value={formData[field.field_key] || ''}
                  onChange={(e) => handleInputChange(field.field_key, Number(e.target.value))}
                  required={field.required}
                  className="w-full bg-[#FAF8F2] border border-[#DCD8BE] rounded-lg p-2.5 text-xs text-black focus:outline-none focus:ring-2 focus:ring-black"
                >
                  <option value="">Select clinical score parameter...</option>
                  {field.options.map((opt, i) => (
                    <option key={i} value={i}>
                      {opt}
                    </option>
                  ))}
                </select>
              ) : field.data_type === 'file' ? (
                <div className="flex items-center gap-2">
                  <FileText size={16} className="text-[#66655C]" />
                  <input
                    type="text"
                    value={formData[field.field_key] || 'data/mock_patients/patient_001_cxr.png'}
                    onChange={(e) => handleInputChange(field.field_key, e.target.value)}
                    required={field.required}
                    className="w-full bg-[#FAF8F2] border border-[#DCD8BE] rounded-lg p-2.5 text-xs font-mono text-black focus:outline-none focus:ring-2 focus:ring-black"
                  />
                </div>
              ) : (
                <input
                  type="number"
                  step="any"
                  value={formData[field.field_key] ?? ''}
                  onChange={(e) => handleInputChange(field.field_key, Number(e.target.value))}
                  required={field.required}
                  placeholder={`Enter ${field.label}...`}
                  className="w-full bg-[#FAF8F2] border border-[#DCD8BE] rounded-lg p-2.5 text-xs text-black focus:outline-none focus:ring-2 focus:ring-black"
                />
              )}
            </div>
          ))}

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-[#2A2B2E] hover:bg-black text-white font-sans font-bold text-xs uppercase tracking-wider py-3.5 rounded-full transition-all flex items-center justify-center gap-2 shadow-lg mt-6"
          >
            <Send size={14} />
            <span>{submitting ? 'Submitting & Resuming Agent Workflow...' : 'Submit Clinical Parameters & Resume Graph'}</span>
          </button>
        </form>
      </div>
    </div>
  );
};
