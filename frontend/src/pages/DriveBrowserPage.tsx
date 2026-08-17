import React, { useState, useEffect } from 'react';
import type { DriveStatus, DriveFolderItem, ScanSummary } from '../api/drive';
import { 
  getDriveStatus, 
  getDriveAuthUrl, 
  disconnectDrive, 
  getFolders, 
  triggerScan, 
  createSampleLocalData 
} from '../api/drive';
import type { Channel } from '../api/channels';
import { getChannels } from '../api/channels';
import { 
  HardDrive, 
  Folder, 
  RefreshCw, 
  ExternalLink, 
  CheckCircle2, 
  AlertCircle, 
  ChevronRight, 
  FolderTree, 
  Sparkles, 
  Film, 
  FileJson, 
  Image, 
  Unplug
} from 'lucide-react';

interface BreadcrumbItem {
  id: string;
  name: string;
}

export const DriveBrowserPage: React.FC = () => {
  const [driveStatus, setDriveStatus] = useState<DriveStatus | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [folders, setFolders] = useState<DriveFolderItem[]>([]);
  const [currentFolderId, setCurrentFolderId] = useState<string>('root');
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([{ id: 'root', name: 'Root Directory' }]);
  const [selectedChannelId, setSelectedChannelId] = useState<string>('');
  
  const [loadingFolders, setLoadingFolders] = useState<boolean>(false);
  const [scanning, setScanning] = useState<boolean>(false);
  const [generatingSamples, setGeneratingSamples] = useState<boolean>(false);
  const [scanSummary, setScanSummary] = useState<ScanSummary | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadStatusAndChannels = async () => {
    try {
      const [statusData, channelsData] = await Promise.all([
        getDriveStatus(),
        getChannels(),
      ]);
      setDriveStatus(statusData);
      setChannels(channelsData.items);
      if (channelsData.items.length > 0 && !selectedChannelId) {
        setSelectedChannelId(channelsData.items[0].id);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to check storage status');
    }
  };

  const loadFolders = async (parentId: string) => {
    try {
      setLoadingFolders(true);
      setError(null);
      const data = await getFolders(parentId === 'root' ? undefined : parentId);
      setFolders(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to list folders');
    } finally {
      setLoadingFolders(false);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('connected') === 'true') {
      setStatusMessage('Google Drive connected successfully!');
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (params.get('drive_error')) {
      setError(`Google Drive Connection Failed: ${params.get('drive_error')}`);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
    loadStatusAndChannels();
    loadFolders('root');
  }, []);

  const handleNavigateToFolder = (folder: DriveFolderItem) => {
    setCurrentFolderId(folder.id);
    setBreadcrumbs([...breadcrumbs, { id: folder.id, name: folder.name }]);
    loadFolders(folder.id);
  };

  const handleNavigateBreadcrumb = (index: number) => {
    const target = breadcrumbs[index];
    const newBreadcrumbs = breadcrumbs.slice(0, index + 1);
    setBreadcrumbs(newBreadcrumbs);
    setCurrentFolderId(target.id);
    loadFolders(target.id);
  };

  const handleConnectDrive = async () => {
    try {
      const authUrl = await getDriveAuthUrl();
      window.location.href = authUrl;
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Please configure GOOGLE_CLIENT_ID in Settings or .env first.');
    }
  };

  const handleDisconnectDrive = async () => {
    if (window.confirm('Are you sure you want to disconnect Google Drive?')) {
      try {
        await disconnectDrive();
        await loadStatusAndChannels();
        await loadFolders('root');
      } catch (err: any) {
        alert(err.response?.data?.detail || 'Failed to disconnect Drive');
      }
    }
  };

  const handleGenerateSampleData = async () => {
    try {
      setGeneratingSamples(true);
      setError(null);
      const result = await createSampleLocalData();
      setStatusMessage(`Created sample devotional folder hierarchy (${result.total_files_created} files across ${result.structure.join(', ')}).`);
      await loadFolders(currentFolderId);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to create sample local files');
    } finally {
      setGeneratingSamples(false);
    }
  };

  const handleTriggerScan = async () => {
    try {
      setScanning(true);
      setError(null);
      setScanSummary(null);
      setStatusMessage(null);
      const summary = await triggerScan(
        currentFolderId === 'root' ? undefined : currentFolderId,
        selectedChannelId || undefined
      );
      setScanSummary(summary);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Storage scan failed');
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Google Drive & Video Storage</h2>
          <p className="text-sm text-slate-400 mt-1">
            Browse source video hierarchies, configure automation root folders, and synchronize the video index.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              loadStatusAndChannels();
              loadFolders(currentFolderId);
            }}
            disabled={loadingFolders}
            className="flex items-center gap-2 px-3.5 py-2 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 rounded-lg text-xs font-medium transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingFolders ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Error / Status Alerts */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-sm flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {statusMessage && (
        <div className="p-4 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-sm flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>{statusMessage}</span>
        </div>
      )}

      {/* Storage Status Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Connection Status Card */}
        <div className="p-6 rounded-xl bg-slate-900/70 border border-slate-800 space-y-4 backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Primary Storage</span>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
              {driveStatus?.storage_provider || 'local'}
            </span>
          </div>

          <div className="flex items-center gap-3.5">
            <div className={`p-3 rounded-xl border ${
              driveStatus?.connected 
                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' 
                : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}>
              <HardDrive className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-bold text-white text-base">
                {driveStatus?.storage_provider === 'google_drive' ? 'Google Drive' : 'Local Storage'}
              </h3>
              <p className="text-xs text-slate-400">
                {driveStatus?.connected 
                  ? (driveStatus.account_email ? `Connected: ${driveStatus.account_email}` : 'Connected & Active')
                  : 'Operating in Local Test Mode'}
              </p>
            </div>
          </div>

          <div className="pt-2 flex flex-wrap items-center gap-2">
            {driveStatus?.connected ? (
              <button
                onClick={handleDisconnectDrive}
                className="flex items-center gap-2 px-3.5 py-2 bg-slate-800 hover:bg-rose-500/15 hover:text-rose-300 text-slate-300 rounded-lg text-xs font-medium border border-slate-700 hover:border-rose-500/30 transition cursor-pointer"
              >
                <Unplug className="w-3.5 h-3.5" />
                Disconnect Drive
              </button>
            ) : (
              <button
                onClick={handleConnectDrive}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium transition shadow-lg shadow-blue-900/20 cursor-pointer font-semibold"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Connect Google Drive
              </button>
            )}

            {/* Helper to generate sample devotional structure */}
            <button
              onClick={handleGenerateSampleData}
              disabled={generatingSamples}
              className="flex items-center gap-2 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium border border-slate-700 transition cursor-pointer"
              title="Create mock Channel_1/Mahadev, Channel_2 folder tree for offline dev testing"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              {generatingSamples ? 'Creating Sample Tree...' : 'Generate Sample Data'}
            </button>
          </div>
        </div>

        {/* Scan & Synchronization Trigger Card */}
        <div className="lg:col-span-2 p-6 rounded-xl bg-slate-900/70 border border-slate-800 space-y-4 backdrop-blur">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">File Scanner & Indexer</span>
            <span className="text-xs text-slate-400">
              Current Folder: <strong className="text-white font-mono">{breadcrumbs[breadcrumbs.length - 1].name}</strong>
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="sm:col-span-2">
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Link Videos to Channel (Optional)</label>
              <select
                value={selectedChannelId}
                onChange={(e) => setSelectedChannelId(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-red-500 transition"
              >
                <option value="">-- Auto-detect from Channel Folder names --</option>
                {channels.map((ch) => (
                  <option key={ch.id} value={ch.id}>
                    {ch.name} ({ch.timezone})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={handleTriggerScan}
                disabled={scanning}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-red-900/20 transition cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${scanning ? 'animate-spin' : ''}`} />
                {scanning ? 'Scanning Files...' : 'Scan Index Now'}
              </button>
            </div>
          </div>

          {/* Live Scan Results Banner */}
          {scanSummary && (
            <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between text-xs font-semibold text-emerald-400">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" /> Index Scan Completed Successfully
                </span>
                <span className="text-slate-400 font-mono text-[11px]">Root: {scanSummary.root_id}</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 flex items-center gap-2">
                  <FolderTree className="w-4 h-4 text-purple-400" />
                  <div>
                    <div className="font-bold text-white">{scanSummary.folders_found}</div>
                    <div className="text-[10px] text-slate-500">Folders</div>
                  </div>
                </div>
                <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 flex items-center gap-2">
                  <Film className="w-4 h-4 text-blue-400" />
                  <div>
                    <div className="font-bold text-white">{scanSummary.videos_found}</div>
                    <div className="text-[10px] text-slate-500">Videos</div>
                  </div>
                </div>
                <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 flex items-center gap-2">
                  <FileJson className="w-4 h-4 text-amber-400" />
                  <div>
                    <div className="font-bold text-white">{scanSummary.sidecar_json_found}</div>
                    <div className="text-[10px] text-slate-500">Sidecar JSONs</div>
                  </div>
                </div>
                <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 flex items-center gap-2">
                  <Image className="w-4 h-4 text-emerald-400" />
                  <div>
                    <div className="font-bold text-white">{scanSummary.thumbnails_found}</div>
                    <div className="text-[10px] text-slate-500">Thumbnails</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Folder Hierarchy Explorer */}
      <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
        {/* Breadcrumb Bar */}
        <div className="flex items-center justify-between flex-wrap gap-2 pb-3 border-b border-slate-800">
          <nav className="flex items-center gap-1.5 text-xs text-slate-400 flex-wrap">
            {breadcrumbs.map((b, idx) => (
              <React.Fragment key={b.id}>
                {idx > 0 && <ChevronRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />}
                <button
                  onClick={() => handleNavigateBreadcrumb(idx)}
                  className={`hover:text-white transition cursor-pointer font-medium ${
                    idx === breadcrumbs.length - 1 ? 'text-red-400 font-bold' : ''
                  }`}
                >
                  {b.name}
                </button>
              </React.Fragment>
            ))}
          </nav>
          <span className="text-[11px] text-slate-500">
            {folders.length} {folders.length === 1 ? 'folder' : 'folders'} found
          </span>
        </div>

        {/* Folder Grid */}
        {loadingFolders ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-3">
            <div className="w-6 h-6 border-2 border-red-500/20 border-t-red-500 rounded-full animate-spin"></div>
            <span className="text-xs text-slate-400">Browsing directory...</span>
          </div>
        ) : folders.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3.5">
            {folders.map((f) => (
              <div
                key={f.id}
                onClick={() => handleNavigateToFolder(f)}
                className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-red-500/40 hover:bg-slate-900/90 transition cursor-pointer flex items-center justify-between group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 group-hover:bg-amber-500/20 transition">
                    <Folder className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="font-semibold text-slate-200 text-xs truncate group-hover:text-white">
                      {f.name}
                    </h4>
                    <p className="text-[10px] text-slate-500 font-mono truncate">{f.path}</p>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-300 transition shrink-0 ml-2" />
              </div>
            ))}
          </div>
        ) : (
          <div className="py-12 text-center border border-dashed border-slate-800 rounded-xl space-y-3 bg-slate-950/40">
            <Folder className="w-8 h-8 text-slate-600 mx-auto" />
            <div className="text-xs text-slate-400 font-medium">
              No subfolders in this directory.
            </div>
            <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
              You can click "Scan Index Now" to index all video files inside this folder, or click "Generate Sample Data" to scaffold devotional video channels.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
