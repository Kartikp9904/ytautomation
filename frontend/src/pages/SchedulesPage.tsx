import React, { useState, useEffect } from 'react';
import type { ScheduleItem, ScheduleCreateData } from '../api/schedules';
import {
  getSchedules,
  createSchedule,
  updateSchedule,
  toggleSchedule,
  deleteSchedule,
  triggerScheduleNow,
  resetRotationIndex,
  reshufflePool,
} from '../api/schedules';
import type { Channel } from '../api/channels';
import { getChannels } from '../api/channels';
import type { ContentFolderItem, VideoItem } from '../api/videos';
import { getContentFolders, getVideos } from '../api/videos';
import { ScheduleModal } from '../components/schedules/ScheduleModal';
import { CalendarPreviewModal } from '../components/schedules/CalendarPreviewModal';
import {
  Clock,
  Plus,
  Play,
  RotateCw,
  Shuffle,
  Power,
  Trash2,
  Edit,
  Folder,
  Film,
  Calendar,
  Tv,
  AlertCircle,
  CheckCircle2,
  CalendarDays,
  ShieldAlert,
  CalendarCheck,
  RefreshCw,
  X,
  ExternalLink,
  Copy
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const SchedulesPage: React.FC = () => {
  const [schedules, setSchedules] = useState<ScheduleItem[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [folders, setFolders] = useState<ContentFolderItem[]>([]);
  const [videos, setVideos] = useState<VideoItem[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Filters
  const [selectedChannelId, setSelectedChannelId] = useState<string>('');
  const [selectedType, setSelectedType] = useState<string>('');
  const [selectedMode, setSelectedMode] = useState<string>('');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<ScheduleItem | null>(null);
  const [simulatingSchedule, setSimulatingSchedule] = useState<ScheduleItem | null>(null);

  const [runningScheduleId, setRunningScheduleId] = useState<string | null>(null);
  const [toastNotification, setToastNotification] = useState<{
    title: string;
    message: string;
    type: 'success' | 'error' | 'info';
    link?: { text: string; href: string };
  } | null>(null);

  const loadAllData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [schedData, chData, fData, vData] = await Promise.all([
        getSchedules({
          channel_id: selectedChannelId || undefined,
          schedule_type: selectedType || undefined,
          mode: selectedMode || undefined,
        }),
        getChannels(),
        getContentFolders(),
        getVideos({ limit: 100 }),
      ]);
      setSchedules(schedData);
      setChannels(chData.items);
      setFolders(fData);
      setVideos(vData.items);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load scheduling data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, [selectedChannelId, selectedType, selectedMode]);

  const showSuccess = (msg: string) => {
    setSuccessMessage(msg);
    setTimeout(() => setSuccessMessage(null), 4000);
  };

  const handleToggle = async (id: string) => {
    try {
      const updated = await toggleSchedule(id);
      setSchedules(schedules.map((s) => (s.id === id ? updated : s)));
      showSuccess(`Schedule "${updated.name}" is now ${updated.enabled ? 'Enabled' : 'Paused'}.`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to toggle schedule');
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to delete schedule "${name}"?`)) return;
    try {
      await deleteSchedule(id);
      setSchedules(schedules.filter((s) => s.id !== id));
      showSuccess(`Schedule "${name}" deleted.`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete schedule');
    }
  };

  const handleRunNow = async (id: string, name: string) => {
    try {
      setRunningScheduleId(id);
      setError(null);
      const res = await triggerScheduleNow(id);
      setToastNotification({
        title: '🚀 Video Upload Started!',
        message: `Schedule "${name}" was triggered. The background worker is downloading your video from Google Drive and uploading directly to YouTube.`,
        type: 'success',
        link: { text: 'View Upload Logs & Live Status ➔', href: '/logs' }
      });
      showSuccess(`Triggered schedule "${name}" immediately! (Occurrence: ${res.occurrence_id})`);
      loadAllData();
    } catch (err: any) {
      const errDetail = err.response?.data?.detail || 'Failed to trigger schedule execution';
      setError(errDetail);
      setToastNotification({
        title: 'Upload Trigger Failed',
        message: errDetail,
        type: 'error'
      });
    } finally {
      setRunningScheduleId(null);
    }
  };

  const handleResetRotation = async (id: string, name: string) => {
    try {
      setError(null);
      await resetRotationIndex(id, 0);
      showSuccess(`Reset rotation queue for "${name}" back to the first video.`);
      loadAllData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reset rotation index');
    }
  };

  const handleReshuffle = async (id: string, name: string) => {
    try {
      setError(null);
      const res = await reshufflePool(id);
      showSuccess(`Reshuffled pool for "${name}"! (Cycle ${res.current_cycle}, ${res.total_shuffled} videos ready)`);
      loadAllData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reshuffle queue');
    }
  };

  const handleDuplicateSchedule = (sched: ScheduleItem) => {
    setEditingSchedule({
      ...sched,
      id: '',
      name: `${sched.name} (Copy)`,
    });
    setIsModalOpen(true);
  };

  const handleSaveSchedule = async (data: ScheduleCreateData) => {
    if (editingSchedule && editingSchedule.id) {
      await updateSchedule(editingSchedule.id, data);
      showSuccess(`Schedule "${data.name}" updated successfully.`);
    } else {
      await createSchedule(data);
      showSuccess(`New schedule "${data.name}" created successfully.`);
    }
    loadAllData();
  };

  const formatNextRun = (dateStr: string | null) => {
    if (!dateStr) return 'Not scheduled';
    try {
      const d = new Date(dateStr);
      return d.toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Automation Schedules</h2>
          <p className="text-sm text-slate-400 mt-1">
            Automate multi-frequency publishing across channels with Day-of-Month, Rotation, Repeat, and Shuffle modes.
          </p>
        </div>
        <button
          onClick={() => {
            setEditingSchedule(null);
            setIsModalOpen(true);
          }}
          className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-red-900/20 transition cursor-pointer self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          Create Schedule
        </button>
      </div>

      {/* Alerts */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-sm flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Filter Bar */}
      <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 grid grid-cols-1 sm:grid-cols-3 gap-3 backdrop-blur">
        <div>
          <select
            value={selectedChannelId}
            onChange={(e) => setSelectedChannelId(e.target.value)}
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition"
          >
            <option value="">All Channels</option>
            {channels.map((ch) => (
              <option key={ch.id} value={ch.id}>
                {ch.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition"
          >
            <option value="">All Frequencies (Daily, Weekly...)</option>
            <option value="DAILY">Daily</option>
            <option value="WEEKLY">Weekly</option>
            <option value="MONTHLY">Monthly</option>
            <option value="ONE_TIME">One-Time</option>
          </select>
        </div>

        <div>
          <select
            value={selectedMode}
            onChange={(e) => setSelectedMode(e.target.value)}
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition"
          >
            <option value="">All Modes (Day-of-Month, Rotation...)</option>
            <option value="DAY_OF_MONTH">Day-of-Month</option>
            <option value="ROTATION">Sequential Rotation</option>
            <option value="REPEAT">Repeat Mode</option>
            <option value="SHUFFLE">Shuffle Mode</option>
            <option value="SINGLE_VIDEO">Single Video</option>
          </select>
        </div>
      </div>

      {/* Schedules List */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center space-y-3">
          <div className="w-8 h-8 border-3 border-red-500/20 border-t-red-500 rounded-full animate-spin"></div>
          <span className="text-xs text-slate-400">Loading schedules...</span>
        </div>
      ) : schedules.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {schedules.map((sched) => (
            <div
              key={sched.id}
              className={`p-5 rounded-2xl border transition-all flex flex-col justify-between backdrop-blur space-y-4 ${
                sched.enabled
                  ? 'bg-slate-900/80 border-slate-800 hover:border-slate-700 shadow-lg shadow-black/20'
                  : 'bg-slate-900/40 border-slate-800/60 opacity-60'
              }`}
            >
              <div className="space-y-3">
                {/* Card Header */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="p-2.5 rounded-xl bg-red-600/15 text-red-400 border border-red-500/20 shrink-0">
                      <Clock className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-bold text-white text-sm truncate" title={sched.name}>
                        {sched.name}
                      </h3>
                      <div className="flex items-center gap-1.5 text-xs text-slate-400 mt-0.5">
                        <Tv className="w-3.5 h-3.5 text-red-400 shrink-0" />
                        <span className="font-medium text-slate-300">{sched.channel_name}</span>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleToggle(sched.id)}
                    title={sched.enabled ? 'Pause Schedule' : 'Resume Schedule'}
                    className={`p-2 rounded-xl border transition cursor-pointer ${
                      sched.enabled
                        ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                        : 'bg-slate-800 text-slate-500 border-slate-700'
                    }`}
                  >
                    <Power className="w-4 h-4" />
                  </button>
                </div>

                {/* Timing & Mode Badges */}
                <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                  <span className="px-2 py-0.5 rounded font-bold bg-blue-500/15 text-blue-300 border border-blue-500/30 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {sched.publish_time} ({sched.timezone})
                  </span>
                  <span className="px-2 py-0.5 rounded font-semibold bg-purple-500/15 text-purple-300 border border-purple-500/30">
                    {sched.schedule_type}
                  </span>
                  <span className="px-2 py-0.5 rounded font-mono bg-amber-500/15 text-amber-300 border border-amber-500/30">
                    {sched.mode}
                  </span>

                  {sched.upload_lead_minutes !== undefined && sched.upload_lead_minutes > 0 && (
                    <span className="px-2 py-0.5 rounded font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                      <CalendarCheck className="w-3 h-3" /> {sched.upload_lead_minutes}m lead
                    </span>
                  )}

                  {sched.dry_run && (
                    <span className="px-2 py-0.5 rounded font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                      <ShieldAlert className="w-3 h-3" /> Dry Run
                    </span>
                  )}

                  {sched.mode === 'ROTATION' && sched.total_rotation_videos !== undefined && (
                    <span className="px-2 py-0.5 rounded font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                      Next: #{(sched.current_rotation_index || 0) + 1} of {sched.total_rotation_videos}
                    </span>
                  )}

                  {sched.mode === 'SHUFFLE' && sched.shuffle_cycle !== undefined && (
                    <span className="px-2 py-0.5 rounded font-medium bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                      Cycle {sched.shuffle_cycle} • {sched.shuffle_remaining_count} Remaining
                    </span>
                  )}
                </div>

                {/* Source & Next Run Details */}
                <div className="space-y-1.5 text-xs bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="flex items-center gap-1.5">
                      {sched.source_type === 'FOLDER' ? <Folder className="w-3.5 h-3.5 text-amber-400" /> : <Film className="w-3.5 h-3.5 text-blue-400" />}
                      Source:
                    </span>
                    <span className="font-semibold text-slate-200 truncate max-w-[200px]">
                      {sched.source_name}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-slate-400 pt-1 border-t border-slate-800/60">
                    <span className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-emerald-400" />
                      Next Execution:
                    </span>
                    <span className="font-mono text-emerald-400 font-semibold">
                      {formatNextRun(sched.next_run_time)}
                    </span>
                  </div>
                </div>

                {/* Title & Description Template Preview */}
                {(sched.title_template || sched.description_template) && (
                  <div className="p-3 bg-slate-950/90 rounded-xl border border-slate-800 space-y-1.5 text-xs">
                    {sched.title_template && (
                      <div className="space-y-0.5">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Custom Title:</span>
                        <p className="font-semibold text-slate-200 truncate">{sched.title_template}</p>
                      </div>
                    )}
                    {sched.description_template && (
                      <div className="space-y-0.5 pt-1 border-t border-slate-800/60">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Description Template:</span>
                        <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed whitespace-pre-line">{sched.description_template}</p>
                      </div>
                    )}
                    {sched.tags && sched.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 pt-1">
                        {sched.tags.slice(0, 4).map((t, idx) => (
                          <span key={idx} className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-400">
                            #{t}
                          </span>
                        ))}
                        {sched.tags.length > 4 && (
                          <span className="text-[10px] text-slate-500 self-center">+{sched.tags.length - 4} more</span>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Card Actions Footer */}
              <div className="border-t border-slate-800/80 pt-3 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleRunNow(sched.id, sched.name)}
                    disabled={runningScheduleId === sched.id}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600 text-emerald-300 hover:text-white rounded-lg text-xs font-semibold border border-emerald-500/30 hover:border-emerald-500 transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {runningScheduleId === sched.id ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                        <span>Starting...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5" />
                        <span>Run Now</span>
                      </>
                    )}
                  </button>

                  {sched.mode === 'DAY_OF_MONTH' && (
                    <button
                      onClick={() => setSimulatingSchedule(sched)}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium border border-slate-700 transition cursor-pointer"
                      title="Simulate Month Day-Mapping"
                    >
                      <CalendarDays className="w-3.5 h-3.5 text-purple-400" /> Simulate Month
                    </button>
                  )}

                  {sched.mode === 'ROTATION' && (
                    <button
                      onClick={() => handleResetRotation(sched.id, sched.name)}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium border border-slate-700 transition cursor-pointer"
                      title="Reset Rotation to First Video"
                    >
                      <RotateCw className="w-3.5 h-3.5 text-emerald-400" /> Reset Queue
                    </button>
                  )}

                  {sched.mode === 'SHUFFLE' && (
                    <button
                      onClick={() => handleReshuffle(sched.id, sched.name)}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium border border-slate-700 transition cursor-pointer"
                      title="Reshuffle Video Queue"
                    >
                      <Shuffle className="w-3.5 h-3.5 text-cyan-400" /> Reshuffle
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => handleDuplicateSchedule(sched)}
                    className="p-1.5 text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10 rounded-lg transition cursor-pointer border border-transparent hover:border-cyan-500/20"
                    title="Duplicate Schedule"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => {
                      setEditingSchedule(sched);
                      setIsModalOpen(true);
                    }}
                    className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition cursor-pointer border border-transparent hover:border-slate-700"
                    title="Edit Schedule"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(sched.id, sched.name)}
                    className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition cursor-pointer border border-transparent hover:border-rose-500/20"
                    title="Delete Schedule"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Empty State */
        <div className="p-12 text-center border border-dashed border-slate-800 rounded-2xl space-y-4 bg-slate-900/40">
          <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mx-auto text-slate-400">
            <Clock className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="font-semibold text-slate-200">No Automation Schedules Configured</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Click "+ Create Schedule" to configure daily, weekly, or monthly publishing rules.
            </p>
          </div>
          <button
            onClick={() => {
              setEditingSchedule(null);
              setIsModalOpen(true);
            }}
            className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-semibold transition cursor-pointer"
          >
            Create First Schedule
          </button>
        </div>
      )}

      {/* Schedule Create / Edit Modal */}
      <ScheduleModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSaveSchedule}
        schedule={editingSchedule}
        channels={channels}
        folders={folders}
        videos={videos}
      />

      {/* Calendar Month Simulation Modal */}
      <CalendarPreviewModal
        isOpen={!!simulatingSchedule}
        onClose={() => setSimulatingSchedule(null)}
        schedule={simulatingSchedule}
      />

      {/* Floating Toast Notification */}
      {toastNotification && (
        <div className="fixed bottom-6 right-6 z-50 max-w-md w-full px-4 sm:px-0 animate-in fade-in slide-in-from-bottom-5 duration-300">
          <div
            className={`p-4 rounded-2xl border shadow-2xl backdrop-blur-xl flex items-start gap-3.5 ${
              toastNotification.type === 'success'
                ? 'bg-slate-900/95 border-emerald-500/40 text-slate-100 shadow-emerald-950/40'
                : 'bg-slate-900/95 border-rose-500/40 text-slate-100 shadow-rose-950/40'
            }`}
          >
            <div
              className={`p-2 rounded-xl shrink-0 ${
                toastNotification.type === 'success'
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'bg-rose-500/20 text-rose-400'
              }`}
            >
              {toastNotification.type === 'success' ? (
                <CheckCircle2 className="w-5 h-5" />
              ) : (
                <AlertCircle className="w-5 h-5" />
              )}
            </div>
            <div className="flex-1 min-w-0 space-y-1">
              <h4 className="font-bold text-sm text-white">{toastNotification.title}</h4>
              <p className="text-xs text-slate-300 leading-relaxed">{toastNotification.message}</p>
              {toastNotification.link && (
                <div className="pt-1.5">
                  <Link
                    to={toastNotification.link.href}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-400 hover:text-emerald-300 underline underline-offset-4 transition"
                  >
                    <span>{toastNotification.link.text}</span>
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              )}
            </div>
            <button
              onClick={() => setToastNotification(null)}
              className="p-1 text-slate-400 hover:text-white rounded-lg transition cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
