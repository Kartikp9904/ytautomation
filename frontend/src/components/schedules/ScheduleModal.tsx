import React, { useState, useEffect } from 'react';
import type { ScheduleItem, ScheduleCreateData } from '../../api/schedules';
import type { Channel } from '../../api/channels';
import type { ContentFolderItem, VideoItem } from '../../api/videos';
import { YOUTUBE_CATEGORIES } from '../../constants/categories';
import { getPresets, type ContentPreset } from '../../api/presets';
import { PresetManagerModal } from './PresetManagerModal';
import { 
  X, 
  Clock, 
  Tv, 
  Sparkles,
  ShieldAlert,
  CalendarCheck,
  FolderTree,
  Search,
  Copy,
  Settings2,
  Globe,
  Sliders,
  Baby
} from 'lucide-react';

interface ScheduleModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: ScheduleCreateData) => Promise<void>;
  schedule?: ScheduleItem | null;
  channels: Channel[];
  folders: ContentFolderItem[];
  videos: VideoItem[];
}

const DAYS_OF_WEEK = [
  { id: 'MON', label: 'Mon' },
  { id: 'TUE', label: 'Tue' },
  { id: 'WED', label: 'Wed' },
  { id: 'THU', label: 'Thu' },
  { id: 'FRI', label: 'Fri' },
  { id: 'SAT', label: 'Sat' },
  { id: 'SUN', label: 'Sun' },
];

