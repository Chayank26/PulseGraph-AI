import React, { useState } from 'react';
import { useWorkflow } from '../../context/WorkflowContext';
import { CheckCircle2, FileImage, Eye, ZoomIn, ZoomOut, Layers } from 'lucide-react';
import './ImagingPage.css';

export const ImagingPage: React.FC = () => {
  const { session, agentStatuses } = useWorkflow();
  const imaging = session.state.imaging_data || {
    image_path: 'data/mock_patients/patient_001_cxr.png',
    modality: 'CHEST_XRAY_PA',
    findings: [
      { finding_name: 'Pulmonary Infiltrate / Opacity', confidence: 0.88, region: 'Right Lower Lobe', clinical_significance: 'HIGH' as const },
      { finding_name: 'Cardiomegaly', confidence: 0.74, region: 'Cardiac Silhouette', clinical_significance: 'MODERATE' as const },
      { finding_name: 'Pleural Effusion', confidence: 0.32, region: 'Left Costophrenic Angle', clinical_significance: 'LOW' as const }
    ],
    impression: 'Sub-segmental filling defect noted in right lower lobe. Radiographic opacity suspicious for pulmonary embolism or pneumonia. Recommend CT Pulmonary Angiography correlation.'
  };
  const status = agentStatuses.imaging || 'COMPLETED';

  const [contrastMode, setContrastMode] = useState<'normal' | 'high' | 'inverted'>('normal');
  const [showHeatmap, setShowHeatmap] = useState<boolean>(true);
  const [zoomLevel, setZoomLevel] = useState<number>(100);

  const toggleContrast = () => {
    if (contrastMode === 'normal') setContrastMode('high');
    else if (contrastMode === 'high') setContrastMode('inverted');
    else setContrastMode('normal');
  };

  return (
    <div className="imaging-shell animate-fade-in font-sans">
      {/* Header Banner */}
      <div className="imaging-banner">
        <div>
          <div className="imaging-banner-meta">
            AGENT 02 • MODALITY CHEST X-RAY / CT DICOM
          </div>
          <h1 className="imaging-banner-title">
            MULTIMODAL VISION AGENT
          </h1>
          <p className="imaging-banner-subtitle">
            DenseNet-121 / CheXNet deep learning inference engine on chest radiograph DICOM scans.
          </p>
        </div>

        <div className="imaging-banner-badge">
          <CheckCircle2 size={16} className="text-[#C8D2E6]" />
          <span>STATUS: {status}</span>
        </div>
      </div>

      {/* Main Imaging Layout */}
      <div className="imaging-main-grid">
        {/* Left Column: Image DICOM Viewer Canvas */}
        <div className="imaging-viewer-box">
          <div className="flex items-center justify-between">
            <h3 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C]">
              INGESTED RADIOGRAPH SCAN
            </h3>
            <span className="text-xs font-mono font-bold text-black uppercase bg-[#C8D2E6] px-2.5 py-0.5 rounded">
              {imaging.modality}
            </span>
          </div>

          {/* Interactive Viewer Toolbar */}
          <div className="flex items-center justify-between bg-white border border-[#DCD8BE] rounded-xl p-2 text-xs font-mono">
            <div className="flex items-center gap-1.5">
              <button
                onClick={toggleContrast}
                className="px-2.5 py-1 rounded bg-[#2A2B2E] text-white hover:bg-black transition flex items-center gap-1 text-[11px]"
              >
                <Eye size={12} />
                <span>Mode: {contrastMode.toUpperCase()}</span>
              </button>
              <button
                onClick={() => setShowHeatmap(!showHeatmap)}
                className={`px-2.5 py-1 rounded transition flex items-center gap-1 text-[11px] ${
                  showHeatmap ? 'bg-[#E19B4C] text-black font-bold' : 'bg-gray-200 text-gray-700'
                }`}
              >
                <Layers size={12} />
                <span>Heatmap: {showHeatmap ? 'ON' : 'OFF'}</span>
              </button>
            </div>

            <div className="flex items-center gap-1 text-black font-bold">
              <button
                onClick={() => setZoomLevel(Math.max(80, zoomLevel - 10))}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <ZoomOut size={14} />
              </button>
              <span className="w-10 text-center">{zoomLevel}%</span>
              <button
                onClick={() => setZoomLevel(Math.min(150, zoomLevel + 10))}
                className="p-1 hover:bg-gray-100 rounded"
              >
                <ZoomIn size={14} />
              </button>
            </div>
          </div>

          {/* Radiograph DICOM Display Screen */}
          <div
            className={`relative rounded-xl p-8 border-2 border-black flex flex-col items-center justify-center min-h-[340px] text-white space-y-3 overflow-hidden shadow-inner transition-all duration-300 ${
              contrastMode === 'high'
                ? 'bg-black contrast-150'
                : contrastMode === 'inverted'
                ? 'bg-white text-black invert'
                : 'bg-black'
            }`}
            style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'center' }}
          >
            {/* Simulated DenseNet Class Activation Map Overlay */}
            {showHeatmap && (
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-red-600/30 via-amber-500/20 to-transparent pointer-events-none animate-pulse"></div>
            )}

            <FileImage size={64} className="text-[#C8D2E6] relative z-10" />
            <div className="relative z-10 text-center space-y-1 font-mono text-xs">
              <p className="font-bold text-white tracking-widest uppercase">
                {imaging.image_path.split('/').pop() || 'PATIENT_001_CXR.PNG'}
              </p>
              <p className="text-gray-400 text-[10px]">
                DenseNet-121 Feature Map • 14 Pre-Trained Radiographic Conditions
              </p>
            </div>

            <div className="absolute bottom-3 left-3 right-3 bg-white/10 backdrop-blur text-[10px] font-mono px-3 py-1.5 rounded flex justify-between text-gray-300">
              <span>FOV: 35cm x 43cm</span>
              <span>KVP: 120 | MAS: 3.2</span>
            </div>
          </div>
        </div>

        {/* Right Column: CheXNet Vision Model Inference Findings */}
        <div className="imaging-findings-box">
          <div className="bg-[#FAF8F2] border-2 border-black rounded-2xl p-6 space-y-6 shadow-sm">
            <h3 className="font-serif uppercase tracking-widest text-xs font-bold text-[#66655C]">
              CHEXNET VISION INFERENCE FINDINGS ({imaging.findings.length})
            </h3>

            <div className="space-y-4">
              {imaging.findings.map((f, i) => {
                const confPct = Math.round(f.confidence * 100);
                return (
                  <div key={i} className="bg-white border border-[#DCD8BE] rounded-xl p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-bold text-base text-black">{f.finding_name}</h4>
                        <p className="text-xs text-[#66655C] font-mono mt-0.5">Anatomical Region: {f.region || 'Unspecified'}</p>
                      </div>
                      <div className="text-right">
                        <span className="bg-[#2A2B2E] text-white font-mono text-xs font-bold px-3 py-1 rounded-full">
                          {confPct}% CONFIDENCE
                        </span>
                        <p className="text-[10px] font-mono font-bold text-red-800 uppercase mt-1">
                          {f.clinical_significance} SEVERITY
                        </p>
                      </div>
                    </div>

                    {/* Visual Probability Bar */}
                    <div className="w-full bg-[#E2DFC9] h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-black h-full transition-all duration-500"
                        style={{ width: `${confPct}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="pt-4 border-t border-[#E2DFC9]">
              <h4 className="font-serif uppercase tracking-wider text-xs font-bold text-[#66655C] mb-2">
                RADIOLOGY IMPRESSION
              </h4>
              <p className="font-serif italic text-base text-black font-semibold leading-relaxed">
                "{imaging.impression}"
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
