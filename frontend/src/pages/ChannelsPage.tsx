import React, { useState, useEffect } from 'react';
import type { 
  Channel, 
  ChannelInput, 
  TimezoneOption 
} from '../api/channels';
import { 
  getChannels, 
  getTimezones, 
  createChannel, 
  updateChannel, 
  toggleChannel, 
  deleteChannel 
} from '../api/channels';
import { ChannelCard } from '../components/channels/ChannelCard';
import { ChannelModal } from '../components/channels/ChannelModal';
import { Tv, Plus, Search, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react';

export const ChannelsPage: React.FC = () => {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [timezones, setTimezones] = useState<TimezoneOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedChannel, setSelectedChannel] = useState<Channel | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [channelsData, timezonesData] = await Promise.all([
        getChannels(),
        getTimezones(),
      ]);
      setChannels(channelsData.items);
      setTimezones(timezonesData);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load channels');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();

    // Check OAuth return params
    const params = new URLSearchParams(window.location.search);
    if (params.get('youtube_connected') === 'true') {
      const title = params.get('title') || 'YouTube Channel';
      setSuccessMsg(`Successfully connected and verified YouTube channel "${title}"!`);
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (params.get('youtube_error')) {
      setError(`YouTube Connection Failed: ${params.get('youtube_error')}`);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const handleOpenAdd = () => {
    setSelectedChannel(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (channel: Channel) => {
    setSelectedChannel(channel);
    setIsModalOpen(true);
  };

  const handleModalSubmit = async (data: ChannelInput) => {
    if (selectedChannel) {
      await updateChannel(selectedChannel.id, data);
      setSuccessMsg(`Channel "${data.name}" updated.`);
    } else {
      await createChannel(data);
      setSuccessMsg(`New channel "${data.name}" created.`);
    }
    await loadData();
  };

  const handleToggleStatus = async (id: string) => {
    try {
      const updated = await toggleChannel(id);
      setChannels(channels.map((c) => (c.id === id ? updated : c)));
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to toggle channel status');
    }
  };

  const handleDeleteChannel = async (id: string) => {
    try {
      await deleteChannel(id);
      setChannels(channels.filter((c) => c.id !== id));
      setSuccessMsg('Channel deleted.');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete channel');
    }
  };

  const filteredChannels = channels.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.timezone.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">YouTube Channels</h2>
          <p className="text-sm text-slate-400 mt-1">
            Manage multiple YouTube channels, timezone configurations, OAuth tokens, and API quotas.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={loading}
            className="p-2.5 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 rounded-lg transition cursor-pointer"
            title="Refresh list"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleOpenAdd}
            className="flex items-center gap-2 px-4 py-2.5 bg-red-600 hover:bg-red-500 text-white rounded-lg text-sm font-medium transition shadow-lg shadow-red-900/20 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            Add Channel
          </button>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-sm flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Search Bar & Total */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="relative max-w-md w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search channels by name or timezone..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-red-500 transition"
          />
        </div>
        <div className="text-xs text-slate-400 font-medium">
          Total Channels: <span className="text-white font-bold">{channels.length}</span>
        </div>
      </div>

      {/* Loading state */}
      {loading && channels.length === 0 ? (
        <div className="py-20 flex flex-col items-center justify-center space-y-3">
          <div className="w-8 h-8 border-3 border-red-500/20 border-t-red-500 rounded-full animate-spin"></div>
          <span className="text-xs text-slate-400">Loading channels...</span>
        </div>
      ) : filteredChannels.length > 0 ? (
        /* Channel Cards Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredChannels.map((channel) => (
            <ChannelCard
              key={channel.id}
              channel={channel}
              onEdit={handleOpenEdit}
              onToggle={handleToggleStatus}
              onDelete={handleDeleteChannel}
              onRefresh={loadData}
            />
          ))}
        </div>
      ) : (
        /* Empty State */
        <div className="p-12 text-center border border-dashed border-slate-800 rounded-xl space-y-4 bg-slate-900/40">
          <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mx-auto text-slate-400">
            <Tv className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="font-semibold text-slate-200">
              {search ? 'No matching channels found' : 'No YouTube Channels Added Yet'}
            </h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              {search
                ? 'Try adjusting your search term to find a configured channel.'
                : 'Click "Add Channel" above to configure your first YouTube channel and set its timezone.'}
            </p>
          </div>
          {!search && (
            <button
              onClick={handleOpenAdd}
              className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-medium transition cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              Add Your First Channel
            </button>
          )}
        </div>
      )}

      {/* Add / Edit Channel Modal */}
      <ChannelModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleModalSubmit}
        channel={selectedChannel}
        timezones={timezones}
      />
    </div>
  );
};
