import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { useWorkflow } from '../../context/WorkflowContext';
import { Play, RotateCcw, LogOut, User, AlertCircle } from 'lucide-react';

export const AppHeader: React.FC = () => {
  const { doctor, logout } = useAuth();
  const { session, runWorkflow, runningAgentId, resetDemoSession } = useWorkflow();

  return (
    <header className="w-full bg-[#F5F3EB] px-4 md:px-8 py-5 border-b border-[#E2DFC9] flex flex-col md:flex-row items-center justify-between gap-4">
      {/* Patient Pill */}
      <div className="flex items-center gap-2">
        <div className="bg-[#2A2B2E] text-white font-mono text-xs md:text-sm tracking-wider uppercase font-semibold px-5 py-2 rounded-full shadow-sm flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#E19B4C] animate-pulse"></span>
          <span>{session.patient_id}</span>
        </div>

        {session.status === 'WAITING_FOR_CLINICAL_DATA' && (
          <div className="bg-[#FFF3C4] text-[#8C6D00] border border-[#E6C200] text-xs font-semibold px-3 py-1.5 rounded-full flex items-center gap-1.5 animate-bounce">
            <AlertCircle size={14} />
            <span>Data Needed</span>
          </div>
        )}
      </div>

      {/* Center Editorial Title Block */}
      <div className="text-center">
        <p className="text-[10px] md:text-xs font-mono uppercase tracking-[0.25em] text-[#66655C] font-medium">
          NEURO-SYMBOLIC MULTIMODAL ENGINE
        </p>
        <h1 className="font-serif italic text-2xl md:text-3xl text-[#1A1A1C] font-semibold tracking-tight">
          PulseGraph Clinical Decision Support
        </h1>
      </div>

      {/* Session Pill & Controls */}
      <div className="flex items-center gap-3">
        <div className="bg-[#2A2B2E] text-white font-mono text-xs md:text-sm tracking-wider uppercase font-semibold px-5 py-2 rounded-full shadow-sm">
          <span>{session.session_id}</span>
        </div>

        {/* Action Controls */}
        <button
          onClick={() => runWorkflow()}
          disabled={!!runningAgentId}
          title="Run Multi-Agent Execution Pipeline"
          className={`flex items-center gap-1.5 bg-[#1A1A1C] text-white px-3.5 py-2 rounded-full text-xs font-medium hover:bg-black transition-colors ${
            runningAgentId ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          <Play size={13} className={runningAgentId ? 'animate-spin' : ''} />
          <span className="hidden sm:inline">{runningAgentId ? 'Running...' : 'Run Pipeline'}</span>
        </button>

        <button
          onClick={resetDemoSession}
          title="Reset Demo Session State"
          className="p-2 text-[#4A4943] hover:text-black hover:bg-[#EAE7DA] rounded-full transition-colors"
        >
          <RotateCcw size={16} />
        </button>

        {/* Clinician Profile */}
        {doctor && (
          <div className="flex items-center gap-2 pl-2 border-l border-[#DCD8BE]">
            <div className="w-8 h-8 rounded-full bg-[#E2DFC9] flex items-center justify-center text-[#1A1A1C] font-semibold text-xs border border-[#C7C4AE]">
              <User size={15} />
            </div>
            <div className="hidden lg:block text-left text-xs">
              <p className="font-semibold text-[#1A1A1C] leading-none">{doctor.full_name}</p>
              <p className="text-[10px] text-[#66655C]">{doctor.department}</p>
            </div>
            <button
              onClick={logout}
              title="Sign Out Physician"
              className="p-1.5 text-[#66655C] hover:text-red-700 hover:bg-red-50 rounded-full transition-colors ml-1"
            >
              <LogOut size={15} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
