import React from 'react';
import { AlertOctagon } from 'lucide-react';

export const FailedJobsPage: React.FC = () => {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Failed Jobs & Retries</h2>
          <p className="text-sm text-slate-400 mt-1">
            Review upload failures, backoff timers, and manual retry options.
          </p>
        </div>
      </div>

      <div className="p-12 text-center border border-dashed border-slate-800 rounded-xl space-y-4 bg-slate-900/40">
        <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mx-auto text-emerald-400">
          <AlertOctagon className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h3 className="font-semibold text-slate-200">Zero Failed Jobs</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            All systems nominal. Any upload errors or interrupted jobs will be surfaced here for easy recovery.
          </p>
        </div>
      </div>
    </div>
  );
};
