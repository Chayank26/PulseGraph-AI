import React from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { CheckCircle2, FileImage } from 'lucide-react';
import './ImagingPage.css';

export const ImagingPage: React.FC = () => {
  const { session, agentStatuses } = useWorkflow();
  const imaging = session.state.imaging_data;
  const status = agentStatuses.imaging || 'COMPLETED';

  return (
    <div className="imaging-shell animate-fade-in">
      {/* Header Banner */}
      <div className="imaging-banner">
        <div>
          <div className="imaging-banner-meta">
            AGENT 02 • MODALITY CHEST X-RAY / CT
          </div>
          <h1 className="imaging-banner-title">
            MULTIMODAL VISION AGENT
          </h1>
          <p className="imaging-banner-subtitle">
            Performs DenseNet-121 / CheXNet diagnostic inference on chest radiography DICOM scans.
          </p>
        </div>

        <div className="imaging-banner-badge">
          <CheckCircle2 size={16} className="text-[#C8D2E6]" />
          <span>STATUS: {status}</span>
        </div>
      </div>

      {/* Main Imaging Layout */}
      <div className="imaging-main-grid">
        {/* Left Column: Image DICOM Viewer Placeholder */}
        <div className="imaging-viewer-box">
          <div className="flex items-center justify-between">
            <h3 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C]">
              INGESTED RADIOGRAPH SCAN
            </h3>
            <span className="text-xs font-mono font-bold text-black uppercase bg-[#C8D2E6] px-2.5 py-0.5 rounded">
              {imaging?.modality || 'CHEST_XRAY_PA'}
            </span>
          </div>

          {/* Radiograph Mock Display */}
          <div className="relative bg-black rounded-xl p-8 border-2 border-black flex flex-col items-center justify-center min-h-[320px] text-white space-y-3 overflow-hidden shadow-inner">
            <div className="absolute inset-0 bg-gradient-to-tr from-gray-900 via-gray-800 to-gray-950 opacity-90"></div>
            {/* Simulated radiograph grid overlay */}
            <div className="absolute inset-0 bg-[radial-gradient(#4a5568_1px,transparent_1px)] [background-size:16px_16px] opacity-30"></div>
            
            <FileImage size={56} className="text-[#C8D2E6] relative z-10 animate-pulse" />
            <div className="relative z-10 text-center space-y-1 font-mono text-xs">
              <p className="font-bold text-white tracking-widest">PATIENT_001_CXR.PNG</p>
              <p className="text-gray-400 text-[10px]">DenseNet-121 Feature Activation Map Applied</p>
            </div>

            <div className="absolute bottom-3 left-3 right-3 bg-white/10 backdrop-blur text-[10px] font-mono px-3 py-1.5 rounded flex justify-between text-gray-300">
              <span>FOV: 35cm x 43cm</span>
              <span>KVP: 120 | MAS: 3.2</span>
            </div>
          </div>
        </div>

        {/* Right Column: Model Inference Findings */}
        <div className="imaging-findings-box">
          <div className="bg-[#FAF8F2] border-2 border-black rounded-2xl p-6 space-y-6 shadow-sm">
            <h3 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C]">
              CHEXNET VISION INFERENCE FINDINGS
            </h3>

            <div className="space-y-4">
              {imaging?.findings.map((f, i) => (
                <div key={i} className="bg-white border border-[#DCD8BE] rounded-xl p-4 flex items-center justify-between">
                  <div>
                    <h4 className="font-bold text-sm text-black">{f.finding_name}</h4>
                    <p className="text-xs text-[#66655C] font-mono mt-0.5">Location: {f.region || 'Unspecified'}</p>
                  </div>
                  <div className="text-right">
                    <span className="bg-[#2A2B2E] text-white font-mono text-xs font-bold px-3 py-1 rounded-full">
                      {(f.confidence * 100).toFixed(0)}% Confidence
                    </span>
                    <p className="text-[10px] font-mono font-bold text-red-800 uppercase mt-1">
                      {f.clinical_significance} SEVERITY
                    </p>
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-4 border-t border-[#E2DFC9]">
              <h4 className="font-serif uppercase tracking-wider text-xs font-bold text-[#66655C] mb-2">
                RADIOLOGY IMPRESSION
              </h4>
              <p className="font-serif italic text-base text-black font-semibold leading-relaxed">
                "{imaging?.impression}"
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
