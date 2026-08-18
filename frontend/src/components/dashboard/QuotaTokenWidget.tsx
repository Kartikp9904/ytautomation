import React, { useEffect, useState } from 'react';
import { getQuotaSummary, type QuotaSummary } from '../../api/youtube';
import { 
  Coins, 
  UploadCloud, 
  Clock, 
  Tv
} from 'lucide-react';

export const QuotaTokenWidget: React.FC = () => {
  const [quota, setQuota] = useState<QuotaSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [countdown, setCountdown] = useState<string>('');

  const loadQuota = async () => {
    try {
      const data = await getQuotaSummary();
      setQuota(data);
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQuota();
    const interval = setInterval(loadQuota, 10000);
    return () => clearInterval(interval);
  }, []);

  // Update countdown timer to midnight UTC
  useEffect(() => {
    const updateTimer = () => {
      const now = new Date();
      const nowUtc = Date.UTC(
        now.getUTCFullYear(),
        now.getUTCMonth(),
        now.getUTCDate(),
        now.getUTCHours(),
        now.getUTCMinutes(),
        now.getUTCSeconds()
      );
      const tomorrowUtc = Date.UTC(
        now.getUTCFullYear(),
        now.getUTCMonth(),
        now.getUTCDate() + 1,
        0,
        0,
        0
      );
      const diffMs = tomorrowUtc - nowUtc;
      if (diffMs <= 0) {
        setCountdown('Resetting now...');
        return;
      }
      const hours = Math.floor(diffMs / (1000 * 60 * 60));
      const mins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
      const secs = Math.floor((diffMs % (1000 * 60)) / 1000);
      setCountdown(`${hours}h ${mins}m ${secs}s`);
    };

    updateTimer();
    const timerInterval = setInterval(updateTimer, 1000);
    return () => clearInterval(timerInterval);
  }, []);

  if (loading && !quota) {
    return (
      <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 animate-pulse">
        <div className="h-4 bg-slate-800 rounded w-1/4 mb-3"></div>
        <div className="h-8 bg-slate-800 rounded w-1/2"></div>
      </div>
    );
  }

  const limit = quota?.daily_limit || 10000;
  const used = quota?.total_used_today || 0;
  const remaining = quota?.total_remaining_today ?? (limit - used);
  const percent = quota?.percent_used ?? Math.round((used / limit) * 100);
  const estUploads = quota?.estimated_uploads_remaining ?? Math.floor(remaining / 1600);

  const getMeterColor = () => {
    if (percent > 85) return 'from-rose-500 to-red-600 text-rose-400 border-rose-500/40 bg-rose-500/10';
    if (percent > 60) return 'from-amber-500 to-orange-500 text-amber-400 border-amber-500/40 bg-amber-500/10';
    return 'from-emerald-500 to-teal-500 text-emerald-400 border-emerald-500/40 bg-emerald-500/10';
  };

  return (
    <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900/90 via-slate-900/60 to-slate-950 border border-slate-800 shadow-xl backdrop-blur relative overflow-hidden">
      {/* Background Accent Glow */}
      <div className="absolute top-0 right-0 w-72 h-72 bg-red-600/5 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
        {/* Left: Main Token Stats */}
        <div className="space-y-3 max-w-lg">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <Coins className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                YouTube API Quota & Tokens
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getMeterColor()}`}>
                  {100 - percent}% Units Left
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Daily allotment for automated video uploads, thumbnail attachments, and channel sync.
              </p>
            </div>
          </div>

          {/* Meter Bar */}
          <div className="space-y-1.5 pt-1">
            <div className="flex justify-between text-xs">
              <span className="text-slate-400 font-medium">
                Used: <strong className="text-white font-mono">{used.toLocaleString()}</strong> / {limit.toLocaleString()} Units
              </span>
              <span className="text-emerald-400 font-mono font-semibold">
                {remaining.toLocaleString()} Units Remaining
              </span>
            </div>
            <div className="w-full h-3 bg-slate-950 rounded-full overflow-hidden p-0.5 border border-slate-800">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${
                  percent > 85 ? 'from-rose-500 to-red-600' : percent > 60 ? 'from-amber-500 to-orange-500' : 'from-emerald-500 to-teal-400'
                } transition-all duration-500`}
                style={{ width: `${Math.min(100, Math.max(3, percent))}%` }}
              />
            </div>
          </div>
        </div>

        {/* Right: Quick Action Insights & Countdown */}
        <div className="grid grid-cols-2 sm:grid-cols-2 gap-3 lg:w-96 shrink-0">
          {/* Estimated Uploads Left */}
          <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span>Shorts Uploads Left</span>
              <UploadCloud className="w-4 h-4 text-blue-400" />
            </div>
            <div className="mt-2">
              <div className="text-xl font-bold text-white font-mono">~{estUploads}</div>
              <span className="text-[10px] text-slate-500">(1,600 units / video)</span>
            </div>
          </div>

          {/* Daily Reset Countdown */}
          <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span>Daily Quota Reset</span>
              <Clock className="w-4 h-4 text-amber-400" />
            </div>
            <div className="mt-2">
              <div className="text-sm font-bold text-amber-300 font-mono">{countdown || '00:00 UTC'}</div>
              <span className="text-[10px] text-slate-500">Resets at 00:00 UTC</span>
            </div>
          </div>
        </div>
      </div>

      {/* Optional Channel Breakdown Pill list if multiple channels */}
      {quota && quota.channels && quota.channels.length > 1 && (
        <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center gap-3 text-xs">
          <span className="text-slate-400 font-medium flex items-center gap-1">
            <Tv className="w-3.5 h-3.5" /> Channel Usage:
          </span>
          {quota.channels.map((ch) => (
            <div
              key={ch.channel_id}
              className="px-2.5 py-1 rounded-lg bg-slate-950/80 border border-slate-800 text-[11px] text-slate-300 flex items-center gap-2"
            >
              <span className="font-semibold text-white">{ch.channel_name}</span>
              <span className="text-slate-400 font-mono">{ch.used_units} units</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
