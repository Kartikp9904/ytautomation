import React, { useEffect, useState } from 'react';
import { 
  getCalendarEvents, 
  getSchedules, 
  simulateScheduleCalendar,
  type CalendarEventItem, 
  type ScheduleItem, 
  type CalendarDaySimulationItem 
} from '../api/schedules';
import { getChannels, type Channel } from '../api/channels';
import { 
  Calendar as CalendarIcon, 
  ChevronLeft, 
  ChevronRight, 
  Play, 
  Sparkles, 
  Tv, 
  ExternalLink
} from 'lucide-react';

export const CalendarPage: React.FC = () => {
  const [currentDate, setCurrentDate] = useState<Date>(new Date());
  const [channels, setChannels] = useState<Channel[]>([]);
  const [schedules, setSchedules] = useState<ScheduleItem[]>([]);
  const [selectedChannelId, setSelectedChannelId] = useState<string>('');
  const [events, setEvents] = useState<CalendarEventItem[]>([]);
  
  // Dry run simulation states
  const [selectedSimScheduleId, setSelectedSimScheduleId] = useState<string>('');
  const [simResults, setSimResults] = useState<CalendarDaySimulationItem[] | null>(null);
  const [simulating, setSimulating] = useState<boolean>(false);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth() + 1;

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  useEffect(() => {
    getChannels().then((data) => setChannels(data.items)).catch(() => {});
    getSchedules().then((data) => setSchedules(data)).catch(() => {});
  }, []);

  const loadEvents = async () => {
    try {
      const data = await getCalendarEvents(year, month, selectedChannelId || undefined);
      setEvents(data);
    } catch {
      // Ignored
    }
  };

  useEffect(() => {
    loadEvents();
    setSimResults(null);
  }, [year, month, selectedChannelId]);

  const handlePrevMonth = () => {
    setCurrentDate(new Date(year, month - 2, 1));
  };

  const handleNextMonth = () => {
    setCurrentDate(new Date(year, month, 1));
  };

  const handleToday = () => {
    setCurrentDate(new Date());
  };

  const handleRunSimulation = async () => {
    if (!selectedSimScheduleId) return;
    try {
      setSimulating(true);
      const res = await simulateScheduleCalendar(selectedSimScheduleId, year, month);
      setSimResults(res.days);
    } catch (err: any) {
      alert(err.message || 'Simulation failed');
    } finally {
      setSimulating(false);
    }
  };

  // Calendar Grid Calculations
  const firstDayIndex = new Date(year, month - 1, 1).getDay(); // 0 is Sun
  const adjustedFirstDay = (firstDayIndex + 6) % 7; // 0 is Mon
  const daysInCurrentMonth = new Date(year, month, 0).getDate();

  const daysArray = Array.from({ length: daysInCurrentMonth }, (_, i) => i + 1);
  const leadingBlanks = Array.from({ length: adjustedFirstDay }, (_, i) => i);

  const getModeBadge = (mode: string) => {
    switch (mode) {
      case 'DAY_OF_MONTH':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">DOM</span>;
      case 'ROTATION':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">ROT</span>;
      case 'SHUFFLE':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">SHUF</span>;
      case 'REPEAT':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">REP</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400">PUB</span>;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <CalendarIcon className="w-6 h-6 text-red-500" />
            Publication Calendar & Simulator
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Visual month planner, scheduled premiere triggers, and dry-run calendar projection.
          </p>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Channel Filter */}
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-xs">
            <Tv className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedChannelId}
              onChange={(e) => setSelectedChannelId(e.target.value)}
              className="bg-transparent text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="" className="bg-slate-900 text-slate-200">All Channels</option>
              {channels.map((c) => (
                <option key={c.id} value={c.id} className="bg-slate-900 text-slate-200">
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          {/* Month Navigation */}
          <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-xl p-1">
            <button
              onClick={handlePrevMonth}
              title="Previous Month"
              className="p-1.5 hover:bg-slate-800 text-slate-300 rounded-lg transition cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-3 text-xs font-semibold text-white font-mono">
              {monthNames[month - 1]} {year}
            </span>
            <button
              onClick={handleNextMonth}
              title="Next Month"
              className="p-1.5 hover:bg-slate-800 text-slate-300 rounded-lg transition cursor-pointer"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <button
            onClick={handleToday}
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-medium border border-slate-700 transition cursor-pointer"
          >
            Today
          </button>
        </div>
      </div>

      {/* Simulator Bar */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row md:items-center md:justify-between gap-4 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-white">Dry-Run Calendar Simulator</h4>
            <p className="text-[11px] text-slate-400">
              Preview scheduled video assignments and leap year fallbacks without making YouTube API calls.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={selectedSimScheduleId}
            onChange={(e) => setSelectedSimScheduleId(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-200 rounded-xl px-3 py-1.5 text-xs focus:outline-none focus:border-red-500"
          >
            <option value="">Select a Schedule to Simulate...</option>
            {schedules.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.mode})
              </option>
            ))}
          </select>

          <button
            onClick={handleRunSimulation}
            disabled={!selectedSimScheduleId || simulating}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-900/20 transition disabled:opacity-50 cursor-pointer"
          >
            <Play className="w-3 h-3" />
            {simulating ? 'Simulating...' : 'Simulate Month'}
          </button>

          {simResults && (
            <button
              onClick={() => setSimResults(null)}
              className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded-xl text-xs transition cursor-pointer"
            >
              Clear Sim
            </button>
          )}
        </div>
      </div>

      {/* Simulation Active Notice */}
      {simResults && (
        <div className="p-3 rounded-xl bg-indigo-950/40 border border-indigo-500/30 text-xs text-indigo-200 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            Displaying simulated calendar plan for <strong>{monthNames[month - 1]} {year}</strong> (
            {simResults.filter((d) => d.is_matched).length} days matched,{' '}
            {simResults.filter((d) => d.is_fallback).length} fallbacks applied).
          </span>
        </div>
      )}

      {/* 7-Day Grid Headers */}
      <div className="grid grid-cols-7 gap-2 text-center text-xs font-bold text-slate-400 tracking-wider">
        <div>MON</div>
        <div>TUE</div>
        <div>WED</div>
        <div>THU</div>
        <div>FRI</div>
        <div>SAT</div>
        <div>SUN</div>
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-7 gap-2">
        {/* Leading blanks */}
        {leadingBlanks.map((b) => (
          <div key={`blank-${b}`} className="min-h-[110px] rounded-2xl bg-slate-950/30 border border-slate-900/50 p-2" />
        ))}

        {/* Days */}
        {daysArray.map((day) => {
          const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
          const isToday =
            new Date().toDateString() === new Date(year, month - 1, day).toDateString();
          
          const dayEvents = events.filter((e) => e.date === dateStr);
          const simDay = simResults?.find((s) => s.day_number === day);

          return (
            <div
              key={`day-${day}`}
              className={`min-h-[110px] rounded-2xl p-2.5 flex flex-col justify-between transition border ${
                isToday
                  ? 'bg-slate-900/90 border-red-500/60 shadow-lg shadow-red-950/20'
                  : 'bg-slate-900/50 border-slate-800/80 hover:border-slate-700/80'
              }`}
            >
              {/* Day Header */}
              <div className="flex items-center justify-between">
                <span
                  className={`text-xs font-bold font-mono ${
                    isToday ? 'text-red-400 px-1.5 py-0.5 rounded-md bg-red-500/10' : 'text-slate-300'
                  }`}
                >
                  {day}
                </span>

                {isToday && (
                  <span className="text-[10px] font-bold uppercase tracking-wider text-red-400">
                    Today
                  </span>
                )}
              </div>

              {/* Events & Simulated Events in Cell */}
              <div className="space-y-1.5 my-1 overflow-y-auto max-h-[80px]">
                {/* Real Scheduled Occurrences */}
                {dayEvents.map((evt) => (
                  <div
                    key={evt.id}
                    className="p-1.5 rounded-lg bg-slate-800/90 border border-slate-700/60 text-[11px] text-slate-200 space-y-0.5 shadow-sm"
                  >
                    <div className="flex items-center justify-between gap-1">
                      {getModeBadge(evt.mode)}
                      <span className="font-mono text-[10px] text-slate-400">{evt.publish_time}</span>
                    </div>

                    <div className="font-semibold truncate text-white" title={evt.title}>
                      {evt.title}
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-slate-400">
                      <span className="truncate max-w-[70px]">{evt.channel_name}</span>
                      {evt.youtube_url && (
                        <a
                          href={evt.youtube_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-red-400 hover:text-red-300"
                        >
                          <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      )}
                    </div>
                  </div>
                ))}

                {/* Simulated Overlay */}
                {simDay && (
                  <div
                    className={`p-1.5 rounded-lg text-[11px] border space-y-0.5 ${
                      simDay.is_matched
                        ? 'bg-indigo-950/60 border-indigo-500/40 text-indigo-200'
                        : 'bg-slate-950/60 border-dashed border-slate-800 text-slate-500'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold text-indigo-400">SIMULATED</span>
                      {simDay.is_fallback && (
                        <span className="text-[9px] font-bold px-1 bg-amber-500/20 text-amber-300 rounded">
                          Fallback
                        </span>
                      )}
                    </div>
                    <div className="font-medium truncate text-slate-200" title={simDay.video_filename || 'No video'}>
                      {simDay.video_filename || 'No Video Match'}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
