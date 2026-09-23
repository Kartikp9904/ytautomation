import React, { useState, useEffect } from 'react';
import type { SourceChannelSync, SourceChannelSyncInput, SyncedSourceVideo } from '../api/channelSync';
import { 
  getSyncConfigs, 
  createSyncConfig, 
  updateSyncConfig, 
  deleteSyncConfig, 
  triggerChannelSync, 
  getSyncedVideos,
  uploadSingleSyncedVideo 
} from '../api/channelSync';
import type { Channel } from '../api/channels';
import { getChannels } from '../api/channels';
import { 
  Radio, 
  Plus, 
  RefreshCw, 
  Trash2, 
  Play, 
  ExternalLink, 
  CheckCircle2, 
  AlertCircle, 
  ArrowRight, 
  Download, 
  Upload, 
  Sparkles, 
  Layers, 
  Tv, 
  X,
  Sliders
} from 'lucide-react';

const Youtube: React.FC<{ className?: string }> = ({ className = "w-5 h-5" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
  </svg>
);

export const ChannelSyncPage: React.FC = () => {
  const [configs, setConfigs] = useState<SourceChannelSync[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [syncedVideos, setSyncedVideos] = useState<SyncedSourceVideo[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [uploadingVideoId, setUploadingVideoId] = useState<string | null>(null);
  const [selectedSyncId, setSelectedSyncId] = useState<string | null>(null);
  
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingConfig, setEditingConfig] = useState<SourceChannelSync | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modal Form State
  const [sourceUrl, setSourceUrl] = useState<string>('');
  const [targetChannelId, setTargetChannelId] = useState<string>('');
  const [syncMode, setSyncMode] = useState<string>('ALL');
  const [privacyStatus, setPrivacyStatus] = useState<string>('public');
  const [publishMode, setPublishMode] = useState<string>('SCHEDULED');
  const [dailyPublishCount, setDailyPublishCount] = useState<number>(3);
  const [publishTimeSlotsInput, setPublishTimeSlotsInput] = useState<string>('10:00, 15:00, 20:00');
  const [timezone, setTimezone] = useState<string>(Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
  const [maxVideoSizeMb, setMaxVideoSizeMb] = useState<number>(300);
  const [titlePrefix, setTitlePrefix] = useState<string>('');
  const [titleSuffix, setTitleSuffix] = useState<string>('');
  const [descriptionFooter, setDescriptionFooter] = useState<string>('');
  const [customTagsInput, setCustomTagsInput] = useState<string>('');
  const [maxDownloadCount, setMaxDownloadCount] = useState<number>(5);

  const updateDailySlotsPreset = (count: number) => {
    setDailyPublishCount(count);
    if (count === 1) setPublishTimeSlotsInput('12:00');
    else if (count === 2) setPublishTimeSlotsInput('10:00, 18:00');
    else if (count === 3) setPublishTimeSlotsInput('10:00, 15:00, 20:00');
    else if (count === 4) setPublishTimeSlotsInput('09:00, 13:00, 17:00, 21:00');
    else if (count === 5) setPublishTimeSlotsInput('08:00, 11:00, 14:00, 17:00, 20:00');
  };

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [configsData, channelsData, videosData] = await Promise.all([
        getSyncConfigs(),
        getChannels(),
        getSyncedVideos(selectedSyncId || undefined),
      ]);
      setConfigs(configsData);
      setChannels(channelsData.items);
      setSyncedVideos(videosData);
      if (channelsData.items.length > 0 && !targetChannelId) {
        setTargetChannelId(channelsData.items[0].id);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load channel sync data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedSyncId]);

  const handleOpenAdd = () => {
    setEditingConfig(null);
    setSourceUrl('');
    setSyncMode('ALL');
    setPrivacyStatus('public');
    setPublishMode('SCHEDULED');
    setDailyPublishCount(3);
    setPublishTimeSlotsInput('10:00, 15:00, 20:00');
    setTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
    setMaxVideoSizeMb(300);
    setTitlePrefix('');
    setTitleSuffix('');
    setDescriptionFooter('Original creator: Voice Gaming. Full credit to original creator!');
    setCustomTagsInput('gaming, shorts, funny, gameplay');
    if (channels.length > 0) setTargetChannelId(channels[0].id);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (cfg: SourceChannelSync) => {
    setEditingConfig(cfg);
    setSourceUrl(cfg.source_channel_url);
    setTargetChannelId(cfg.target_channel_id);
    setSyncMode(cfg.sync_mode);
    setPrivacyStatus(cfg.publish_privacy_status);
    setPublishMode(cfg.publish_mode || (cfg.auto_publish ? 'IMMEDIATE' : 'SCHEDULED'));
    setDailyPublishCount(cfg.daily_publish_count || 3);
    setPublishTimeSlotsInput(
      cfg.publish_time_slots && cfg.publish_time_slots.length > 0
        ? cfg.publish_time_slots.join(', ')
        : '10:00, 15:00, 20:00'
    );
    setTimezone(cfg.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC');
    setMaxVideoSizeMb(cfg.max_video_size_mb || 300);
    setTitlePrefix(cfg.title_prefix || '');
    setTitleSuffix(cfg.title_suffix || '');
    setDescriptionFooter(cfg.description_footer || '');
    setCustomTagsInput(cfg.custom_tags?.join(', ') || '');
    setIsModalOpen(true);
  };

  const handleSubmitModal = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const tags = customTagsInput
        .split(',')
        .map((t) => t.trim())
        .filter((t) => t.length > 0);

      const timeSlots = publishTimeSlotsInput
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0);

      const payload: SourceChannelSyncInput = {
        source_channel_url: sourceUrl,
        target_channel_id: targetChannelId,
        sync_mode: syncMode,
        auto_publish: publishMode === 'IMMEDIATE',
        publish_privacy_status: privacyStatus,
        publish_mode: publishMode,
        daily_publish_count: dailyPublishCount,
        publish_time_slots: timeSlots.length > 0 ? timeSlots : ['10:00', '15:00', '20:00'],
        timezone: timezone || 'UTC',
        max_video_size_mb: Number(maxVideoSizeMb) || 300,
        title_prefix: titlePrefix || undefined,
        title_suffix: titleSuffix || undefined,
        description_footer: descriptionFooter || undefined,
        custom_tags: tags,
        enabled: true,
      };

      if (editingConfig) {
        await updateSyncConfig(editingConfig.id, payload);
        setSuccessMsg('Sync monitor updated successfully!');
      } else {
        await createSyncConfig(payload);
        setSuccessMsg('New channel sync monitor added!');
      }
      setIsModalOpen(false);
      await loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to save sync monitor.');
    }
  };

  const handleDelete = async (id: string, name?: string) => {
    if (window.confirm(`Delete sync monitor for "${name || 'Channel'}"?`)) {
      try {
        await deleteSyncConfig(id);
        setSuccessMsg('Sync monitor deleted.');
        await loadData();
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to delete monitor.');
      }
    }
  };

  const handleTriggerSync = async (cfg: SourceChannelSync) => {
    try {
      setSyncingId(cfg.id);
      setError(null);
      const result = await triggerChannelSync(cfg.id, maxDownloadCount);
      setSuccessMsg(result.message);
      await loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Sync failed.');
    } finally {
      setSyncingId(null);
    }
  };

  const handleUploadSingleVideo = async (videoId: string) => {
    try {
      setUploadingVideoId(videoId);
      setError(null);
      const uploaded = await uploadSingleSyncedVideo(videoId);
      setSuccessMsg(`Video "${uploaded.title}" uploaded to YouTube: ${uploaded.uploaded_youtube_url}`);
      await loadData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to upload video.');
    } finally {
      setUploadingVideoId(null);
    }
  };

  const totalSynced = configs.reduce((acc, c) => acc + (c.videos_synced_count || 0), 0);
  const totalUploaded = configs.reduce((acc, c) => acc + (c.videos_uploaded_count || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-red-600/20 to-amber-500/20 text-red-400 border border-red-500/30 shadow-lg shadow-red-950/30">
              <Radio className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h1 className="text-2xl font-black text-white tracking-tight">Channel Auto-Sync & Mirroring</h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Monitor external creators (e.g. Voice Gaming), auto-download new videos with metadata, and publish to your channels.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={loading}
            className="p-2.5 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 rounded-xl transition cursor-pointer"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleOpenAdd}
            className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white rounded-xl text-xs font-bold transition shadow-lg shadow-red-900/30 cursor-pointer"
          >
            <Plus className="w-4 h-4" /> Add Source Channel
          </button>
        </div>
      </div>

      {/* Stats Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur flex items-center gap-3.5">
          <div className="p-3 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Youtube className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">Monitored Channels</div>
            <div className="text-xl font-black text-white">{configs.length}</div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur flex items-center gap-3.5">
          <div className="p-3 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Download className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">Total Videos Synced</div>
            <div className="text-xl font-black text-white">{totalSynced}</div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur flex items-center gap-3.5">
          <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Upload className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[11px] text-slate-400 font-medium">Auto-Uploaded to YouTube</div>
            <div className="text-xl font-black text-white">{totalUploaded}</div>
          </div>
        </div>
      </div>

      {/* Alert Messages */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Active Monitors Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <Layers className="w-4 h-4 text-red-500" /> Configured Channel Sync Pipelines
          </h2>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span>Batch download per sync:</span>
            <select
              value={maxDownloadCount}
              onChange={(e) => setMaxDownloadCount(Number(e.target.value))}
              className="px-2 py-1 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
            >
              <option value={1}>1 video</option>
              <option value={3}>3 videos</option>
              <option value={5}>5 videos</option>
              <option value={10}>10 videos</option>
            </select>
          </div>
        </div>

        {configs.length === 0 ? (
          <div className="p-12 text-center border border-dashed border-slate-800 rounded-2xl bg-slate-900/30 space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto text-slate-400">
              <Radio className="w-6 h-6 text-red-400" />
            </div>
            <h3 className="font-bold text-white text-sm">No Source Channels Added Yet</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Add external creators like <strong>@VoiceGaming</strong> to auto-extract their videos, metadata, and upload to your channels automatically.
            </p>
            <button
              onClick={handleOpenAdd}
              className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-xl text-xs font-bold transition shadow-lg shadow-red-900/20 cursor-pointer"
            >
              + Add First Source Channel
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {configs.map((cfg) => {
              const isSyncing = syncingId === cfg.id;
              return (
                <div
                  key={cfg.id}
                  className={`p-5 rounded-2xl border transition-all flex flex-col justify-between backdrop-blur ${
                    selectedSyncId === cfg.id
                      ? 'bg-slate-900 border-red-500/50 shadow-lg shadow-red-950/20'
                      : 'bg-slate-900/70 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="space-y-3.5">
                    {/* Top row */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className="p-2.5 rounded-xl bg-red-600/10 text-red-400 border border-red-500/20">
                          <Youtube className="w-5 h-5" />
                        </div>
                        <div>
                          <h3 className="font-bold text-white text-sm flex items-center gap-2">
                            {cfg.source_channel_name || 'YouTube Source Channel'}
                            {cfg.publish_mode === 'SCHEDULED' ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-blue-500/15 text-blue-300 border border-blue-500/30 flex items-center gap-1">
                                📅 {cfg.daily_publish_count || 3}/day ({cfg.publish_time_slots?.join(', ') || '10:00, 15:00, 20:00'})
                              </span>
                            ) : (cfg.publish_mode === 'IMMEDIATE' || cfg.auto_publish) ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                                ⚡ Immediate
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                                ✋ Manual
                              </span>
                            )}
                          </h3>
                          <a
                            href={cfg.source_channel_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-[11px] text-slate-400 hover:text-red-400 flex items-center gap-1 font-mono truncate max-w-xs transition"
                          >
                            {cfg.source_channel_url} <ExternalLink className="w-3 h-3 shrink-0" />
                          </a>
                        </div>
                      </div>

                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleOpenEdit(cfg)}
                          className="p-1.5 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-lg transition cursor-pointer"
                          title="Edit Settings"
                        >
                          <Sliders className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(cfg.id, cfg.source_channel_name)}
                          className="p-1.5 hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 rounded-lg transition cursor-pointer"
                          title="Delete Monitor"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Mapping Route */}
                    <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 flex items-center justify-between text-xs">
                      <div className="space-y-0.5">
                        <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Source Mode</span>
                        <div className="font-semibold text-slate-300">
                          {cfg.sync_mode === 'SHORTS_ONLY' ? '⚡ Shorts Only (≤60s)' : cfg.sync_mode === 'FULL_VIDEOS_ONLY' ? '🎬 Full Videos' : '🌐 All Videos & Shorts'}
                        </div>
                      </div>

                      <ArrowRight className="w-4 h-4 text-slate-600" />

                      <div className="space-y-0.5 text-right">
                        <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Target Channel</span>
                        <div className="font-semibold text-emerald-400 flex items-center gap-1.5 justify-end">
                          <Tv className="w-3.5 h-3.5" />
                          {cfg.target_channel_name || 'Connected Channel'}
                        </div>
                      </div>
                    </div>

                    {/* Meta options badges */}
                    <div className="flex flex-wrap gap-1.5 text-[10px] font-mono">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/60">
                        Privacy: {cfg.publish_privacy_status}
                      </span>
                      {cfg.title_prefix && (
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700/60">
                          Prefix: "{cfg.title_prefix}"
                        </span>
                      )}
                      {cfg.title_suffix && (
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700/60">
                          Suffix: "{cfg.title_suffix}"
                        </span>
                      )}
                    </div>

                    {cfg.last_error && (
                      <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-[11px] text-rose-300">
                        ⚠️ {cfg.last_error}
                      </div>
                    )}
                  </div>

                  {/* Bottom Action Footer */}
                  <div className="pt-4 mt-4 border-t border-slate-800/80 flex items-center justify-between gap-3">
                    <div className="text-[11px] text-slate-400">
                      Synced: <strong className="text-white">{cfg.videos_synced_count || 0}</strong> | Uploaded: <strong className="text-emerald-400">{cfg.videos_uploaded_count || 0}</strong>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSelectedSyncId(selectedSyncId === cfg.id ? null : cfg.id)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition cursor-pointer ${
                          selectedSyncId === cfg.id
                            ? 'bg-red-500/20 text-red-300 border-red-500/40'
                            : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
                        }`}
                      >
                        {selectedSyncId === cfg.id ? 'Viewing Videos' : 'View Videos'}
                      </button>

                      <button
                        onClick={() => handleTriggerSync(cfg)}
                        disabled={isSyncing}
                        className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white shadow-lg shadow-red-950/40 transition cursor-pointer disabled:opacity-50"
                      >
                        {isSyncing ? (
                          <>
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Ingesting...
                          </>
                        ) : (
                          <>
                            <Play className="w-3.5 h-3.5" /> Sync & Ingest
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Synced Videos Table */}
      <div className="space-y-4 pt-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <Youtube className="w-4 h-4 text-red-500" /> Synced Videos Queue & History
            {selectedSyncId && (
              <span className="text-xs text-red-400 font-mono font-normal">
                (Filtered by selected channel monitor)
              </span>
            )}
          </h2>
          {selectedSyncId && (
            <button
              onClick={() => setSelectedSyncId(null)}
              className="text-xs text-slate-400 hover:text-white underline cursor-pointer"
            >
              Clear Filter
            </button>
          )}
        </div>

        {syncedVideos.length === 0 ? (
          <div className="p-8 text-center border border-slate-800 rounded-2xl bg-slate-900/20 text-xs text-slate-400">
            No videos synced yet. Click <strong>"Sync & Ingest"</strong> on any monitored channel above to pull videos!
          </div>
        ) : (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 text-slate-400 font-mono text-[11px] border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Video / Thumbnail</th>
                    <th className="px-4 py-3">Source Title</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Download Status</th>
                    <th className="px-4 py-3">Upload Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {syncedVideos.map((v) => {
                    const isUploading = uploadingVideoId === v.id;
                    return (
                      <tr key={v.id} className="hover:bg-slate-800/30 transition">
                        <td className="px-4 py-3">
                          <div className="relative w-20 h-12 rounded-lg overflow-hidden bg-slate-950 border border-slate-800 shrink-0">
                            {v.thumbnail_url ? (
                              <img src={v.thumbnail_url} alt={v.title} className="w-full h-full object-cover" />
                            ) : (
                              <div className="w-full h-full flex items-center justify-center text-slate-600">
                                <Youtube className="w-5 h-5" />
                              </div>
                            )}
                            {v.is_short && (
                              <span className="absolute bottom-1 right-1 px-1 py-0.2 rounded text-[9px] font-bold bg-red-600 text-white font-mono">
                                SHORT
                              </span>
                            )}
                          </div>
                        </td>

                        <td className="px-4 py-3 max-w-xs">
                          <a
                            href={v.source_url}
                            target="_blank"
                            rel="noreferrer"
                            className="font-bold text-white hover:text-red-400 line-clamp-2 transition flex items-center gap-1"
                          >
                            {v.title} <ExternalLink className="w-3 h-3 shrink-0 opacity-60" />
                          </a>
                          {v.tags && v.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {v.tags.slice(0, 3).map((t, idx) => (
                                <span key={idx} className="text-[10px] text-slate-500 font-mono">
                                  #{t}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>

                        <td className="px-4 py-3 font-mono">
                          {v.is_short ? (
                            <span className="px-2 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20 text-[10px]">
                              Shorts
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20 text-[10px]">
                              Video ({v.duration_seconds ? `${Math.round(v.duration_seconds)}s` : 'Full'})
                            </span>
                          )}
                        </td>

                        <td className="px-4 py-3 font-mono">
                          {v.download_status === 'DOWNLOADED' ? (
                            <span className="text-emerald-400 font-bold flex items-center gap-1">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Ready
                            </span>
                          ) : v.download_status === 'DOWNLOADING' ? (
                            <span className="text-cyan-400 flex items-center gap-1">
                              <RefreshCw className="w-3.5 h-3.5 animate-spin" /> In Progress
                            </span>
                          ) : (
                            <span className="text-rose-400 flex items-center gap-1">
                              <AlertCircle className="w-3.5 h-3.5" /> {v.download_status}
                            </span>
                          )}
                        </td>

                        <td className="px-4 py-3 font-mono">
                          {v.upload_status === 'UPLOADED' ? (
                            <a
                              href={v.uploaded_youtube_url || `https://youtu.be/${v.uploaded_youtube_video_id}`}
                              target="_blank"
                              rel="noreferrer"
                              className="text-emerald-400 font-bold hover:underline flex items-center gap-1"
                            >
                              <CheckCircle2 className="w-3.5 h-3.5" /> Published <ExternalLink className="w-3 h-3" />
                            </a>
                          ) : v.upload_status === 'UPLOADING' ? (
                            <span className="text-cyan-400 flex items-center gap-1">
                              <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Uploading...
                            </span>
                          ) : v.upload_status === 'SKIPPED' ? (
                            <span className="text-slate-500">Skipped by filter</span>
                          ) : (
                            <span className="text-amber-400">Pending Upload</span>
                          )}
                        </td>

                        <td className="px-4 py-3 text-right">
                          {v.upload_status !== 'UPLOADED' && (
                            <button
                              onClick={() => handleUploadSingleVideo(v.id)}
                              disabled={isUploading}
                              className="px-3 py-1 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-bold transition cursor-pointer shadow disabled:opacity-50 inline-flex items-center gap-1"
                            >
                              {isUploading ? (
                                <>
                                  <RefreshCw className="w-3 h-3 animate-spin" /> Uploading
                                </>
                              ) : (
                                <>
                                  <Upload className="w-3 h-3" /> Upload to Channel
                                </>
                              )}
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Add / Edit Monitor Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <h3 className="font-bold text-white text-base flex items-center gap-2">
                <Youtube className="w-5 h-5 text-red-500" />
                {editingConfig ? 'Edit Source Channel Monitor' : 'Add Source YouTube Channel to Mirror'}
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmitModal} className="space-y-4 text-xs">
              <div>
                <label className="block font-medium text-slate-300 mb-1">
                  Source Channel URL or Handle *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. @VoiceGaming or https://www.youtube.com/@VoiceGaming"
                  value={sourceUrl}
                  onChange={(e) => setSourceUrl(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:border-red-500 font-mono"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Accepts channel handles (@VoiceGaming), full URLs, or channel IDs.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block font-medium text-slate-300 mb-1">Target Channel *</label>
                  <select
                    value={targetChannelId}
                    onChange={(e) => setTargetChannelId(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-red-500 font-medium"
                    required
                  >
                    {channels.map((ch) => (
                      <option key={ch.id} value={ch.id}>
                        {ch.name} ({ch.timezone})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-medium text-slate-300 mb-1">Sync Content Type</label>
                  <select
                    value={syncMode}
                    onChange={(e) => setSyncMode(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 focus:outline-none focus:border-red-500 font-medium"
                  >
                    <option value="ALL">All Videos & Shorts</option>
                    <option value="SHORTS_ONLY">Shorts Only (≤60s)</option>
                    <option value="FULL_VIDEOS_ONLY">Full-Length Videos Only</option>
                  </select>
                </div>
              </div>

              {/* Publishing & Drip Strategy */}
              <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-4">
                <div>
                  <label className="block font-bold text-white mb-2">Publishing Strategy</label>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => setPublishMode('SCHEDULED')}
                      className={`p-3 rounded-xl border text-left transition cursor-pointer ${
                        publishMode === 'SCHEDULED'
                          ? 'bg-blue-600/15 border-blue-500 text-white shadow-sm'
                          : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <div className="font-bold text-xs flex items-center gap-1.5">
                        <span>📅</span> Daily Drip
                      </div>
                      <p className="text-[10px] text-slate-400 mt-1 leading-relaxed">
                        Publish 1–5 videos/day spaced across specific time slots.
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => setPublishMode('IMMEDIATE')}
                      className={`p-3 rounded-xl border text-left transition cursor-pointer ${
                        publishMode === 'IMMEDIATE'
                          ? 'bg-emerald-600/15 border-emerald-500 text-white shadow-sm'
                          : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <div className="font-bold text-xs flex items-center gap-1.5">
                        <span>⚡</span> Immediate
                      </div>
                      <p className="text-[10px] text-slate-400 mt-1 leading-relaxed">
                        Upload immediately as soon as a new video is discovered.
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => setPublishMode('MANUAL')}
                      className={`p-3 rounded-xl border text-left transition cursor-pointer ${
                        publishMode === 'MANUAL'
                          ? 'bg-amber-600/15 border-amber-500 text-white shadow-sm'
                          : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <div className="font-bold text-xs flex items-center gap-1.5">
                        <span>✋</span> Manual
                      </div>
                      <p className="text-[10px] text-slate-400 mt-1 leading-relaxed">
                        Stage metadata in library; you click upload manually.
                      </p>
                    </button>
                  </div>
                </div>

                {publishMode === 'SCHEDULED' && (
                  <div className="space-y-3 pt-2 border-t border-slate-800/80">
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <label className="font-medium text-slate-300">Videos Per Day</label>
                        <span className="text-blue-400 font-bold font-mono text-xs">{dailyPublishCount} / day</span>
                      </div>
                      <div className="flex gap-2">
                        {[1, 2, 3, 4, 5].map((count) => (
                          <button
                            key={count}
                            type="button"
                            onClick={() => updateDailySlotsPreset(count)}
                            className={`flex-1 py-1.5 rounded-lg border text-xs font-bold transition cursor-pointer ${
                              dailyPublishCount === count
                                ? 'bg-blue-600 border-blue-500 text-white'
                                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
                            }`}
                          >
                            {count}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="block font-medium text-slate-300 mb-1">
                        Daily Time Slots (24h format, comma-separated)
                      </label>
                      <input
                        type="text"
                        value={publishTimeSlotsInput}
                        onChange={(e) => setPublishTimeSlotsInput(e.target.value)}
                        placeholder="e.g. 10:00, 15:00, 20:00"
                        className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-200 font-mono text-xs focus:outline-none focus:border-blue-500"
                      />
                      <p className="text-[10px] text-slate-500 mt-1">
                        Videos will automatically publish at these exact times every day.
                      </p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block font-medium text-slate-300 mb-1">Schedule Timezone</label>
                        <input
                          type="text"
                          value={timezone}
                          onChange={(e) => setTimezone(e.target.value)}
                          placeholder="e.g. Asia/Kolkata or UTC"
                          className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-200 font-mono text-xs focus:outline-none focus:border-blue-500"
                        />
                      </div>

                      <div>
                        <label className="block font-medium text-slate-300 mb-1">Max Video Size Guard (MB)</label>
                        <input
                          type="number"
                          value={maxVideoSizeMb}
                          onChange={(e) => setMaxVideoSizeMb(Number(e.target.value))}
                          placeholder="300"
                          className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-200 font-mono text-xs focus:outline-none focus:border-blue-500"
                        />
                      </div>
                    </div>

                    {/* Storage Safety Callout */}
                    <div className="p-3 bg-emerald-950/25 border border-emerald-500/20 rounded-xl text-emerald-300 text-[11px] flex items-start gap-2">
                      <span className="text-sm">🛡️</span>
                      <div>
                        <strong>Storage-Safe Just-In-Time Pipeline:</strong> Videos are not stored in advance on your server. When a daily time slot arrives, the background worker downloads 1 video, uploads it to YouTube, and deletes the temporary file immediately.
                      </div>
                    </div>
                  </div>
                )}

                <div>
                  <label className="block font-medium text-slate-400 mb-1">Publish Privacy Status</label>
                  <select
                    value={privacyStatus}
                    onChange={(e) => setPrivacyStatus(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-red-500 font-mono"
                  >
                    <option value="public">Public (Visible to everyone)</option>
                    <option value="unlisted">Unlisted (Anyone with link)</option>
                    <option value="private">Private (Only you)</option>
                  </select>
                </div>
              </div>

              <div className="space-y-3 pt-2">
                <h4 className="font-bold text-slate-300 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Title & Description Customization (Optional)
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block font-medium text-slate-400 mb-1">Title Prefix</label>
                    <input
                      type="text"
                      placeholder="e.g. 🔥"
                      value={titlePrefix}
                      onChange={(e) => setTitlePrefix(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-400 mb-1">Title Suffix</label>
                    <input
                      type="text"
                      placeholder="e.g. #VoiceGaming"
                      value={titleSuffix}
                      onChange={(e) => setTitleSuffix(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200"
                    />
                  </div>
                </div>

                <div>
                  <label className="block font-medium text-slate-400 mb-1">Description Footer / Credits</label>
                  <textarea
                    rows={2}
                    placeholder="e.g. Credits to Voice Gaming! Subscribe for daily gameplay highlights."
                    value={descriptionFooter}
                    onChange={(e) => setDescriptionFooter(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 resize-none"
                  />
                </div>

                <div>
                  <label className="block font-medium text-slate-400 mb-1">Additional Custom Tags (Comma-separated)</label>
                  <input
                    type="text"
                    placeholder="e.g. gaming, voicegaming, highlights, funny"
                    value={customTagsInput}
                    onChange={(e) => setCustomTagsInput(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 font-mono"
                  />
                </div>
              </div>

              <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-bold shadow-lg shadow-red-900/30"
                >
                  {editingConfig ? 'Save Changes' : 'Add Monitor Pipeline'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
