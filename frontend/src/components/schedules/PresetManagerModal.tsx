import React, { useState, useEffect, useRef } from 'react';
import {
  getPresets,
  savePreset,
  uploadPresetsJsonFile,
  exportPresetsJson,
  type ContentPreset
} from '../../api/presets';
import {
  X,
  Plus,
  Trash2,
  Upload,
  Download,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  FileJson,
  Layers,
  RotateCw
} from 'lucide-react';

interface PresetManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectPreset?: (preset: ContentPreset) => void;
}

export const PresetManagerModal: React.FC<PresetManagerModalProps> = ({
  isOpen,
  onClose,
  onSelectPreset
}) => {
  const [presets, setPresets] = useState<ContentPreset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string>('mahadev');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // New Hook input
  const [newHookText, setNewHookText] = useState<string>('');
  const [bulkHooksText, setBulkHooksText] = useState<string>('');
  const [isBulkAdding, setIsBulkAdding] = useState<boolean>(false);

  // File upload input
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadPresets = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getPresets();
      setPresets(data);
      if (data.length > 0 && !data.find((p) => p.id === selectedPresetId)) {
        setSelectedPresetId(data[0].id);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load presets');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadPresets();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const currentPreset = presets.find((p) => p.id === selectedPresetId) || presets[0];

  const showSuccess = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 4000);
  };

  const handleAddSingleHook = async () => {
    if (!newHookText.trim() || !currentPreset) return;
    try {
      const updatedHooks = [...currentPreset.hooks, newHookText.trim()];
      const updatedPreset = { ...currentPreset, hooks: updatedHooks };
      await savePreset(updatedPreset);
      setPresets(presets.map((p) => (p.id === currentPreset.id ? updatedPreset : p)));
      setNewHookText('');
      showSuccess('Hook added successfully!');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add hook');
    }
  };

  const handleBulkAddHooks = async () => {
    if (!bulkHooksText.trim() || !currentPreset) return;
    try {
      const lines = bulkHooksText
        .split('\n')
        .map((l) => l.trim())
        .filter((l) => l.length > 0);
      if (lines.length === 0) return;

      const updatedHooks = [...currentPreset.hooks, ...lines];
      const updatedPreset = { ...currentPreset, hooks: updatedHooks };
      await savePreset(updatedPreset);
      setPresets(presets.map((p) => (p.id === currentPreset.id ? updatedPreset : p)));
      setBulkHooksText('');
      setIsBulkAdding(false);
      showSuccess(`Added ${lines.length} hooks successfully!`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to bulk add hooks');
    }
  };

  const handleDeleteHook = async (indexToDelete: number) => {
    if (!currentPreset) return;
    try {
      const updatedHooks = currentPreset.hooks.filter((_, i) => i !== indexToDelete);
      const updatedPreset = { ...currentPreset, hooks: updatedHooks };
      await savePreset(updatedPreset);
      setPresets(presets.map((p) => (p.id === currentPreset.id ? updatedPreset : p)));
      showSuccess('Hook removed.');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete hook');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setLoading(true);
      setError(null);
      await uploadPresetsJsonFile(file, false);
      showSuccess(`Uploaded and imported hooks from "${file.name}"!`);
      await loadPresets();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload JSON file');
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleExportJson = async () => {
    try {
      const blob = await exportPresetsJson();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'content_presets.json';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      showSuccess('Exported presets to content_presets.json!');
    } catch (err: any) {
      setError('Failed to export presets JSON');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                Niche Preset & 31-Day Hook Manager
                <span className="text-xs font-normal px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  Auto-Rotation
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Manage universal hooks and titles for each category. Rotates 31+ unique titles monthly to prevent YouTube spam filtering.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Notifications */}
        {error && (
          <div className="mx-6 mt-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        {successMsg && (
          <div className="mx-6 mt-4 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Main Content Layout */}
        <div className="flex-1 overflow-hidden grid grid-cols-1 md:grid-cols-3 gap-0 divide-y md:divide-y-0 md:divide-x divide-slate-800">
          {/* Left Column: Preset Categories */}
          <div className="p-4 space-y-3 bg-slate-950/30 overflow-y-auto">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5" /> Categories
              </span>
              <span className="text-[10px] text-slate-500">{presets.length} active</span>
            </div>

            <div className="space-y-1.5">
              {presets.map((preset) => {
                const isSelected = preset.id === selectedPresetId;
                return (
                  <button
                    key={preset.id}
                    onClick={() => setSelectedPresetId(preset.id)}
                    className={`w-full text-left p-3 rounded-xl transition cursor-pointer flex flex-col gap-1 border ${
                      isSelected
                        ? 'bg-red-500/15 border-red-500/30 text-white shadow-sm'
                        : 'bg-slate-900/50 hover:bg-slate-800/60 border-slate-800 text-slate-300'
                    }`}
                  >
                    <div className="text-xs font-semibold">{preset.name}</div>
                    <div className="text-[11px] text-slate-400 flex items-center gap-2">
                      <span>{preset.hooks?.length || 0} hooks</span>
                      <span>•</span>
                      <span>{preset.category_name || 'Category'}</span>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Quick Actions (Import JSON, Export JSON) */}
            <div className="pt-4 mt-4 border-t border-slate-800 space-y-2">
              <div className="text-[11px] font-semibold text-slate-400 flex items-center gap-1">
                <FileJson className="w-3.5 h-3.5 text-blue-400" /> JSON Import / Export
              </div>

              <input
                type="file"
                ref={fileInputRef}
                accept=".json"
                onChange={handleFileUpload}
                className="hidden"
              />

              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 rounded-lg text-xs font-medium transition cursor-pointer"
              >
                <Upload className="w-3.5 h-3.5" />
                Upload JSON File
              </button>

              <button
                onClick={handleExportJson}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-medium transition cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                Export JSON Backup
              </button>
            </div>
          </div>

          {/* Right Column: Active Category Hooks List */}
          <div className="md:col-span-2 p-5 space-y-4 overflow-y-auto flex flex-col">
            {currentPreset ? (
              <>
                {/* Category Header Card */}
                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-white">{currentPreset.name}</h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {currentPreset.hooks?.length || 0} unique hooks configured (31-day cycle with auto-reset)
                      </p>
                    </div>
                    {onSelectPreset && (
                      <button
                        onClick={() => {
                          onSelectPreset(currentPreset);
                          onClose();
                        }}
                        className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-medium transition cursor-pointer shadow"
                      >
                        Use in Schedule
                      </button>
                    )}
                  </div>
                </div>

                {/* Add Hook Input */}
                {!isBulkAdding ? (
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newHookText}
                      onChange={(e) => setNewHookText(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleAddSingleHook()}
                      placeholder="Add a new universal hook/title (e.g. 🔱 हर हर महादेव 🙏 #shorts)"
                      className="flex-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-red-500"
                    />
                    <button
                      onClick={handleAddSingleHook}
                      disabled={!newHookText.trim()}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-medium transition cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
                    >
                      <Plus className="w-3.5 h-3.5" /> Add
                    </button>
                    <button
                      onClick={() => setIsBulkAdding(true)}
                      className="px-3 py-2 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 rounded-lg text-xs transition cursor-pointer"
                    >
                      Bulk Paste
                    </button>
                  </div>
                ) : (
                  <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span>Paste multiple hooks (one per line):</span>
                      <button
                        onClick={() => setIsBulkAdding(false)}
                        className="text-slate-500 hover:text-slate-300 text-[11px]"
                      >
                        Cancel
                      </button>
                    </div>
                    <textarea
                      rows={4}
                      value={bulkHooksText}
                      onChange={(e) => setBulkHooksText(e.target.value)}
                      placeholder="Hook line 1 #shorts&#10;Hook line 2 #shorts&#10;Hook line 3 #shorts"
                      className="w-full p-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-red-500 font-mono"
                    />
                    <button
                      onClick={handleBulkAddHooks}
                      disabled={!bulkHooksText.trim()}
                      className="px-4 py-1.5 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-medium transition cursor-pointer disabled:opacity-50"
                    >
                      Import Lines
                    </button>
                  </div>
                )}

                {/* Hooks List */}
                <div className="flex-1 space-y-2">
                  <div className="text-xs font-semibold text-slate-400 flex items-center justify-between">
                    <span>Active Rotation Hooks:</span>
                    <span className="text-[11px] text-slate-500">Day 1 to Day {currentPreset.hooks?.length || 0}</span>
                  </div>

                  <div className="space-y-1.5 max-h-[360px] overflow-y-auto pr-1">
                    {currentPreset.hooks?.map((hook, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between gap-3 text-xs text-slate-200 group hover:border-slate-700 transition"
                      >
                        <div className="flex items-center gap-2.5 overflow-hidden">
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] font-mono text-slate-400 shrink-0">
                            Day {idx + 1}
                          </span>
                          <span className="truncate">{hook}</span>
                        </div>
                        <button
                          onClick={() => handleDeleteHook(idx)}
                          className="text-slate-500 hover:text-rose-400 p-1 rounded transition opacity-0 group-hover:opacity-100 cursor-pointer"
                          title="Delete Hook"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs">
                No preset selected
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <RotateCw className="w-3.5 h-3.5 text-emerald-400" />
            <span>Rotates seamlessly 1 to 31 every month with zero duplicate title penalties.</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-medium transition cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
