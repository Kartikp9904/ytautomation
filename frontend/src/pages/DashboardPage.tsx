import React, { useEffect, useState } from 'react';
import { fetchHealth, type SystemHealth } from '../api/client';
import { getChannels } from '../api/channels';
import { getTodayTimeline, type TimelineItem } from '../api/schedules';
import { listUploadJobs } from '../api/uploads';
import { WorkerPoolWidget } from '../components/dashboard/WorkerPoolWidget';
import { 
  Tv, 
  CalendarDays, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  ArrowUpRight, 
  Plus, 
  ExternalLink 
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [channelsCount, setChannelsCount] = useState<number>(0);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [completedCount, setCompletedCount] = useState<number>(0);
  const [failedCount, setFailedCount] = useState<number>(0);

  const loadData = async () => {
    fetchHealth().then(setHealth).catch(() => {});
    getChannels().then((data) => setChannelsCount(data.total)).catch(() => {});
    getTodayTimeline().then(setTimeline).catch(() => {});
    listUploadJobs().then((jobs) => {
      const completed = jobs.filter((j) => j.status === 'SUCCESS').length;
      const failed = jobs.filter((j) => j.status === 'FAILED' || j.status === 'RETRYING').length;
      setCompletedCount(completed);
      setFailedCount(failed);
    }).catch(() => {});
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
      case 'SUCCESS':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">COMPLETED</span>;
      case 'IN_PROGRESS':
      case 'DOWNLOADING':
      case 'UPLOADING':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30 animate-pulse">UPLOADING</span>;
      case 'RETRYING':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">RETRYING</span>;
      case 'FAILED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">FAILED</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700">QUEUED</span>;
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Automation Overview</h2>
          <p className="text-sm text-slate-400 mt-1">
            Real-time status of connected YouTube channels, automated upload queues, and scheduler state.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/channels"
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm font-medium border border-slate-700 transition cursor-pointer"
          >
            <Tv className="w-4 h-4" />
            Manage Channels
          </Link>
          <Link
            to="/schedules"
            className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-sm font-medium shadow-lg shadow-red-900/20 transition cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            New Schedule
          </Link>
        </div>
      </div>

      {/* Worker Pool & Concurrency Widget */}
      <WorkerPoolWidget />

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800/80 backdrop-blur space-y-3">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Active Channels</span>
            <Tv className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white">{channelsCount}</div>
          <p className="text-xs text-slate-500">Configured YouTube accounts</p>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800/80 backdrop-blur space-y-3">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Today's Scheduled</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white">{timeline.length}</div>
          <p className="text-xs text-slate-500">Uploads targeted for today</p>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800/80 backdrop-blur space-y-3">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Completed Uploads</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white">{completedCount}</div>
          <p className="text-xs text-slate-500">Successfully published videos</p>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800/80 backdrop-blur space-y-3">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Failed / Retrying</span>
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-white">{failedCount}</div>
          <p className="text-xs text-slate-500">
            {failedCount > 0 ? (
              <Link to="/logs" className="text-rose-400 underline">View issues in logs</Link>
            ) : (
              'All pipelines healthy'
            )}
          </p>
        </div>
      </div>

      {/* System Status Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Today's Queue */}
        <div className="lg:col-span-2 p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-white text-base">Today's Scheduled Timeline</h3>
            <Link to="/calendar" className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1 font-medium">
              View Calendar <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {timeline.length === 0 ? (
            <div className="py-12 flex flex-col items-center justify-center text-center space-y-3 border border-dashed border-slate-800 rounded-lg">
              <CalendarDays className="w-8 h-8 text-slate-600" />
              <div className="text-sm font-medium text-slate-300">No scheduled uploads today</div>
              <p className="text-xs text-slate-500 max-w-sm">
                Connect a YouTube channel and set up your daily, weekly, or day-of-month schedules to get started.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {timeline.map((item) => (
                <div
                  key={item.id}
                  className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between gap-3 text-xs"
                >
                  <div className="flex items-center gap-3">
                    {getStatusBadge(item.status)}
                    <div>
                      <div className="font-semibold text-white truncate max-w-md">{item.video_title}</div>
                      <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
                        <span>{item.channel_name}</span>
                        <span>•</span>
                        <span className="font-mono text-slate-500">
                          Target: {new Date(item.scheduled_publish_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                        {item.dry_run && (
                          <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-amber-500/20 text-amber-300">
                            Dry Run
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {item.youtube_url && (
                    <a
                      href={item.youtube_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 bg-red-600/20 hover:bg-red-600 text-red-300 hover:text-white rounded-lg transition"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Infrastructure & Storage Health */}
        <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
          <h3 className="font-semibold text-white text-base">Storage & Infrastructure</h3>
          <div className="space-y-3.5 text-xs">
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
              <span className="text-slate-400">Database Engine</span>
              <span className="font-mono text-emerald-400 font-medium">{health?.database || 'SQLite (WAL)'}</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
              <span className="text-slate-400">Primary Storage</span>
              <span className="font-semibold text-emerald-400">{health?.storage.provider || 'Google Drive (Cloud)'}</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
              <span className="text-slate-400">Upload Temp Buffer</span>
              <span className="font-mono text-slate-200 font-medium">
                {health?.storage.free_space_gb !== null && health?.storage.free_space_gb !== undefined
                  ? `${health.storage.free_space_gb} GB Free`
                  : 'Checking...'}
              </span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
              <span className="text-slate-400">Execution Mode</span>
              <span className="font-mono text-blue-400 font-medium">{health?.environment || 'development'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
