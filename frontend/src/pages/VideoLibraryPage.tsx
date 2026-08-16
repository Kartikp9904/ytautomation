import React, { useState, useEffect } from 'react';
import type { VideoItem, ContentFolderItem } from '../api/videos';
import { getVideos, toggleVideo, getContentFolders } from '../api/videos';
import type { Channel } from '../api/channels';
import { getChannels } from '../api/channels';
import { MetadataPreviewModal } from '../components/videos/MetadataPreviewModal';
import { UploadNowModal } from '../components/videos/UploadNowModal';
import { 
  Film, 
  Search, 
  Calendar, 
  FileJson, 
  Image, 
  Sparkles, 
  Power, 
  Folder, 
  Tv, 
  RefreshCw,
  AlertCircle,
  Upload
} from 'lucide-react';

export const VideoLibraryPage: React.FC = () => {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [totalVideos, setTotalVideos] = useState<number>(0);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [folders, setFolders] = useState<ContentFolderItem[]>([]);
  
  const [search, setSearch] = useState('');
  const [selectedChannelId, setSelectedChannelId] = useState<string>('');
  const [selectedFolderId, setSelectedFolderId] = useState<string>('');
  const [selectedDay, setSelectedDay] = useState<number | undefined>(undefined);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewVideo, setPreviewVideo] = useState<VideoItem | null>(null);
  const [uploadVideo, setUploadVideo] = useState<VideoItem | null>(null);

  const loadFilterOptions = async () => {
    try {
      const [chData, fData] = await Promise.all([
        getChannels(),
        getContentFolders(),
      ]);
      setChannels(chData.items);
      setFolders(fData);
    } catch {
      // Ignored
    }
  };

  const loadVideos = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getVideos({
        search: search || undefined,
        channel_id: selectedChannelId || undefined,
        folder_id: selectedFolderId || undefined,
        day_of_month: selectedDay,
      });
      setVideos(res.items);
      setTotalVideos(res.total);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load videos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFilterOptions();
  }, []);

  useEffect(() => {
    loadVideos();
  }, [selectedChannelId, selectedFolderId, selectedDay]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadVideos();
  };

  const handleToggle = async (id: string) => {
    try {
      const updated = await toggleVideo(id);
      setVideos(videos.map((v) => (v.id === id ? updated : v)));
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to toggle video');
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Video Library</h2>
          <p className="text-sm text-slate-400 mt-1">
            Browse indexed video assets, review sidecar metadata JSONs, thumbnails, and trigger manual "Upload Now" pipelines.
          </p>
        </div>
        <button
          onClick={loadVideos}
          disabled={loading}
          className="flex items-center gap-2 px-3.5 py-2 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 rounded-lg text-xs font-medium transition cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Library
        </button>
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Filter Bar */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4 backdrop-blur">
        <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {/* Search Box */}
          <div className="sm:col-span-2 relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search filename or path (e.g. 15.mp4 or Mahadev)..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-red-500 transition"
            />
          </div>

          {/* Channel Selector */}
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

          {/* Folder Selector */}
          <div>
            <select
              value={selectedFolderId}
              onChange={(e) => setSelectedFolderId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition"
            >
              <option value="">All Folders ({videos.length} videos)</option>
              {folders
                .filter((f) => (f.videos_count ?? 0) > 0)
                .map((f) => (
                  <option key={f.id} value={f.id}>
                    📁 {f.name} ({f.videos_count} {f.videos_count === 1 ? 'vid' : 'vids'})
                  </option>
                ))}
            </select>
          </div>
        </form>

        {/* Day-of-Month Pill Filter (1 to 31) */}
        <div className="pt-2 border-t border-slate-800/80 flex items-center gap-2 overflow-x-auto pb-1 text-xs">
          <span className="text-slate-400 font-medium shrink-0 flex items-center gap-1 text-[11px]">
            <Calendar className="w-3 h-3 text-purple-400" /> Day of Month:
          </span>
          <button
            onClick={() => setSelectedDay(undefined)}
            className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition cursor-pointer shrink-0 ${
              selectedDay === undefined
                ? 'bg-red-600 text-white font-bold'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            All Days
          </button>
          {Array.from({ length: 31 }, (_, i) => i + 1).map((d) => (
            <button
              key={d}
              onClick={() => setSelectedDay(d)}
              className={`px-2 py-1 rounded-md text-[11px] font-mono transition cursor-pointer shrink-0 ${
                selectedDay === d
                  ? 'bg-red-600 text-white font-bold'
                  : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* Videos List / Grid */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center space-y-3">
          <div className="w-8 h-8 border-3 border-red-500/20 border-t-red-500 rounded-full animate-spin"></div>
          <span className="text-xs text-slate-400">Loading video library...</span>
        </div>
      ) : videos.length > 0 ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400 px-1">
            <span>Showing <strong className="text-white">{videos.length}</strong> of <strong className="text-white">{totalVideos}</strong> videos</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {videos.map((vid) => (
              <div
                key={vid.id}
                className={`p-4 rounded-xl border transition-all flex flex-col justify-between backdrop-blur ${
                  vid.enabled
                    ? 'bg-slate-900/80 border-slate-800 hover:border-slate-700 shadow-md'
                    : 'bg-slate-900/40 border-slate-800/60 opacity-60'
                }`}
              >
                <div className="space-y-3">
                  {/* Top Header */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="p-2 rounded-lg bg-red-600/15 text-red-400 border border-red-500/20 shrink-0">
                        <Film className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <h4 className="font-bold text-white text-xs truncate" title={vid.filename}>
                          {vid.filename}
                        </h4>
                        <p className="text-[10px] text-slate-500 font-mono truncate" title={vid.path}>
                          {vid.path}
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={() => handleToggle(vid.id)}
                      title={vid.enabled ? 'Disable Video' : 'Enable Video'}
                      className={`p-1.5 rounded-lg border transition cursor-pointer ${
                        vid.enabled
                          ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                          : 'bg-slate-800 text-slate-500 border-slate-700'
                      }`}
                    >
                      <Power className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Badges Bar */}
                  <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                    {vid.day_of_month_index && (
                      <span className="px-2 py-0.5 rounded font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                        Day #{vid.day_of_month_index}
                      </span>
                    )}
                    <span className="px-2 py-0.5 rounded font-mono bg-slate-800 text-slate-300 border border-slate-700">
                      {formatBytes(vid.size_bytes)}
                    </span>
                    {vid.custom_metadata && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                        <FileJson className="w-3 h-3" /> JSON
                      </span>
                    )}
                    {vid.custom_thumbnail_file_id && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-300 border border-blue-500/30">
                        <Image className="w-3 h-3" /> Thumb
                      </span>
                    )}
                  </div>

                  {/* Channel & Folder Association */}
                  <div className="text-[11px] text-slate-400 space-y-1 bg-slate-950/40 p-2 rounded-lg border border-slate-800/60">
                    <div className="flex items-center gap-1.5 truncate">
                      <Tv className="w-3 h-3 text-slate-500 shrink-0" />
                      <span>Channel: <strong className="text-slate-300">{vid.channel_name || 'Unassigned'}</strong></span>
                    </div>
                    <div className="flex items-center gap-1.5 truncate">
                      <Folder className="w-3 h-3 text-slate-500 shrink-0" />
                      <span>Folder: <strong className="text-slate-300">{vid.folder_name || 'Root'}</strong></span>
                    </div>
                  </div>
                </div>

                {/* Footer Actions */}
                <div className="border-t border-slate-800/80 pt-3 mt-3 flex items-center justify-between gap-2">
                  <button
                    onClick={() => setPreviewVideo(vid)}
                    className="flex items-center gap-1 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-[11px] font-medium transition cursor-pointer border border-slate-700"
                  >
                    <Sparkles className="w-3 h-3 text-amber-400" />
                    Preview
                  </button>

                  <button
                    onClick={() => setUploadVideo(vid)}
                    className="flex items-center gap-1 px-2.5 py-1.5 bg-red-600 hover:bg-red-500 text-white rounded-lg text-[11px] font-bold transition shadow-md shadow-red-900/20 cursor-pointer"
                  >
                    <Upload className="w-3 h-3" />
                    Upload Now
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* Empty State */
        <div className="p-12 text-center border border-dashed border-slate-800 rounded-2xl space-y-4 bg-slate-900/40">
          <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mx-auto text-slate-400">
            <Film className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="font-semibold text-slate-200">No Videos Found in Library</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Go to Google Drive page and click "Scan Index Now" (or "Generate Sample Data" for dev testing) to populate the video library.
            </p>
          </div>
        </div>
      )}

      {/* Metadata Preview Modal */}
      <MetadataPreviewModal
        isOpen={!!previewVideo}
        onClose={() => setPreviewVideo(null)}
        video={previewVideo}
      />

      {/* Upload Now Modal */}
      <UploadNowModal
        isOpen={!!uploadVideo}
        onClose={() => setUploadVideo(null)}
        video={uploadVideo}
        channels={channels}
      />
    </div>
  );
};
