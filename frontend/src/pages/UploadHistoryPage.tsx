import React from 'react';
import { History } from 'lucide-react';

export const UploadHistoryPage: React.FC = () => {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Upload History</h2>
          <p className="text-sm text-slate-400 mt-1">
            Complete audit record of uploaded videos, YouTube video IDs, and scheduled release times.
          </p>
        </div>
      </div>

      <div className="p-12 text-center border border-dashed border-slate-800 rounded-xl space-y-4 bg-slate-900/40">
        <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mx-auto text-slate-400">
          <History className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h3 className="font-semibold text-slate-200">No Uploads Recorded</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Once automated or manual uploads execute, full YouTube direct links and timestamps will be logged here.
          </p>
        </div>
      </div>
    </div>
  );
};
