import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { agentsList } from '../../data/mockClinicalSession';
import { useWorkflow } from '../../context/WorkflowContext';

export const WorkflowTopBanner: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { agentStatuses, runningAgentId } = useWorkflow();

  return (
    <div className="w-full grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 border-b-2 border-black bg-[#FAF8F2] select-none">
      {agentsList.map((agent) => {
        const isActiveRoute = location.pathname === agent.route;
        const isRunning = runningAgentId === agent.id;
        const status = agentStatuses[agent.id] || 'IDLE';

        return (
          <div
            key={agent.id}
            onClick={() => navigate(agent.route)}
            style={{ backgroundColor: agent.color }}
            className={`relative p-3 md:p-4 cursor-pointer transition-all duration-200 border-r border-b md:border-b-0 border-black/20 hover:brightness-95 group ${
              isActiveRoute ? 'ring-2 ring-inset ring-black shadow-inner' : ''
            }`}
          >
            {/* Top Agent Metadata Line */}
            <div className="flex items-center justify-between text-[10px] sm:text-xs font-sans tracking-wide uppercase text-black/70 font-semibold mb-1">
              <span>AGENT {agent.number}</span>
              <span className="truncate max-w-[120px] font-normal italic font-serif">
                {agent.tagline}
              </span>
            </div>

            {/* Agent Stage Name - Giant Bold Editorial Sans */}
            <div className="flex items-baseline justify-between">
              <h2 className="text-xl sm:text-2xl md:text-3xl font-extrabold tracking-tight uppercase text-black font-sans leading-none">
                {agent.name}
              </h2>

              {/* Status Indicator Dot */}
              <div className="flex items-center gap-1.5 ml-2">
                {isRunning ? (
                  <span className="flex h-2.5 w-2.5 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-black opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-black"></span>
                  </span>
                ) : status === 'COMPLETED' ? (
                  <span className="w-2 h-2 rounded-full bg-black/60"></span>
                ) : (
                  <span className="w-2 h-2 rounded-full border border-black/40"></span>
                )}
              </div>
            </div>

            {/* Active Running Pulse Line */}
            {isRunning && (
              <div className="absolute bottom-0 left-0 right-0 h-1 bg-black animate-pulse" />
            )}

            {/* Selected Route Active Indicator Bar */}
            {isActiveRoute && (
              <div className="absolute top-0 left-0 right-0 h-1.5 bg-black" />
            )}
          </div>
        );
      })}
    </div>
  );
};
