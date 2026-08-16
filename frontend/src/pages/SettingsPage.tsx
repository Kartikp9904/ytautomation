import React from 'react';
import { Shield, Key } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="pb-6 border-b border-slate-800">
        <h2 className="text-2xl font-bold text-white tracking-tight">System Settings</h2>
        <p className="text-sm text-slate-400 mt-1">
          Configure global Google OAuth credentials, default storage paths, and scheduler behavior.
        </p>
      </div>

      <div className="space-y-6">
        {/* Google OAuth Credentials */}
        <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center gap-3">
            <Key className="w-5 h-5 text-amber-400" />
            <div>
              <h3 className="font-semibold text-white text-sm">Google Cloud Application Credentials</h3>
              <p className="text-xs text-slate-400">OAuth 2.0 Web Application credentials from Google Cloud Console</p>
            </div>
          </div>

          <div className="space-y-3 pt-2">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Google Client ID</label>
              <input
                type="text"
                placeholder="apps.googleusercontent.com"
                className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-red-500 font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Google Client Secret</label>
              <input
                type="password"
                placeholder="••••••••••••••••••••••••"
                className="w-full px-3.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-red-500 font-mono"
              />
            </div>
          </div>
        </div>

        {/* Security & Token Storage */}
        <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center gap-3">
            <Shield className="w-5 h-5 text-emerald-400" />
            <div>
              <h3 className="font-semibold text-white text-sm">Security & Encryption</h3>
              <p className="text-xs text-slate-400">OAuth tokens are encrypted at rest using AES-256-GCM.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
