import React, { useState, useEffect } from 'react';
import type { VideoItem, MetadataPreview } from '../../api/videos';
import { previewVideoMetadata } from '../../api/videos';
import { 
  X, 
  Sparkles, 
  FileText, 
  Tag, 
  Layers, 
  Calendar,
  CheckCircle2
} from 'lucide-react';

interface MetadataPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  video: VideoItem | null;
}

export const MetadataPreviewModal: React.FC<MetadataPreviewModalProps> = ({
  isOpen,
  onClose,
  video,
}) => {
  const [preview, setPreview] = useState<MetadataPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [targetDate, setTargetDate] = useState<string>(new Date().toISOString().split('T')[0]);

  const loadPreview = async () => {
    if (!video) return;
    try {
      setLoading(true);
      setError(null);
      const data = await previewVideoMetadata(video.id, {
        channel_id: video.channel_id || undefined,
        target_date: `${targetDate}T09:00:00`,
      });
      setPreview(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to resolve effective metadata');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && video) {
      loadPreview();
    }
  }, [isOpen, video, targetDate]);

  if (!isOpen || !video) return null;

  const getSourceBadge = (sourceType: string) => {
    switch (sourceType) {
      case 'video_sidecar':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
            Sidecar .JSON
          </span>
        );
      case 'folder_default':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-purple-500/15 text-purple-300 border border-purple-500/30">
            Folder Default
          </span>
        );
      case 'schedule_template':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-blue-500/15 text-blue-300 border border-blue-500/30">
            Schedule Template
          </span>
        );
      case 'channel_default':
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-amber-500/15 text-amber-300 border border-amber-500/30">
            Channel Default
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-400 border border-slate-700">
            System Default
          </span>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/80">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-600/20 text-red-400 border border-red-500/30">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">
                Effective Metadata Preview
              </h3>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                {video.filename} {video.day_of_month_index && `(Day #${video.day_of_month_index})`}
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

        {/* Date Selector Simulation Bar */}
        <div className="px-6 py-3 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-2 text-slate-300">
            <Calendar className="w-4 h-4 text-blue-400" />
            <span>Simulate Publish Date for Variable Substitution:</span>
          </div>
          <input
            type="date"
            value={targetDate}
            onChange={(e) => setTargetDate(e.target.value)}
            className="px-3 py-1 bg-slate-900 border border-slate-700 rounded text-slate-200 text-xs focus:outline-none focus:border-red-500 font-mono"
          />
        </div>

        {/* Body */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          {error && (
            <div className="p-3.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-medium">
              {error}
            </div>
          )}

          {loading ? (
            <div className="py-16 flex flex-col items-center justify-center space-y-3">
              <div className="w-6 h-6 border-2 border-red-500/20 border-t-red-500 rounded-full animate-spin"></div>
              <span className="text-xs text-slate-400">Resolving priority hierarchy...</span>
            </div>
          ) : preview ? (
            <div className="space-y-6">
              {/* Resolved YouTube Title */}
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-red-400" /> Final YouTube Video Title
                  </span>
                  {getSourceBadge(preview.source_hierarchy["title"] || "system_default")}
                </div>
                <div className="text-sm font-semibold text-white bg-slate-900/90 p-3 rounded-lg border border-slate-800/80 font-mono">
                  {preview.title}
                </div>
              </div>

              {/* Resolved Description */}
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-blue-400" /> Final Video Description
                  </span>
                  {getSourceBadge(preview.source_hierarchy["description"] || "system_default")}
                </div>
                <div className="text-xs text-slate-300 bg-slate-900/90 p-3 rounded-lg border border-slate-800/80 whitespace-pre-wrap leading-relaxed">
                  {preview.description}
                </div>
              </div>

              {/* Tags & Category Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Tags */}
                <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                      <Tag className="w-3.5 h-3.5 text-purple-400" /> Tags
                    </span>
                    {getSourceBadge(preview.source_hierarchy["tags"] || "system_default")}
                  </div>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {preview.tags.map((t) => (
                      <span
                        key={t}
                        className="px-2 py-0.5 rounded text-xs font-medium bg-red-600/15 text-red-300 border border-red-500/20"
                      >
                        #{t}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Category & Thumbnail */}
                <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-amber-400" /> Category & Thumbnail
                    </span>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800">
                      <span className="text-slate-400">Category ID:</span>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-slate-200 font-bold">{preview.category_id}</span>
                        {getSourceBadge(preview.source_hierarchy["category_id"] || "system_default")}
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800">
                      <span className="text-slate-400">Thumbnail:</span>
                      <div className="flex items-center gap-2">
                        <span className="text-slate-200 font-medium">
                          {preview.thumbnail_storage_id ? 'Custom Image Found' : 'None (Default)'}
                        </span>
                        {getSourceBadge(preview.source_hierarchy["thumbnail"] || "none")}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Priority Hierarchy Provenance Explanation */}
              <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/80 text-xs space-y-2">
                <h4 className="font-bold text-slate-300 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Priority Engine Summary
                </h4>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  Metadata resolved according to rule: <strong className="text-slate-200">Video Sidecar JSON &gt; Folder Default &gt; Schedule Template &gt; Channel Default &gt; Global</strong>.
                </p>
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-900/80 flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition cursor-pointer"
          >
            Close Preview
          </button>
        </div>
      </div>
    </div>
  );
};
