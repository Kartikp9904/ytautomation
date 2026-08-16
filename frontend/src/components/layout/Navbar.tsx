import React, { useEffect, useState } from 'react';
import { fetchHealth, type SystemHealth } from '../../api/client';
import { Database, Clock, HardDrive, RefreshCw } from 'lucide-react';

export const Navbar: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(false);

  const checkHealth = async () => {
    try {
      setLoading(true);
      const data = await fetchHealth();
      setHealth(data);
    } catch {
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 bg-slate-900/60 backdrop-blur border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-10">
      {/* Title / Breadcrumbs */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-400 font-medium">Environment:</span>
        <span className="px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-300 font-mono border border-slate-700">
          {health?.environment || 'development'}
        </span>
      </div>

      {/* System Status Badges */}
      <div className="flex items-center gap-3 text-xs">
        {/* Database Status */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60">
          <Database className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400">DB:</span>
          <span className={health?.database === 'HEALTHY' ? 'text-emerald-400 font-semibold' : 'text-amber-400'}>
            {health?.database || 'CONNECTING'}
          </span>
        </div>

        {/* Scheduler Status */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400">Scheduler:</span>
          <span className="text-blue-400 font-medium">{health?.scheduler || 'READY'}</span>
        </div>

        {/* Storage Provider & Disk Space */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700/60">
          <HardDrive className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400">Storage:</span>
          <span className="text-slate-200 capitalize font-medium">{health?.storage.provider || 'local'}</span>
          {health?.storage.free_space_gb !== null && health?.storage.free_space_gb !== undefined && (
            <span className="text-slate-500 font-mono text-[11px]">({health.storage.free_space_gb} GB free)</span>
          )}
        </div>

        {/* Refresh Button */}
        <button
          onClick={checkHealth}
          disabled={loading}
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-md transition-colors border border-transparent hover:border-slate-700 cursor-pointer"
          title="Refresh System Health"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>
    </header>
  );
};
