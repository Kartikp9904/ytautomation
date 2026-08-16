import React, { useState, useEffect } from 'react';
import type { VideoItem } from '../../api/videos';
import { previewVideoMetadata } from '../../api/videos';
import type { Channel } from '../../api/channels';
import { triggerManualUpload, getUploadJob, type UploadJobItem } from '../../api/uploads';
import { 
  X, 
  Upload, 
  CheckCircle2, 
  AlertCircle, 
  ExternalLink, 
  Lock, 
  Eye, 
  Globe,
  Loader2
} from 'lucide-react';

interface UploadNowModalProps {
  isOpen: boolean;
  onClose: () => void;
  video: VideoItem | null;
  channels: Channel[];
}

export const UploadNowModal: React.FC<UploadNowModalProps> = ({
  isOpen,
  onClose,
  video,
  channels,
}) => {
  const [selectedChannelId, setSelectedChannelId] = useState<string>('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [privacyStatus, setPrivacyStatus] = useState('private');
  
  const [uploading, setUploading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<UploadJobItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Initialize selected channel and metadata
  useEffect(() => {
    if (isOpen && video) {
      const initialChannelId = video.channel_id || (channels.length > 0 ? channels[0].id : '');
      setSelectedChannelId(initialChannelId);
      setJobId(null);
      setJobStatus(null);
      setError(null);
      setUploading(false);

      if (initialChannelId) {
        previewVideoMetadata(video.id, { channel_id: initialChannelId })
          .then((meta) => {
            setTitle(meta.title);
            setDescription(meta.description || '');
            setPrivacyStatus(meta.privacy_status || 'private');
          })
          .catch(() => {
            setTitle(video.filename);
          });
      } else {
        setTitle(video.filename);
      }
    }
  }, [isOpen, video]);

  // Handle Channel change
  const handleChannelChange = (chId: string) => {
    setSelectedChannelId(chId);
    if (video && chId) {
      previewVideoMetadata(video.id, { channel_id: chId })
        .then((meta) => {
          setTitle(meta.title);
          setDescription(meta.description || '');
          setPrivacyStatus(meta.privacy_status || 'private');
        })
        .catch(() => {});
    }
  };

  // Poll upload job progress
  useEffect(() => {
    let timer: any = null;
    if (jobId && uploading) {
      timer = setInterval(async () => {
        try {
          const job = await getUploadJob(jobId);
          setJobStatus(job);
          if (job.status === 'SUCCESS' || job.status === 'FAILED') {
            setUploading(false);
          }
        } catch {
          // ignore
        }
      }, 1500);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [jobId, uploading]);

  if (!isOpen || !video) return null;

  const handleStartUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedChannelId) {
      setError('Please select a destination YouTube channel.');
      return;
    }

    try {
      setError(null);
      setUploading(true);
      const res = await triggerManualUpload({
        video_id: video.id,
        channel_id: selectedChannelId,
        title,
        description,
        privacy_status: privacyStatus,
      });
      setJobId(res.job_id);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to trigger upload');
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/80">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-600/20 text-red-400 border border-red-500/30">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">
                Upload to YouTube Now
              </h3>
              <p className="text-xs text-slate-400 font-mono mt-0.5 truncate max-w-sm">
                {video.filename}
              </p>
            </div>
          </div>
          {!uploading && (
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
          {error && (
            <div className="p-3.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-medium flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Job Success Screen */}
          {jobStatus?.status === 'SUCCESS' && (
            <div className="p-6 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <h4 className="font-bold text-white text-base">Video Published Successfully!</h4>
                <p className="text-xs text-slate-300 mt-1 font-mono">{jobStatus.youtube_video_id}</p>
              </div>

              <div className="pt-2">
                <a
                  href={jobStatus.youtube_url || `https://youtu.be/${jobStatus.youtube_video_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold transition shadow-lg shadow-emerald-900/30 cursor-pointer"
                >
                  <ExternalLink className="w-4 h-4" /> Watch on YouTube
                </a>
              </div>
            </div>
          )}

          {/* Upload Progress Bar */}
          {uploading && (
            <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-slate-300 flex items-center gap-2">
                  <Loader2 className="w-4 h-4 text-red-500 animate-spin" />
                  Status: <strong className="text-white uppercase font-mono">{jobStatus?.status || 'INITIALIZING'}</strong>
                </span>
                <span className="font-mono text-slate-400 font-bold">
                  {jobStatus?.progress_percentage || 0}%
                </span>
              </div>

              <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-red-600 to-amber-500 transition-all duration-300"
                  style={{ width: `${jobStatus?.progress_percentage || 10}%` }}
                ></div>
              </div>

              <p className="text-[11px] text-slate-500 text-center">
                Downloading from cloud storage and streaming resumable chunks to YouTube API...
              </p>
            </div>
          )}

          {/* Upload Form */}
          {jobStatus?.status !== 'SUCCESS' && (
            <form onSubmit={handleStartUpload} className="space-y-4">
              {/* Destination Channel */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Destination YouTube Channel *
                </label>
                <select
                  value={selectedChannelId}
                  onChange={(e) => handleChannelChange(e.target.value)}
                  disabled={uploading}
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition"
                  required
                >
                  <option value="">Select Channel...</option>
                  {channels.map((ch) => (
                    <option key={ch.id} value={ch.id}>
                      {ch.name} ({ch.timezone})
                    </option>
                  ))}
                </select>
              </div>

              {/* Title */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-medium text-slate-300">Video Title (max 100 chars)</label>
                  <span className="text-[10px] text-slate-500 font-mono">{title.length}/100</span>
                </div>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={100}
                  disabled={uploading}
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition font-mono"
                  required
                />
              </div>

              {/* Description */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-medium text-slate-300">Description</label>
                  <span className="text-[10px] text-slate-500 font-mono">{description.length}/5000</span>
                </div>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={4}
                  maxLength={5000}
                  disabled={uploading}
                  className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition font-mono resize-y"
                />
              </div>

              {/* Privacy Status */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  YouTube Privacy Status
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: 'private', label: 'Private', icon: Lock },
                    { id: 'unlisted', label: 'Unlisted', icon: Eye },
                    { id: 'public', label: 'Public', icon: Globe },
                  ].map((p) => {
                    const Icon = p.icon;
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => setPrivacyStatus(p.id)}
                        disabled={uploading}
                        className={`p-2.5 rounded-lg border text-xs font-medium flex items-center justify-center gap-2 transition cursor-pointer ${
                          privacyStatus === p.id
                            ? 'bg-red-600/20 border-red-500 text-white'
                            : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        <Icon className="w-3.5 h-3.5" />
                        {p.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Modal Footer Actions */}
              <div className="pt-4 border-t border-slate-800 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={uploading}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading}
                  className="flex items-center gap-2 px-5 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-bold transition shadow-lg shadow-red-900/30 cursor-pointer disabled:opacity-50"
                >
                  {uploading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" /> Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4" /> Publish to YouTube
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