export const ScheduleModal: React.FC<ScheduleModalProps> = ({
  isOpen,
  onClose,
  onSave,
  schedule,
  channels,
  folders,
  videos,
}) => {
  const [channelId, setChannelId] = useState('');
  const [name, setName] = useState('');
  const [scheduleType, setScheduleType] = useState('DAILY');
  const [sourceType, setSourceType] = useState('FOLDER');
  const [sourceId, setSourceId] = useState('');
  const [mode, setMode] = useState('DAY_OF_MONTH');
  const [publishTime, setPublishTime] = useState('09:00');
  const [uploadLeadMinutes, setUploadLeadMinutes] = useState<number>(180);
  const [useYoutubeScheduledPublish, setUseYoutubeScheduledPublish] = useState<boolean>(true);
  const [dryRun, setDryRun] = useState<boolean>(false);
  const [selectedDaysOfWeek, setSelectedDaysOfWeek] = useState<string[]>(['MON', 'WED', 'FRI']);
  const [dayOfMonth, setDayOfMonth] = useState<number>(1);
  const [enabled, setEnabled] = useState(true);

  // Metadata overrides
  const [titleTemplate, setTitleTemplate] = useState('');
  const [descriptionTemplate, setDescriptionTemplate] = useState('');
  const [tagsInput, setTagsInput] = useState('');
  const [categoryId, setCategoryId] = useState('22');
  const [privacyStatus, setPrivacyStatus] = useState('private');

  // Advanced YouTube Upload Options
  const [madeForKids, setMadeForKids] = useState<boolean>(false);
  const [ageRestricted, setAgeRestricted] = useState<boolean>(false);
  const [defaultLanguage, setDefaultLanguage] = useState<string>('hi');
  const [defaultAudioLanguage, setDefaultAudioLanguage] = useState<string>('hi');
  const [containsSyntheticMedia, setContainsSyntheticMedia] = useState<boolean>(false);
  const [presetCategory, setPresetCategory] = useState<string>('mahadev');

  // Presets modal
  const [isPresetModalOpen, setIsPresetModalOpen] = useState<boolean>(false);
  const [presetsList, setPresetsList] = useState<ContentPreset[]>([]);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [folderSearch, setFolderSearch] = useState('');

  const isDuplicate = !!(schedule && !schedule.id);

  const selectedFolder = folders.find((f) => f.id === sourceId);

  const availableFolders = folders
    .filter((f) => (f.videos_count ?? 0) > 0)
    .filter((f) => {
      if (!folderSearch.trim()) return true;
      const q = folderSearch.toLowerCase();
      return f.name.toLowerCase().includes(q) || f.path.toLowerCase().includes(q);
    })
    .sort((a, b) => a.path.localeCompare(b.path));

  const loadPresetsList = async () => {
    try {
      const data = await getPresets();
      setPresetsList(data);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    loadPresetsList();
  }, []);

  useEffect(() => {
    if (schedule) {
      setChannelId(schedule.channel_id);
      setName(schedule.name);
      setScheduleType(schedule.schedule_type);
      setSourceType(schedule.source_type);
      setSourceId(schedule.source_id);
      setMode(schedule.mode);
      setPublishTime(schedule.publish_time);
      setUploadLeadMinutes(schedule.upload_lead_minutes ?? 180);
      setUseYoutubeScheduledPublish(schedule.use_youtube_scheduled_publish ?? true);
      setDryRun(schedule.dry_run ?? false);
      setSelectedDaysOfWeek(schedule.days_of_week || ['MON']);
      setDayOfMonth(schedule.day_of_month || 1);
      setEnabled(schedule.enabled);
      setTitleTemplate(schedule.title_template || '');
      setDescriptionTemplate(schedule.description_template || '');
      setTagsInput(schedule.tags?.join(', ') || '');
      setCategoryId(schedule.category_id || '22');
      setPrivacyStatus(schedule.privacy_status || 'private');
      setMadeForKids(schedule.made_for_kids ?? false);
      setAgeRestricted(schedule.age_restricted ?? false);
      setDefaultLanguage(schedule.default_language || 'hi');
      setDefaultAudioLanguage(schedule.default_audio_language || 'hi');
      setContainsSyntheticMedia(schedule.contains_synthetic_media ?? false);
      setPresetCategory(schedule.preset_category || 'mahadev');
    } else {
      setChannelId(channels[0]?.id || '');
      setName('');
      setScheduleType('DAILY');
      setSourceType('FOLDER');
      const firstValidFolder = folders.find((f) => (f.videos_count ?? 0) > 0) || folders[0];
      setSourceId(firstValidFolder?.id || '');
      setMode('DAY_OF_MONTH');
      setPublishTime('09:00');
      setUploadLeadMinutes(180);
      setUseYoutubeScheduledPublish(true);
      setDryRun(false);
      setSelectedDaysOfWeek(['MON', 'WED', 'FRI']);
      setDayOfMonth(1);
      setEnabled(true);
      setTitleTemplate('{dynamic_hook}');
      setDescriptionTemplate('');
      setTagsInput('');
      setCategoryId('22');
      setPrivacyStatus('private');
      setMadeForKids(false);
      setAgeRestricted(false);
      setDefaultLanguage('hi');
      setDefaultAudioLanguage('hi');
      setContainsSyntheticMedia(false);
      setPresetCategory('mahadev');
    }
    setError(null);
  }, [schedule, isOpen, channels, folders]);

  if (!isOpen) return null;

  const selectedChannel = channels.find((c) => c.id === channelId);

  const toggleDayOfWeek = (day: string) => {
    if (selectedDaysOfWeek.includes(day)) {
      if (selectedDaysOfWeek.length > 1) {
        setSelectedDaysOfWeek(selectedDaysOfWeek.filter((d) => d !== day));
      }
    } else {
      setSelectedDaysOfWeek([...selectedDaysOfWeek, day]);
    }
  };

  const insertVariable = (variable: string, field: 'title' | 'description') => {
    if (field === 'title') {
      setTitleTemplate((prev) => (prev ? `${prev} ${variable}` : variable));
    } else {
      setDescriptionTemplate((prev) => (prev ? `${prev}\n${variable}` : variable));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Schedule name is required');
      return;
    }
    if (!channelId) {
      setError('Please select a channel');
      return;
    }
    if (!sourceId) {
      setError('Please select a source folder or video');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      const tags = tagsInput
        .split(',')
        .map((t) => t.trim())
        .filter((t) => t.length > 0);

      const payload: ScheduleCreateData = {
        channel_id: channelId,
        name: name.trim(),
        schedule_type: scheduleType,
        source_type: sourceType,
        source_id: sourceId,
        mode,
        publish_time: publishTime,
        timezone: selectedChannel?.timezone || 'UTC',
        upload_lead_minutes: uploadLeadMinutes,
        use_youtube_scheduled_publish: useYoutubeScheduledPublish,
        dry_run: dryRun,
        days_of_week: scheduleType === 'WEEKLY' ? selectedDaysOfWeek : undefined,
        day_of_month: scheduleType === 'MONTHLY' ? dayOfMonth : undefined,
        enabled,
        title_template: titleTemplate || undefined,
        description_template: descriptionTemplate || undefined,
        tags: tags.length > 0 ? tags : undefined,
        category_id: categoryId,
        privacy_status: privacyStatus,
        made_for_kids: madeForKids,
        age_restricted: ageRestricted,
        default_language: defaultLanguage,
        default_audio_language: defaultAudioLanguage,
        contains_synthetic_media: containsSyntheticMedia,
        preset_category: presetCategory || undefined,
      };

      await onSave(payload);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to save schedule');
    } finally {
      setSaving(false);
    }
  };

  const handleApplyPreset = (preset: ContentPreset) => {
    setPresetCategory(preset.id);
    setTitleTemplate('{dynamic_hook}');
    setDescriptionTemplate('{dynamic_description}');
    if (preset.tags && preset.tags.length > 0) setTagsInput(preset.tags.join(', '));
    if (preset.category_id) setCategoryId(preset.category_id);
    if (preset.default_language) setDefaultLanguage(preset.default_language);
    if (preset.default_audio_language) setDefaultAudioLanguage(preset.default_audio_language);
    if (preset.made_for_kids !== undefined) setMadeForKids(preset.made_for_kids);
    if (preset.age_restricted !== undefined) setAgeRestricted(preset.age_restricted);
    if (preset.contains_synthetic_media !== undefined) setContainsSyntheticMedia(preset.contains_synthetic_media);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/80">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg border ${isDuplicate ? 'bg-cyan-600/20 text-cyan-400 border-cyan-500/30' : 'bg-red-600/20 text-red-400 border-red-500/30'}`}>
              {isDuplicate ? <Copy className="w-5 h-5" /> : <Clock className="w-5 h-5" />}
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">
                {isDuplicate ? 'Duplicate & Create Schedule' : schedule && schedule.id ? 'Edit Schedule Rule' : 'Create Automation Schedule'}
              </h3>
              <p className="text-xs text-slate-400">
                {isDuplicate
                  ? 'Creating a new independent schedule pre-filled from an existing template.'
                  : 'Configure timing, lead-time buffer, YouTube scheduled premiere, and metadata templates.'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit}>
          <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
            {isDuplicate && (
              <div className="p-3.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs flex items-center gap-3">
                <Copy className="w-4 h-4 shrink-0 text-cyan-400" />
                <span>
                  <strong>Duplication Active:</strong> All templates, tags, and settings are pre-filled. Adjust the time, channel, or name as needed and click <strong>Create Schedule</strong> to register a new scheduler.
                </span>
              </div>
            )}

            {error && (
              <div className="p-3.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-medium">
                {error}
              </div>
            )}

            {/* Target Channel & Schedule Name */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
                  <Tv className="w-3.5 h-3.5 text-red-400" /> Target Channel *
                </label>
                <select
                  value={channelId}
                  onChange={(e) => setChannelId(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition"
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
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Schedule Name *</label>
                <input
                  type="text"
                  placeholder="e.g. Daily Morning Aarti (9:00 AM)"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-red-500 transition"
                  required
                />
              </div>
            </div>

            {/* Schedule Type & Publish Time */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Schedule Frequency *</label>
                <select
                  value={scheduleType}
                  onChange={(e) => setScheduleType(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition"
                >
                  <option value="DAILY">Daily (Every Day)</option>
                  <option value="WEEKLY">Weekly (Specific Days)</option>
                  <option value="MONTHLY">Monthly (Specific Day)</option>
                  <option value="ONE_TIME">One-Time Run</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Automation Mode *</label>
                <select
                  value={mode}
                  onChange={(e) => setMode(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition"
                >
                  <option value="DAY_OF_MONTH">Day-of-Month (1.mp4, 15.mp4)</option>
                  <option value="ROTATION">Sequential Rotation</option>
                  <option value="REPEAT">Repeat Single Video</option>
                  <option value="SHUFFLE">Random Shuffle (No Repeat)</option>
                  <option value="SINGLE_VIDEO">Single Video</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center justify-between">
                  <span>Publish Time *</span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {selectedChannel?.timezone || 'UTC'}
                  </span>
                </label>
                <input
                  type="time"
                  value={publishTime}
                  onChange={(e) => setPublishTime(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 font-mono transition"
                  required
                />
              </div>
            </div>

            {/* Lead Time & Advanced YouTube Automation Options */}
            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                  <CalendarCheck className="w-4 h-4 text-emerald-400" />
                  YouTube Pre-Upload & Lead Time
                </span>
                <span className="text-[11px] text-slate-400">
                  Buffer: <strong className="text-emerald-400">{uploadLeadMinutes} min</strong> ({Math.round(uploadLeadMinutes/60)} hrs ahead)
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="block text-[11px] text-slate-300 mb-1 font-medium">
                    Upload Lead Time Buffer (Minutes)
                  </label>
                  <select
                    value={uploadLeadMinutes}
                    onChange={(e) => setUploadLeadMinutes(parseInt(e.target.value) || 0)}
                    className="w-full px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition"
                  >
                    <option value={0}>0 mins (Upload at publish time)</option>
                    <option value={30}>30 mins in advance</option>
                    <option value={60}>1 hour in advance</option>
                    <option value={120}>2 hours in advance</option>
                    <option value={180}>3 hours in advance (Recommended)</option>
                    <option value={360}>6 hours in advance</option>
                    <option value={720}>12 hours in advance</option>
                  </select>
                </div>

                <div className="space-y-2 pt-1">
                  <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useYoutubeScheduledPublish}
                      onChange={(e) => setUseYoutubeScheduledPublish(e.target.checked)}
                      className="rounded border-slate-700 text-red-600 focus:ring-red-500 w-4 h-4 bg-slate-900"
                    />
                    <span>Schedule via YouTube <code className="text-red-400 font-mono text-[10px]">publishAt</code></span>
                  </label>

                  <label className="flex items-center gap-2 text-xs text-amber-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={dryRun}
                      onChange={(e) => setDryRun(e.target.checked)}
                      className="rounded border-slate-700 text-amber-500 focus:ring-amber-400 w-4 h-4 bg-slate-900"
                    />
                    <span className="flex items-center gap-1">
                      <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
                      Dry Run (Simulate without API calls)
                    </span>
                  </label>
                </div>
              </div>
            </div>

            {/* Weekly Days of Week Picker */}
            {scheduleType === 'WEEKLY' && (
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <label className="block text-xs font-semibold text-slate-300">Select Active Days of Week</label>
                <div className="flex flex-wrap gap-2">
                  {DAYS_OF_WEEK.map((d) => (
                    <button
                      key={d.id}
                      type="button"
                      onClick={() => toggleDayOfWeek(d.id)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                        selectedDaysOfWeek.includes(d.id)
                          ? 'bg-red-600 text-white shadow-md'
                          : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-white'
                      }`}
                    >
                      {d.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Monthly Day Picker */}
            {scheduleType === 'MONTHLY' && (
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <label className="block text-xs font-semibold text-slate-300">Select Day of Month (1 - 31)</label>
                <input
                  type="number"
                  min="1"
                  max="31"
                  value={dayOfMonth}
                  onChange={(e) => setDayOfMonth(parseInt(e.target.value) || 1)}
                  className="w-32 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white font-mono focus:outline-none focus:border-red-500"
                />
              </div>
            )}

            {/* Source Selection (Folder or Video) */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Source Type *</label>
                <select
                  value={sourceType}
                  onChange={(e) => {
                    const st = e.target.value;
                    setSourceType(st);
                    setSourceId(st === 'FOLDER' ? (folders[0]?.id || '') : (videos[0]?.id || ''));
                  }}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition"
                >
                  <option value="FOLDER">Content Folder</option>
                  <option value="VIDEO">Specific Video</option>
                </select>
              </div>

              <div className="sm:col-span-2 space-y-2">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-semibold text-slate-300">
                    {sourceType === 'FOLDER' ? 'Select Target Folder or Subfolder *' : 'Select Video *'}
                  </label>
                  {sourceType === 'FOLDER' && (
                    <span className="text-[11px] text-slate-400">
                      {availableFolders.length} {availableFolders.length === 1 ? 'folder' : 'folders'} with videos
                    </span>
                  )}
                </div>

                {sourceType === 'FOLDER' ? (
                  <div className="space-y-2">
                    {/* Quick Search */}
                    <div className="relative">
                      <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        placeholder="Search folders or subfolders (e.g. Mahadev, Animations, Part 2)..."
                        value={folderSearch}
                        onChange={(e) => setFolderSearch(e.target.value)}
                        className="w-full pl-8 pr-16 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-red-500 transition"
                      />
                      {folderSearch && (
                        <button
                          type="button"
                          onClick={() => setFolderSearch('')}
                          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 text-[11px] font-medium bg-slate-800 px-1.5 py-0.5 rounded cursor-pointer"
                        >
                          Clear
                        </button>
                      )}
                    </div>

                    {/* Hierarchical Dropdown */}
                    <select
                      value={sourceId}
                      onChange={(e) => setSourceId(e.target.value)}
                      className="w-full px-3 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition font-mono"
                      required
                    >
                      {availableFolders.length === 0 ? (
                        <option value="">No matching folders or subfolders found</option>
                      ) : (
                        availableFolders.map((f) => {
                          const depth = (f.path.match(/\//g) || []).length;
                          const prefix = depth > 0 ? `${'\u00A0\u00A0'.repeat(depth)}↳ ` : '📁 ';
                          const pathDisplay = f.path.split('/').join(' › ');
                          return (
                            <option key={f.id} value={f.id}>
                              {prefix}{pathDisplay} ({f.videos_count} {f.videos_count === 1 ? 'vid' : 'vids'})
                            </option>
                          );
                        })
                      )}
                    </select>

                    {/* Selected Folder/Subfolder Details Card */}
                    {selectedFolder && (
                      <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 flex items-start justify-between gap-3 text-xs">
                        <div className="space-y-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-white flex items-center gap-1.5">
                              <FolderTree className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                              {selectedFolder.name}
                            </span>
                            <span className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[10px] font-bold">
                              {selectedFolder.videos_count} {selectedFolder.videos_count === 1 ? 'Video' : 'Videos'} Ready
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-400 font-mono truncate">
                            📍 <span className="text-slate-500">Full Path:</span> {selectedFolder.path}
                          </p>
                        </div>
                        <div className="text-[10px] text-slate-500 shrink-0 text-right font-medium">
                          <span>Target Source</span>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <select
                    value={sourceId}
                    onChange={(e) => setSourceId(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition"
                    required
                  >
                    {videos.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.filename} ({v.day_of_month_index ? `Day #${v.day_of_month_index}` : 'No day'}) - {v.path}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            {/* Niche Preset Category & 31-Day Hook Selector */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-amber-400" />
                  <span className="text-xs font-bold text-white">Content Niche & 31-Day Hook Preset</span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                    Auto-Rotate 31+ Titles
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setIsPresetModalOpen(true)}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-blue-400 text-xs font-medium border border-slate-700 transition cursor-pointer"
                >
                  <Settings2 className="w-3.5 h-3.5" />
                  Manage & Upload Hooks
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => {
                    const m = presetsList.find((p) => p.id === 'mahadev');
                    if (m) handleApplyPreset(m);
                    else setPresetCategory('mahadev');
                  }}
                  className={`p-2.5 rounded-xl border text-left transition cursor-pointer flex flex-col gap-0.5 ${
                    presetCategory === 'mahadev'
                      ? 'bg-amber-500/15 border-amber-500/40 text-amber-200'
                      : 'bg-slate-950/60 hover:bg-slate-900 border-slate-800 text-slate-400'
                  }`}
                >
                  <span className="text-xs font-bold text-white">🔱 Mahadev Niche</span>
                  <span className="text-[10px] text-slate-400">35+ Universal status hooks</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    const s = presetsList.find((p) => p.id === 'shinchan');
                    if (s) handleApplyPreset(s);
                    else setPresetCategory('shinchan');
                  }}
                  className={`p-2.5 rounded-xl border text-left transition cursor-pointer flex flex-col gap-0.5 ${
                    presetCategory === 'shinchan'
                      ? 'bg-red-500/15 border-red-500/40 text-red-200'
                      : 'bg-slate-950/60 hover:bg-slate-900 border-slate-800 text-slate-400'
                  }`}
                >
                  <span className="text-xs font-bold text-white">😂 Shinchan Niche</span>
                  <span className="text-[10px] text-slate-400">35+ Comedy hooks</span>
                </button>

                <button
                  type="button"
                  onClick={() => setPresetCategory('')}
                  className={`p-2.5 rounded-xl border text-left transition cursor-pointer flex flex-col gap-0.5 ${
                    !presetCategory
                      ? 'bg-slate-800 border-slate-600 text-white'
                      : 'bg-slate-950/60 hover:bg-slate-900 border-slate-800 text-slate-400'
                  }`}
                >
                  <span className="text-xs font-bold text-white">Custom / None</span>
                  <span className="text-[10px] text-slate-400">Manual metadata rules</span>
                </button>
              </div>
            </div>

            {/* Template Variables Helper */}
            <div className="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
                <span className="flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Click variable to insert into Title:
                </span>
                <span className="text-[11px] text-emerald-400 font-mono">
                  {'{dynamic_hook}'} = Unique hook every day
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {['{dynamic_hook}', '{channel}', '{date}', '{day}', '{month}', '{year}', '{filename}'].map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => insertVariable(v, 'title')}
                    className={`px-2 py-0.5 rounded font-mono text-[11px] border transition cursor-pointer ${
                      v === '{dynamic_hook}'
                        ? 'bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border-emerald-500/30 font-bold'
                        : 'bg-slate-900 hover:bg-slate-800 text-red-400 hover:text-red-300 border-slate-800'
                    }`}
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>

            {/* Title & Description Override Templates */}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Title Template Override (Use {'{dynamic_hook}'} for 31-day auto-rotation)
                </label>
                <input
                  type="text"
                  placeholder="e.g. {dynamic_hook} or {channel} | {date}"
                  value={titleTemplate}
                  onChange={(e) => setTitleTemplate(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-red-500 transition font-mono"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-slate-300">
                    Description Template Override (Use {'{dynamic_description}'} for 31-day auto-rotating captions)
                  </label>
                  <button
                    type="button"
                    onClick={() => insertVariable('{dynamic_description}', 'description')}
                    className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/25 font-mono font-bold cursor-pointer transition"
                  >
                    + {'{dynamic_description}'}
                  </button>
                </div>
                <textarea
                  rows={3}
                  placeholder="e.g. {dynamic_description} or Daily video for {date}. Subscribe to {channel}."
                  value={descriptionTemplate}
                  onChange={(e) => setDescriptionTemplate(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-red-500 transition resize-none font-mono"
                />
              </div>
            </div>

            {/* Tags, Category & Privacy */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Tags (Comma-separated)</label>
                <input
                  type="text"
                  placeholder="mahadev, shorts, shivbhakti"
                  value={tagsInput}
                  onChange={(e) => setTagsInput(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-red-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Category</label>
                <select
                  value={categoryId}
                  onChange={(e) => setCategoryId(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition"
                >
                  {YOUTUBE_CATEGORIES.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Privacy Status</label>
                <select
                  value={privacyStatus}
                  onChange={(e) => setPrivacyStatus(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition"
                >
                  <option value="private">Private (Recommended)</option>
                  <option value="unlisted">Unlisted</option>
                  <option value="public">Public</option>
                </select>
              </div>
            </div>

            {/* Advanced YouTube Upload & Audience Settings */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-4">
              <div className="flex items-center gap-2 text-xs font-bold text-white border-b border-slate-800/80 pb-2">
                <Sliders className="w-4 h-4 text-blue-400" />
                <span>Advanced YouTube Upload & Audience Settings</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Made for Kids */}
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                    <Baby className="w-3.5 h-3.5 text-pink-400" /> Audience (Made for Kids)
                  </label>
                  <select
                    value={madeForKids ? 'yes' : 'no'}
                    onChange={(e) => setMadeForKids(e.target.value === 'yes')}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500"
                  >
                    <option value="no">No, it's not made for kids (Recommended for Shorts Feed)</option>
                    <option value="yes">Yes, it's made for kids</option>
                  </select>
                </div>

                {/* Age Restriction */}
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5 text-amber-400" /> Age Restriction
                  </label>
                  <select
                    value={ageRestricted ? 'yes' : 'no'}
                    onChange={(e) => setAgeRestricted(e.target.value === 'yes')}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500"
                  >
                    <option value="no">No, don't restrict to viewers 18 and older</option>
                    <option value="yes">Yes, restrict to viewers 18 and older (18+)</option>
                  </select>
                </div>

                {/* Video Language */}
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                    <Globe className="w-3.5 h-3.5 text-emerald-400" /> Video Language
                  </label>
                  <select
                    value={defaultLanguage}
                    onChange={(e) => setDefaultLanguage(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500"
                  >
                    <option value="hi">Hindi (hi)</option>
                    <option value="en">English (en)</option>
                    <option value="mr">Marathi (mr)</option>
                    <option value="gu">Gujarati (gu)</option>
                    <option value="ta">Tamil (ta)</option>
                    <option value="te">Telugu (te)</option>
                    <option value="bn">Bengali (bn)</option>
                  </select>
                </div>

                {/* Audio Language */}
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                    <Globe className="w-3.5 h-3.5 text-cyan-400" /> Audio Language
                  </label>
                  <select
                    value={defaultAudioLanguage}
                    onChange={(e) => setDefaultAudioLanguage(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500"
                  >
                    <option value="hi">Hindi (hi)</option>
                    <option value="en">English (en)</option>
                    <option value="mr">Marathi (mr)</option>
                    <option value="gu">Gujarati (gu)</option>
                    <option value="ta">Tamil (ta)</option>
                    <option value="te">Telugu (te)</option>
                    <option value="bn">Bengali (bn)</option>
                  </select>
                </div>
              </div>

              {/* Altered / Synthetic Media Checkbox */}
              <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between">
                <div>
                  <span className="text-xs font-medium text-slate-200 block">Altered or Synthetic Content</span>
                  <span className="text-[11px] text-slate-400 block">Check if content is generated by AI or significantly altered</span>
                </div>
                <input
                  type="checkbox"
                  checked={containsSyntheticMedia}
                  onChange={(e) => setContainsSyntheticMedia(e.target.checked)}
                  className="w-4 h-4 text-red-600 rounded bg-slate-900 border-slate-700 focus:ring-red-500 cursor-pointer"
                />
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-slate-800 bg-slate-900/80 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-red-900/20 transition cursor-pointer"
            >
              {saving ? 'Saving Schedule...' : isDuplicate ? 'Create Duplicate Schedule' : schedule && schedule.id ? 'Update Schedule' : 'Create Schedule'}
            </button>
          </div>
        </form>
      </div>

      {/* Preset & Hook Manager Modal */}
      {isPresetModalOpen && (
        <PresetManagerModal
          isOpen={isPresetModalOpen}
          onClose={() => {
            setIsPresetModalOpen(false);
            loadPresetsList();
          }}
          onSelectPreset={(p) => {
            handleApplyPreset(p);
            setIsPresetModalOpen(false);
          }}
        />
      )}
    </div>
  );
};

