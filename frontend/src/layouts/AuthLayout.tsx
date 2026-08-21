import React from 'react';
import { Outlet, Link } from 'react-router-dom';

export const AuthLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#F5F3EB] flex flex-col justify-between p-6 md:p-12 font-sans selection:bg-[#E19B4C] selection:text-black">
      {/* Top Brand Header */}
      <header className="flex items-center justify-between w-full max-w-6xl mx-auto">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-full bg-[#1A1A1C] text-white flex items-center justify-center font-bold text-sm shadow-md group-hover:bg-[#E19B4C] group-hover:text-black transition-colors">
            PG
          </div>
          <div>
            <h1 className="font-serif italic text-xl font-bold tracking-tight text-[#1A1A1C]">PulseGraph</h1>
            <p className="text-[10px] font-mono uppercase tracking-widest text-[#66655C]">Neuro-Symbolic CDS</p>
          </div>
        </Link>

        <Link
          to="/"
          className="text-xs font-semibold text-[#66655C] hover:text-black uppercase tracking-wider transition-colors"
        >
          ← Return to Overview
        </Link>
      </header>

      {/* Main Form Box */}
      <main className="w-full max-w-md mx-auto my-12 bg-[#FAF8F2] border-2 border-black rounded-2xl p-8 shadow-2xl">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="text-center text-xs text-[#8C8A7B] max-w-6xl mx-auto font-mono">
        PulseGraph AI © 2026 — Multimodal Clinical Decision Support System. Clinician Review Required.
      </footer>
    </div>
  );
};
