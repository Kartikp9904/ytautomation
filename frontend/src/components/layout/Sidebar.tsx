import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Tv,
  HardDrive,
  Film,
  CalendarDays,
  Calendar,
  History,
  AlertOctagon,
  ScrollText,
  Settings,
  PlaySquare
} from 'lucide-react';

interface NavItem {
  name: string;
  path: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Channels', path: '/channels', icon: Tv },
  { name: 'Google Drive', path: '/drive', icon: HardDrive },
  { name: 'Video Library', path: '/videos', icon: Film },
  { name: 'Schedules', path: '/schedules', icon: CalendarDays },
  { name: 'Calendar', path: '/calendar', icon: Calendar },
  { name: 'Upload History', path: '/uploads', icon: History },
  { name: 'Failed Jobs', path: '/failed-jobs', icon: AlertOctagon },
  { name: 'System Logs', path: '/logs', icon: ScrollText },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-slate-900/90 backdrop-blur border-r border-slate-800 flex flex-col h-screen sticky top-0">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-slate-800 gap-3">
        <div className="p-2 bg-red-600/20 text-red-500 rounded-lg border border-red-500/30">
          <PlaySquare className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-bold text-sm tracking-tight text-white">YT Studio Auto</h1>
          <p className="text-[11px] text-slate-400 font-medium">Self-Hosted Scheduler</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 overflow-y-auto p-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-red-600/15 text-red-400 border border-red-500/30 font-semibold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`
            }
          >
            <item.icon className="w-4 h-4 shrink-0" />
            <span>{item.name}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer / Version Badge */}
      <div className="p-4 border-t border-slate-800/80 text-xs text-slate-500 flex items-center justify-between">
        <span>v1.0.0 (Phase 1)</span>
        <span className="flex items-center gap-1.5 text-emerald-400 text-[11px] font-medium">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          Ready
        </span>
      </div>
    </aside>
  );
};
