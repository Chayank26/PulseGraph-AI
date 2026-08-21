import React from 'react';
import { Outlet } from 'react-router-dom';
import { AppHeader } from '../components/common/AppHeader';
import { WorkflowTopBanner } from '../components/common/WorkflowTopBanner';
import { WorkflowProgress } from '../components/common/WorkflowProgress';
import { ReviewActionBar } from '../components/common/ReviewActionBar';
import { DataRequestModal } from '../components/common/DataRequestModal';

export const AppLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#F5F3EB] flex flex-col font-sans selection:bg-[#E19B4C] selection:text-black">
      {/* Agent Stage Header Navigation (Matching attached reference image!) */}
      <WorkflowTopBanner />

      {/* Primary Patient & Session Header */}
      <AppHeader />

      {/* Multi-Agent Sequential Workflow Progress Bar */}
      <WorkflowProgress compact={true} />

      {/* Main Clinical Viewport */}
      <main className="flex-1 w-full max-w-[1600px] mx-auto px-4 md:px-8 py-6">
        <Outlet />
      </main>

      {/* Floating HITL Review Action Bar & Override Alert */}
      <ReviewActionBar />

      {/* Blocking Data Acquisition Prompt Modal if graph requests missing data */}
      <DataRequestModal />
    </div>
  );
};
