import React, { useState } from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { UrgencyBanner } from './UrgencyBanner';
import { HelpCircle, Send, FileText } from 'lucide-react';

const DataRequestForm: React.FC = () => {
  const { session, resolveDataRequest } = useWorkflow();
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [submitting, setSubmitting] = useState(false);

  const [error, setError] = useState('');
  const activeRequest = session?.state.pending_data_requests?.[0];
  if (!activeRequest) return null;

  const handleInputChange = (key: string, value: any) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const response = activeRequest.requesting_agent === 'diagnostic' && formData.diagnostic_followup_action === 'proceed_to_review' ? { diagnostic_followup_action: 'proceed_to_review' } : formData;
      await resolveDataRequest(activeRequest.request_id, response);
      setFormData({});
    } catch {
      setError('Unable to save these answers. Check the values and try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-[#FAF8F2] border-2 border-black rounded-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto p-6 md:p-8 shadow-2xl animate-fade-in">
        {/* Header Badge */}
        <div className="flex items-center justify-between mb-4">
          <div className="bg-[#E19B4C] text-black text-xs font-mono font-bold uppercase tracking-wider px-3 py-1 rounded-full flex items-center gap-1.5">
            <HelpCircle size={14} />
            <span>{activeRequest.requesting_agent === 'diagnostic' ? 'OPTIONAL CLARIFICATION' : 'CLINICAL DATA REQUIRED'} — {activeRequest.requesting_agent.toUpperCase()} AGENT</span>
          </div>
          <span className="text-[11px] font-mono text-[#66655C]">{activeRequest.request_id}</span>
        </div>

        <h3 className="font-serif italic text-2xl font-bold text-[#1A1A1C] mb-2">
          {activeRequest.pathway_name}
        </h3>
        <p className="text-xs text-[#4A4943] leading-relaxed mb-6 font-sans">
          {activeRequest.reason}
        </p>

        <UrgencyBanner />
        {activeRequest.requesting_agent === 'imaging' && (
          <section className="bg-white border rounded-lg p-3 mb-4 text-sm">
            <p><strong>Complaint:</strong> {session?.state.demographics?.chief_complaint || 'Not recorded'}</p>
            <p><strong>Allergies:</strong> {session?.state.demographics?.allergies?.join(', ') || 'No entries recorded; confirm history'}</p>
            {session?.state.presentation?.sources.map(source => <p key={source.source_id}>{source.text}</p>)}
          </section>
        )}
        {/* Dynamic Form Fields */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {[...activeRequest.required_fields, ...(activeRequest.optional_fields || [])].map((field) => (
            <div key={field.field_key} className="bg-white border border-[#DCD8BE] rounded-xl p-4">
              <label className="block text-xs font-bold text-[#1A1A1C] uppercase tracking-wide mb-1">
                {field.label} {field.required && <span className="text-red-700">*</span>}
              </label>
              {field.description && (
                <p className="text-[11px] text-[#66655C] mb-2">{field.description}</p>
              )}

              {activeRequest.requesting_agent === 'diagnostic' && field.allow_unavailable ? (
                <select aria-label={`${field.label} availability`} value={['__unknown__', '__unavailable__'].includes(formData[field.field_key]) ? formData[field.field_key] : ''}
                  onChange={event => handleInputChange(field.field_key, event.target.value || undefined)}>
                  <option value="">Enter a value</option><option value="__unknown__">Unknown</option><option value="__unavailable__">Unavailable</option>
                </select>
              ) : field.allow_unavailable && (
                <label className="block text-xs mb-2">
                  <input type="checkbox" checked={formData[field.field_key] === '__unavailable__'}
                    onChange={event => handleInputChange(field.field_key, event.target.checked ? '__unavailable__' : undefined)} />
                  {' '}Unknown / unavailable — request clinician assessment
                </label>
              )}
              {['__unknown__', '__unavailable__'].includes(formData[field.field_key]) ? (
                <p className="text-xs">This information will remain unavailable; dependent assessment cannot be completed.</p>
              ) : field.data_type === 'enum' && field.options ? (
                <select
                  value={formData[field.field_key] ?? ''}
                  onChange={(e) => handleInputChange(field.field_key, e.target.value)}
                  required={field.required}
                  className="w-full bg-[#FAF8F2] border border-[#DCD8BE] rounded-lg p-2.5 text-xs text-black focus:outline-none focus:ring-2 focus:ring-black"
                >
                  <option value="">Select an option...</option>
                  {field.options.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt.replace(/_/g, ' ')}
                    </option>
                  ))}
                </select>
              ) : field.data_type === 'bool' ? (
                <select
                  value={formData[field.field_key] === undefined ? '' : String(formData[field.field_key])}
                  onChange={(e) => handleInputChange(field.field_key, e.target.value === '' ? undefined : e.target.value === 'true')}
                  required={field.required}
                  className="w-full bg-[#FAF8F2] border border-[#DCD8BE] rounded-lg p-2.5 text-xs text-black"
                >
                  <option value="">Select an answer...</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              ) : field.data_type === 'str' ? (
                <textarea rows={field.field_key.includes('report') ? 5 : 2}
                  value={formData[field.field_key] ?? ''}
                  onChange={e => handleInputChange(field.field_key, e.target.value)}
                  required={field.required}
                  className="w-full border rounded-lg p-2.5 text-sm text-black"
                  placeholder={field.label} />
              ) : field.data_type === 'file' ? (
                <div className="flex items-center gap-2">
                  <FileText size={16} className="text-[#66655C]" />
                  <input
                    type="text"
                    value={formData[field.field_key] ?? ''}
                    onChange={(e) => handleInputChange(field.field_key, e.target.value)}
                    required={field.required}
                    placeholder="Enter DICOM image filepath or dataset URL..."
                    className="w-full bg-[#FAF8F2] border border-[#DCD8BE] rounded-lg p-2.5 text-xs font-mono text-black focus:outline-none focus:ring-2 focus:ring-black"
                  />
                </div>
              ) : (
                <input
                  type="number"
                  step="any"
                  value={formData[field.field_key] ?? ''}
                  onChange={(e) => handleInputChange(field.field_key, e.target.value === '' ? '' : Number(e.target.value))}
                  required={field.required}
                  placeholder={`Enter ${field.label}...`}
                  className="w-full bg-[#FAF8F2] border border-[#DCD8BE] rounded-lg p-2.5 text-xs text-black focus:outline-none focus:ring-2 focus:ring-black"
                />
              )}
            </div>
          ))}

          {error && <p role="alert" className="text-xs text-red-700">{error}</p>}
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

export const DataRequestModal: React.FC = () => {
  const { session } = useWorkflow();
  const request = session?.state.pending_data_requests?.[0];
  return request ? <DataRequestForm key={request.request_id} /> : null;
};
