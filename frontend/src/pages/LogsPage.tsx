import React, { useEffect, useState } from 'react';
import { 
  listUploadJobs, 
  retryUploadJob, 
  triggerReconciliation, 
  type UploadJobItem,
  type ReconciliationSummary
} from '../api/uploads';
import {
  auditCopyright,
  deleteAndReplaceOccurrence,
  type CopyrightAuditSummary
} from '../api/youtube';
import { 
  History, 
  RefreshCw, 
  RotateCcw, 
  ShieldAlert, 
  ShieldCheck,
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  ExternalLink,
  Loader2,
  HardDrive,
  Trash2
} from 'lucide-react';

export const LogsPage: React.FC = () => {
  const [jobs, setJobs] = useState<UploadJobItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [reconciling, setReconciling] = useState<boolean>(false);
  const [reconcileResult, setReconcileResult] = useState<ReconciliationSummary | null>(null);
  const [auditingCopyright, setAuditingCopyright] = useState<boolean>(false);
  const [copyrightResult, setCopyrightResult] = useState<CopyrightAuditSummary | null>(null);
  const [actionOccurrenceId, setActionOccurrenceId] = useState<string | null>(null);

  const loadJobs = async () => {
    try {
      setLoading(true);
      const data = await listUploadJobs(statusFilter || undefined);
      setJobs(data);
    } catch {
      // Ignored
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 5000);
    return () => clearInterval(interval);
  }, [statusFilter]);

  const handleManualRetry = async (jobId: string) => {
    try {
      await retryUploadJob(jobId);
      await loadJobs();
    } catch (err: any) {
      alert(err.message || 'Failed to retry upload job');
    }
  };

  const handleReconcile = async () => {
    try {
      setReconciling(true);
      const res = await triggerReconciliation();
      setReconcileResult(res);
      await loadJobs();
    } catch (err: any) {
      alert(err.message || 'Failed to execute crash reconciliation');
    } finally {
      setReconciling(false);
    }
  };

  const handleCopyrightAudit = async () => {
    try {
      setAuditingCopyright(true);
      const res = await auditCopyright(undefined, 20);
      setCopyrightResult(res);
      await loadJobs();
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || 'Failed to run copyright audit');
    } finally {
      setAuditingCopyright(false);
    }
  };

  const handleDeleteAndReplace = async (occurrenceId: string) => {
    if (!window.confirm('Delete this video from YouTube and automatically upload a replacement from its schedule?')) {
      return;
    }
    try {
      setActionOccurrenceId(occurrenceId);
      await deleteAndReplaceOccurrence(occurrenceId, 'Manual User Request', true);
      alert('Video deleted from YouTube and replacement video queued!');
      await loadJobs();
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || 'Failed to delete and replace video');
    } finally {
      setActionOccurrenceId(null);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" /> SUCCESS
          </span>
        );
      case 'COPYRIGHT_DELETED':
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/40">
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" /> COPYRIGHT AUTO-DELETED & REPLACED
          </span>
        );
      case 'IN_PROGRESS':
      case 'DOWNLOADING':
      case 'UPLOADING':
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse">
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> {status}
          </span>
        );
      case 'RETRYING':
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <RotateCcw className="w-3.5 h-3.5 animate-spin" /> RETRYING
          </span>
        );
      case 'FAILED':
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertTriangle className="w-3.5 h-3.5" /> FAILED
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            <Clock className="w-3.5 h-3.5" /> {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <History className="w-6 h-6 text-red-500" />
            Upload Jobs & Copyright Guard
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Real-time tracking of uploads, automated copyright audits, and strike auto-replacement.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={loadJobs}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium border border-slate-700 transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>

          <button
            onClick={handleCopyrightAudit}
            disabled={auditingCopyright}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-red-900/20 transition cursor-pointer"
          >
            <ShieldCheck className={`w-3.5 h-3.5 ${auditingCopyright ? 'animate-spin' : ''}`} />
            {auditingCopyright ? 'Auditing Copyright...' : 'Audit Copyright & Strikes'}
          </button>
          
          <button
            onClick={handleReconcile}
            disabled={reconciling}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-amber-900/20 transition cursor-pointer"
          >
            <ShieldAlert className={`w-3.5 h-3.5 ${reconciling ? 'animate-spin' : ''}`} />
            {reconciling ? 'Reconciling...' : 'Crash Reconciliation'}
          </button>
        </div>
      </div>

      {/* Copyright Audit Summary Alert */}
      {copyrightResult && (
        <div className="p-4 rounded-xl bg-slate-900/90 border border-red-500/40 text-xs text-slate-200 flex items-center justify-between shadow-xl">
          <div className="flex items-center gap-3">
            <ShieldCheck className="w-5 h-5 text-red-400 flex-shrink-0" />
            <div>
              <span className="font-bold text-red-300">Copyright Guard Audit Complete:</span> Scanned{' '}
              <span className="font-semibold text-white">{copyrightResult.total_audited}</span> recent uploads.{' '}
              <span className="font-semibold text-emerald-400">{copyrightResult.clean_count} healthy</span>,{' '}
              <span className="font-semibold text-rose-400">{copyrightResult.flagged_and_replaced} flagged & auto-replaced</span>.
            </div>
          </div>
          <button
            onClick={() => setCopyrightResult(null)}
            className="text-slate-400 hover:text-white font-bold px-2 py-1"
          >
            ✕
          </button>
        </div>
      )}

      {/* Reconciliation Summary Alert */}
      {reconcileResult && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-500/30 text-xs text-amber-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-5 h-5 text-amber-400 flex-shrink-0" />
            <div>
              <span className="font-bold">Reconciliation Complete:</span> Scanned{' '}
              {reconcileResult.total_stuck_found} stuck jobs. Re-queued{' '}
              {reconcileResult.reconciled_to_queue} for retry, cleaned{' '}
              {reconcileResult.cleaned_temp_files} orphaned temp files.
            </div>
          </div>
          <button
            onClick={() => setReconcileResult(null)}
            className="text-amber-400 hover:text-white font-bold px-2 py-1"
          >
            ✕
          </button>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {['', 'IN_PROGRESS', 'RETRYING', 'FAILED', 'SUCCESS', 'QUEUED'].map((f) => (
          <button
            key={f}
            onClick={() => setStatusFilter(f)}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer ${
              statusFilter === f
                ? 'bg-red-600 text-white shadow-md shadow-red-900/30'
                : 'bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            {f === '' ? 'All Jobs' : f}
          </button>
        ))}
      </div>

      {/* Jobs List */}
      <div className="space-y-3">
        {jobs.length === 0 ? (
          <div className="py-16 flex flex-col items-center justify-center text-center bg-slate-900/40 border border-slate-800 rounded-2xl">
            <HardDrive className="w-10 h-10 text-slate-600 mb-3" />
            <h3 className="text-base font-semibold text-slate-300">No Upload Jobs Found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm">
              Trigger a manual upload from the Video Library or create an automated schedule to view execution logs.
            </p>
          </div>
        ) : (
          jobs.map((job) => (
            <div
              key={job.id}
              className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-slate-700/80 transition space-y-3.5"
            >
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div className="flex items-center gap-3">
                  {getStatusBadge(job.status)}
                  <span className="font-mono text-xs text-slate-400">Job: {job.id.slice(0, 8)}...</span>
                  <span className="text-xs text-slate-500">
                    Created: {new Date(job.created_at).toLocaleString()}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {job.youtube_url && (
                    <>
                      <a
                        href={job.youtube_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600/20 hover:bg-red-600 text-red-300 hover:text-white rounded-lg text-xs font-medium border border-red-500/30 transition"
                      >
                        <ExternalLink className="w-3.5 h-3.5" /> Watch on YouTube
                      </a>

                      <button
                        onClick={() => handleDeleteAndReplace(job.occurrence_id)}
                        disabled={actionOccurrenceId === job.occurrence_id}
                        className="flex items-center gap-1 px-3 py-1.5 bg-rose-950 hover:bg-rose-900 text-rose-300 hover:text-white rounded-lg text-xs font-medium border border-rose-800 transition cursor-pointer"
                        title="Delete this video from YouTube and immediately upload next replacement from schedule"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                        {actionOccurrenceId === job.occurrence_id ? 'Deleting...' : 'Delete & Replace'}
                      </button>
                    </>
                  )}

                  {(job.status === 'FAILED' || job.status === 'RETRYING') && (
                    <button
                      onClick={() => handleManualRetry(job.id)}
                      className="flex items-center gap-1 px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-amber-900/20 transition cursor-pointer"
                    >
                      <RotateCcw className="w-3.5 h-3.5" /> Retry Now
                    </button>
                  )}
                </div>
              </div>

              {/* Progress Bar */}
              {(job.status === 'IN_PROGRESS' || job.status === 'DOWNLOADING' || job.status === 'UPLOADING') && (
                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs text-slate-400">
                    <span>Transfer Progress</span>
                    <span className="font-mono font-medium text-slate-200">
                      {job.progress_percentage}% ({formatBytes(job.bytes_uploaded)} / {formatBytes(job.total_bytes)})
                    </span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className="h-full bg-blue-500 transition-all duration-300 rounded-full"
                      style={{ width: `${job.progress_percentage}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Error Message & Details */}
              {job.error_message && (
                <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/30 text-xs text-rose-300 space-y-1">
                  <div className="font-semibold flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                    Error [{job.error_type || 'TRANSIENT'}]:
                  </div>
                  <p className="font-mono text-[11px] text-rose-200/90 break-words">{job.error_message}</p>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
