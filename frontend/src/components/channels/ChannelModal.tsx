import React, { useState, useEffect } from 'react';
import type { Channel, ChannelInput, TimezoneOption } from '../../api/channels';
import { YOUTUBE_CATEGORIES } from '../../constants/categories';
import { X, Plus, Globe, FileText, Tag, Shield, Check } from 'lucide-react';

interface ChannelModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: ChannelInput) => Promise<void>;
  channel?: Channel | null;
  timezones: TimezoneOption[];
}

export const ChannelModal: React.FC<ChannelModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  channel,
  timezones,
}) => {
  const [name, setName] = useState('');
  const [timezone, setTimezone] = useState('Asia/Kolkata');
  const [enabled, setEnabled] = useState(true);
  const [defaultTitleTemplate, setDefaultTitleTemplate] = useState('');
  const [defaultDescriptionTemplate, setDefaultDescriptionTemplate] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [defaultCategoryId, setDefaultCategoryId] = useState('22');
  const [defaultPrivacyStatus, setDefaultPrivacyStatus] = useState('private');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (channel) {
      setName(channel.name);
      setTimezone(channel.timezone);
      setEnabled(channel.enabled);
      setDefaultTitleTemplate(channel.default_title_template || '');
      setDefaultDescriptionTemplate(channel.default_description_template || '');
      setTags(channel.default_tags || []);
      setDefaultCategoryId(channel.default_category_id || '22');
      setDefaultPrivacyStatus(channel.default_privacy_status || 'private');
    } else {
      setName('');
      setTimezone('Asia/Kolkata');
      setEnabled(true);
      setDefaultTitleTemplate('{channel} | {date}');
      setDefaultDescriptionTemplate('Welcome to our channel. Scheduled video for {date}.');
      setTags(['devotional', 'daily']);
      setDefaultCategoryId('22');
      setDefaultPrivacyStatus('private');
    }
    setError(null);
  }, [channel, isOpen]);

  if (!isOpen) return null;

  const handleAddTag = () => {
    const trimmed = tagInput.trim().toLowerCase();
    if (trimmed && !tags.includes(trimmed)) {
      setTags([...tags, trimmed]);
      setTagInput('');
    }
  };

  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      handleAddTag();
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter((t) => t !== tagToRemove));
  };

  const insertVariable = (variable: string) => {
    setDefaultTitleTemplate((prev) => `${prev} {${variable}}`);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Channel name is required');
      return;
    }
    try {
      setLoading(true);
      setError(null);
      await onSubmit({
        name: name.trim(),
        timezone,
        enabled,
        default_title_template: defaultTitleTemplate.trim() || null,
        default_description_template: defaultDescriptionTemplate.trim() || null,
        default_tags: tags,
        default_category_id: defaultCategoryId,
        default_privacy_status: defaultPrivacyStatus,
      });
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to save channel');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/80">
          <div>
            <h3 className="text-lg font-bold text-white tracking-tight">
              {channel ? 'Edit Channel Configuration' : 'Add New YouTube Channel'}
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Set channel identification, timezone, and default metadata templates.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6 max-h-[80vh] overflow-y-auto">
          {error && (
            <div className="p-3.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-medium">
              {error}
            </div>
          )}

          {/* Basic Info */}
          <div className="space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <Globe className="w-3.5 h-3.5 text-blue-400" /> Channel Details & Timezone
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Channel Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Mahadev Bhakti Studio"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-red-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Channel Timezone *</label>
                <select
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-red-500 transition font-mono text-xs"
                >
                  {timezones.map((tz) => (
                    <option key={tz.name} value={tz.name}>
                      {tz.label}
                    </option>
                  ))}
                </select>
                <p className="text-[11px] text-slate-500 mt-1">All schedules for this channel run in this timezone.</p>
              </div>
            </div>

            <div className="flex items-center gap-3 pt-1">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={(e) => setEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-10 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-500"></div>
              </label>
              <span className="text-xs text-slate-300 font-medium">Channel Active & Enabled for Scheduling</span>
            </div>
          </div>

          <div className="border-t border-slate-800/80 pt-5 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <FileText className="w-3.5 h-3.5 text-amber-400" /> Default Metadata Templates
            </h4>

            {/* Title Template */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-slate-300">Default Title Template</label>
                <span className="text-[11px] text-slate-500">Available Variables:</span>
              </div>
              <input
                type="text"
                placeholder="e.g. Mahadev Aarti | {date} | {channel}"
                value={defaultTitleTemplate}
                onChange={(e) => setDefaultTitleTemplate(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 font-mono text-xs placeholder-slate-500 focus:outline-none focus:border-red-500 transition"
              />
              <div className="flex flex-wrap gap-1.5 mt-2">
                {['channel', 'date', 'day', 'month', 'year', 'filename'].map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => insertVariable(v)}
                    className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[11px] text-slate-300 font-mono border border-slate-700 flex items-center gap-1 transition cursor-pointer"
                  >
                    <Plus className="w-3 h-3 text-red-400" /> {`{${v}}`}
                  </button>
                ))}
              </div>
            </div>

            {/* Description Template */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Default Description Template</label>
              <textarea
                rows={3}
                placeholder="Default description appended to uploaded videos..."
                value={defaultDescriptionTemplate}
                onChange={(e) => setDefaultDescriptionTemplate(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-red-500 transition"
              />
            </div>

            {/* Tags */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center gap-1.5">
                <Tag className="w-3.5 h-3.5 text-blue-400" /> Default Tags (Comma separated or Enter)
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Type a tag and press Enter"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={handleTagKeyDown}
                  className="flex-1 px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition"
                />
                <button
                  type="button"
                  onClick={handleAddTag}
                  className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium border border-slate-700 transition cursor-pointer"
                >
                  Add
                </button>
              </div>
              {tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2.5">
                  {tags.map((t) => (
                    <span
                      key={t}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-600/15 text-red-300 border border-red-500/20"
                    >
                      #{t}
                      <button
                        type="button"
                        onClick={() => handleRemoveTag(t)}
                        className="hover:text-red-100 transition ml-0.5 cursor-pointer"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Category & Privacy */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">YouTube Video Category</label>
                <select
                  value={defaultCategoryId}
                  onChange={(e) => setDefaultCategoryId(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition"
                >
                  {YOUTUBE_CATEGORIES.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-emerald-400" /> Default Privacy Status
                </label>
                <select
                  value={defaultPrivacyStatus}
                  onChange={(e) => setDefaultPrivacyStatus(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition capitalize"
                >
                  <option value="private">Private (Required for scheduled releases)</option>
                  <option value="unlisted">Unlisted</option>
                  <option value="public">Public</option>
                </select>
              </div>
            </div>
          </div>

          {/* Modal Footer */}
          <div className="border-t border-slate-800 pt-5 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2.5 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-medium shadow-lg shadow-red-900/20 transition flex items-center gap-2 cursor-pointer"
            >
              {loading && <span className="w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin"></span>}
              <Check className="w-4 h-4" />
              {channel ? 'Save Changes' : 'Create Channel'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
