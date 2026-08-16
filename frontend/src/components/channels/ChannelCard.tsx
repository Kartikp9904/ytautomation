import React, { useState, useEffect } from 'react';
import type { Channel } from '../../api/channels';
import { 
  getYouTubeAuthUrl, 
  disconnectYouTubeChannel, 
  getYouTubeConnectionStatus,
  type YouTubeConnectionStatus 
} from '../../api/youtube';
import { 
  Tv, 
  Globe, 
  CalendarDays, 
  Film, 
  Edit2, 
  Trash2, 
  CheckCircle2, 
  AlertCircle, 
  Power,
  ExternalLink,
  Unplug,
  Activity
} from 'lucide-react';

interface ChannelCardProps {
  channel: Channel;
  onEdit: (channel: Channel) => void;
  onToggle: (id: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onRefresh?: () => void;
}

export const ChannelCard: React.FC<ChannelCardProps> = ({
  channel,
  onEdit,
  onToggle,
  onDelete,
  onRefresh,
}) => {
  const [deleting, setDeleting] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [ytStatus, setYtStatus] = useState<YouTubeConnectionStatus | null>(null);

  useEffect(() => {
    getYouTubeConnectionStatus(channel.id)
      .then((status) => setYtStatus(status))
      .catch(() => {});
  }, [channel.id, channel.is_connected]);

  const handleToggle = async () => {
    try {
      setToggling(true);
      await onToggle(channel.id);
    } finally {
      setToggling(false);
    }
  };

  const handleDelete = async () => {
    if (window.confirm(`Are you sure you want to delete channel "${channel.name}"? This will also remove associated schedules.`)) {
      try {
        setDeleting(true);
        await onDelete(channel.id);
      } finally {
        setDeleting(false);
      }
    }
  };

  const handleConnectYouTube = async () => {
    try {
      setConnecting(true);
      const { auth_url } = await getYouTubeAuthUrl(channel.id);
      window.location.href = auth_url;
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to initiate YouTube connection');
      setConnecting(false);
    }
  };

  const handleDisconnectYouTube = async () => {
    if (window.confirm(`Disconnect YouTube account from "${channel.name}"? Scheduled uploads will be paused.`)) {
      try {
        setDisconnecting(true);
        await disconnectYouTubeChannel(channel.id);
        if (onRefresh) onRefresh();
        const updatedStatus = await getYouTubeConnectionStatus(channel.id);
        setYtStatus(updatedStatus);
      } catch (err: any) {
        alert(err.response?.data?.detail || 'Failed to disconnect YouTube');
      } finally {
        setDisconnecting(false);
      }
    }
  };

  const isConnected = ytStatus ? ytStatus.is_connected : channel.is_connected;
  const quotaUsed = ytStatus ? ytStatus.daily_quota_used : 0;
  const quotaLimit = ytStatus ? ytStatus.daily_quota_limit : 10000;
  const quotaPercent = Math.min(100, Math.round((quotaUsed / quotaLimit) * 100));

  return (
    <div className={`rounded-xl border transition-all p-5 flex flex-col justify-between backdrop-blur ${
      channel.enabled
        ? 'bg-slate-900/80 border-slate-800 hover:border-slate-700 shadow-lg'
        : 'bg-slate-900/40 border-slate-800/60 opacity-75'
    }`}>
      <div className="space-y-4">
        {/* Top Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-xl border ${
              channel.enabled 
                ? 'bg-red-600/15 text-red-400 border-red-500/20' 
                : 'bg-slate-800 text-slate-500 border-slate-700'
            }`}>
              <Tv className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-base tracking-tight">{channel.name}</h3>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-300 border border-slate-700/60">
                  <Globe className="w-3 h-3 text-blue-400" />
                  {channel.timezone}
                </span>
              </div>
            </div>
          </div>

          {/* Status Toggle Button */}
          <button
            onClick={handleToggle}
            disabled={toggling}
            title={channel.enabled ? "Disable Channel" : "Enable Channel"}
            className={`p-1.5 rounded-lg border transition cursor-pointer ${
              channel.enabled
                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/25'
                : 'bg-slate-800 text-slate-500 border-slate-700 hover:text-slate-300'
            }`}
          >
            <Power className="w-4 h-4" />
          </button>
        </div>

        {/* YouTube Authorization Card */}
        <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              {isConnected ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              ) : (
                <AlertCircle className="w-4 h-4 text-amber-400" />
              )}
              <span className="text-slate-300 font-medium">
                {isConnected ? 'YouTube Authorized' : 'YouTube Not Connected'}
              </span>
            </div>

            {isConnected ? (
              <button
                onClick={handleDisconnectYouTube}
                disabled={disconnecting}
                className="flex items-center gap-1 text-[11px] text-rose-400 hover:text-rose-300 cursor-pointer font-medium"
              >
                <Unplug className="w-3 h-3" /> Disconnect
              </button>
            ) : (
              <button
                onClick={handleConnectYouTube}
                disabled={connecting}
                className="flex items-center gap-1 px-2 py-0.5 rounded bg-red-600 hover:bg-red-500 text-white font-medium text-[11px] transition cursor-pointer shadow"
              >
                <ExternalLink className="w-3 h-3" /> Connect
              </button>
            )}
          </div>

          {isConnected && (
            <div className="pt-1.5 border-t border-slate-800/60 space-y-1.5 text-[11px]">
              <div className="flex items-center justify-between text-slate-400 font-mono">
                <span>Channel ID:</span>
                <span className="text-slate-200">{channel.youtube_channel_id || ytStatus?.youtube_channel_id}</span>
              </div>
              
              {/* Daily Quota Progress */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-[10px] text-slate-400">
                  <span className="flex items-center gap-1">
                    <Activity className="w-3 h-3 text-cyan-400" /> Daily API Quota
                  </span>
                  <span>{quotaUsed.toLocaleString()} / {quotaLimit.toLocaleString()} units ({quotaPercent}%)</span>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div 
                    className={`h-full transition-all duration-300 ${
                      quotaPercent > 80 ? 'bg-rose-500' : quotaPercent > 50 ? 'bg-amber-500' : 'bg-cyan-500'
                    }`}
                    style={{ width: `${quotaPercent}%` }}
                  ></div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Channel Stats */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="p-2.5 rounded-lg bg-slate-950/40 border border-slate-800 flex items-center gap-2.5">
            <CalendarDays className="w-4 h-4 text-purple-400" />
            <div>
              <div className="font-bold text-white text-sm">{channel.schedules_count}</div>
              <div className="text-[11px] text-slate-500">Active Schedules</div>
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-950/40 border border-slate-800 flex items-center gap-2.5">
            <Film className="w-4 h-4 text-blue-400" />
            <div>
              <div className="font-bold text-white text-sm">{channel.videos_count}</div>
              <div className="text-[11px] text-slate-500">Linked Videos</div>
            </div>
          </div>
        </div>

        {/* Metadata Preview */}
        {channel.default_title_template && (
          <div className="text-xs space-y-1 bg-slate-950/30 p-2.5 rounded-lg border border-slate-800/50">
            <div className="text-[11px] text-slate-500">Default Title Pattern:</div>
            <div className="font-mono text-slate-300 text-[11px] truncate">{channel.default_title_template}</div>
          </div>
        )}

        {/* Tags */}
        {channel.default_tags && channel.default_tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {channel.default_tags.slice(0, 4).map((tag) => (
              <span
                key={tag}
                className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700/50"
              >
                #{tag}
              </span>
            ))}
            {channel.default_tags.length > 4 && (
              <span className="px-1.5 py-0.5 rounded text-[10px] text-slate-500">
                +{channel.default_tags.length - 4} more
              </span>
            )}
          </div>
        )}
      </div>

      {/* Card Footer Actions */}
      <div className="border-t border-slate-800/80 pt-4 mt-4 flex items-center justify-between">
        <span className="text-[11px] text-slate-500 capitalize">
          Privacy: <strong className="text-slate-300">{channel.default_privacy_status}</strong>
        </span>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => onEdit(channel)}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition cursor-pointer"
            title="Edit Channel"
          >
            <Edit2 className="w-4 h-4" />
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition cursor-pointer"
            title="Delete Channel"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
