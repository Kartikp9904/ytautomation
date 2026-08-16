import React, { useEffect, useState } from 'react';
import { getWorkerPoolStatus, pauseWorkerQueue, resumeWorkerQueue, type WorkerPoolStatus } from '../../api/uploads';
import { 
  Activity, 
  Pause, 
  Play, 
  Cpu, 
  Layers, 
  Zap, 
  RefreshCw,
  Clock
} from 'lucide-react';

export const WorkerPoolWidget: React.FC = () => {
  const [status, setStatus] = useState<WorkerPoolStatus | null>(null);
  const [loading, setLoading] = useState(false);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const data = await getWorkerPoolStatus();
      setStatus(data);
    } catch {
      // Ignored
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleTogglePause = async () => {
    if (!status) return;
    try {
      if (status.is_paused) {
        await resumeWorkerQueue();
      } else {
        await pauseWorkerQueue();
      }
      await loadStatus();
    } catch (err: any) {
      alert(err.message || 'Failed to toggle queue state');
    }
  };

  if (!status) return null;

  return (
    <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4 backdrop-blur shadow-lg shadow-black/20">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-red-600/20 text-red-400 border border-red-500/30">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-bold text-white text-sm">Upload Worker Pool & Concurrency</h3>
            <p className="text-[11px] text-slate-400">
              Multi-channel rate limiting and asynchronous worker slots
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadStatus}
            title="Refresh Worker Status"
            className="p-1.5 text-slate-400 hover:text-white bg-slate-800 rounded-lg transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          
          <button
            onClick={handleTogglePause}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
              status.is_paused
                ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                : 'bg-amber-600/20 hover:bg-amber-600 text-amber-300 hover:text-white border border-amber-500/30'
            }`}
          >
            {status.is_paused ? (
              <>
                <Play className="w-3 h-3" /> Resume Queue
              </>
            ) : (
              <>
                <Pause className="w-3 h-3" /> Pause Queue
              </>
            )}
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
          <span className="text-slate-400 flex items-center gap-1 text-[11px]">
            <Cpu className="w-3 h-3 text-blue-400" /> Active Uploads
          </span>
          <div className="text-base font-bold text-white font-mono">
            {status.active_uploads_count} / {status.max_concurrent_uploads}
          </div>
          <span className="text-[10px] text-slate-500">Worker Slots</span>
        </div>

        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
          <span className="text-slate-400 flex items-center gap-1 text-[11px]">
            <Layers className="w-3 h-3 text-purple-400" /> Channel Concurrency
          </span>
          <div className="text-base font-bold text-white font-mono">
            {status.per_channel_max_concurrent} max
          </div>
          <span className="text-[10px] text-slate-500">Per YouTube Account</span>
        </div>

        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
          <span className="text-slate-400 flex items-center gap-1 text-[11px]">
            <Clock className="w-3 h-3 text-amber-400" /> Channel Cooldown
          </span>
          <div className="text-base font-bold text-white font-mono">
            {status.channel_cooldown_seconds}s
          </div>
          <span className="text-[10px] text-slate-500">Anti-Burst Delay</span>
        </div>

        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
          <span className="text-slate-400 flex items-center gap-1 text-[11px]">
            <Zap className="w-3 h-3 text-emerald-400" /> Queue Status
          </span>
          <div className={`text-base font-bold uppercase font-mono ${status.is_paused ? 'text-amber-400' : 'text-emerald-400'}`}>
            {status.is_paused ? 'PAUSED' : 'ONLINE'}
          </div>
          <span className="text-[10px] text-slate-500">Worker Pool</span>
        </div>
      </div>
    </div>
  );
};
