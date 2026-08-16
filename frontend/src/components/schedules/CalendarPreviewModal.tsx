import React, { useState, useEffect } from 'react';
import type { ScheduleItem, CalendarSimulationResponse, CalendarDaySimulationItem } from '../../api/schedules';
import { simulateScheduleCalendar } from '../../api/schedules';
import { 
  X, 
  Calendar, 
  CheckCircle2, 
  AlertTriangle, 
  HelpCircle, 
  Film, 
  ChevronLeft, 
  ChevronRight, 
  Clock
} from 'lucide-react';

interface CalendarPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  schedule: ScheduleItem | null;
}

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

export const CalendarPreviewModal: React.FC<CalendarPreviewModalProps> = ({
  isOpen,
  onClose,
  schedule,
}) => {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1); // 1-12
  const [simulation, setSimulation] = useState<CalendarSimulationResponse | null>(null);
  const [selectedDay, setSelectedDay] = useState<CalendarDaySimulationItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSimulation = async () => {
    if (!schedule) return;
    try {
      setLoading(true);
      setError(null);
      const data = await simulateScheduleCalendar(schedule.id, year, month);
      setSimulation(data);
      if (data.days.length > 0) {
        setSelectedDay(data.days[0]);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to simulate calendar');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && schedule) {
      loadSimulation();
    }
  }, [isOpen, schedule, year, month]);

  if (!isOpen || !schedule) return null;

  const handlePrevMonth = () => {
    if (month === 1) {
      setMonth(12);
      setYear(year - 1);
    } else {
      setMonth(month - 1);
    }
  };

  const handleNextMonth = () => {
    if (month === 12) {
      setMonth(1);
      setYear(year + 1);
    } else {
      setMonth(month + 1);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/80">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-600/20 text-red-400 border border-red-500/30">
              <Calendar className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">
                Day-of-Month Calendar Simulator
              </h3>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                {schedule.name} ({schedule.channel_name})
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Month Selector Bar */}
        <div className="px-6 py-3 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrevMonth}
              className="p-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-300 transition cursor-pointer border border-slate-800"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-bold text-white text-sm">
              {MONTH_NAMES[month - 1]} {year}
            </span>
            <button
              onClick={handleNextMonth}
              className="p-1 rounded bg-slate-900 hover:bg-slate-800 text-slate-300 transition cursor-pointer border border-slate-800"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center gap-3">
            {simulation && (
              <span className="px-2.5 py-1 rounded-full text-[11px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
                {simulation.days_in_month} Days {simulation.is_leap_year && '• Leap Year (29 Feb)'}
              </span>
            )}
          </div>
        </div>

        {/* Main Body */}
        <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6 max-h-[75vh] overflow-y-auto">
          {/* Calendar Grid */}
          <div className="lg:col-span-2 space-y-3">
            {error && (
              <div className="p-3.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-medium">
                {error}
              </div>
            )}

            {loading ? (
              <div className="py-24 flex flex-col items-center justify-center space-y-3">
                <div className="w-6 h-6 border-2 border-red-500/20 border-t-red-500 rounded-full animate-spin"></div>
                <span className="text-xs text-slate-400">Simulating monthly day-mapping...</span>
              </div>
            ) : simulation ? (
              <div>
                <div className="grid grid-cols-7 gap-2">
                  {simulation.days.map((d) => (
                    <div
                      key={d.day_number}
                      onClick={() => setSelectedDay(d)}
                      className={`p-2.5 rounded-xl border transition cursor-pointer flex flex-col justify-between min-h-[70px] ${
                        selectedDay?.day_number === d.day_number
                          ? 'border-red-500 ring-2 ring-red-500/30 bg-slate-900'
                          : d.is_matched
                          ? 'bg-emerald-500/10 border-emerald-500/20 hover:border-emerald-500/50'
                          : d.is_fallback
                          ? 'bg-amber-500/10 border-amber-500/20 hover:border-amber-500/50'
                          : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-white font-mono">{d.day_number}</span>
                        {d.is_matched ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        ) : d.is_fallback ? (
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                        ) : (
                          <HelpCircle className="w-3.5 h-3.5 text-slate-600" />
                        )}
                      </div>

                      <div className="text-[10px] font-mono truncate text-slate-300 mt-1">
                        {d.video_filename || 'No video'}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Calendar Legend */}
                <div className="pt-4 flex flex-wrap items-center gap-4 text-[11px] text-slate-400">
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
                    <span>Matched Day Video ({simulation.days.filter((d) => d.is_matched).length})</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                    <span>Fallback Video ({simulation.days.filter((d) => d.is_fallback).length})</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-slate-600"></span>
                    <span>Missing ({simulation.days.filter((d) => !d.is_matched && !d.is_fallback).length})</span>
                  </div>
                </div>
              </div>
            ) : null}
          </div>

          {/* Day Inspector Panel */}
          <div className="p-5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Film className="w-3.5 h-3.5 text-red-400" /> Day Inspector
            </h4>

            {selectedDay ? (
              <div className="space-y-4 text-xs">
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                  <div className="text-slate-400">Selected Date:</div>
                  <div className="text-sm font-bold text-white font-mono">
                    {selectedDay.date} (Day #{selectedDay.day_number})
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-slate-400">Mapped Video:</div>
                  <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 font-mono text-xs">
                    {selectedDay.video_filename || 'None (Upload would fail or skip)'}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <div className="text-slate-400">Match Status:</div>
                  {selectedDay.is_matched ? (
                    <div className="p-2.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-semibold flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 shrink-0" /> Exact Day Match
                    </div>
                  ) : selectedDay.is_fallback ? (
                    <div className="p-2.5 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-300 font-semibold space-y-1">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 shrink-0" /> Fallback Triggered
                      </div>
                      <p className="text-[10px] text-amber-400/80 font-normal">
                        {selectedDay.fallback_reason}
                      </p>
                    </div>
                  ) : (
                    <div className="p-2.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-300 font-semibold space-y-1">
                      <div className="flex items-center gap-2">
                        <HelpCircle className="w-4 h-4 shrink-0" /> Missing Asset
                      </div>
                      <p className="text-[10px] text-rose-400/80 font-normal">
                        {selectedDay.fallback_reason}
                      </p>
                    </div>
                  )}
                </div>

                <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-500 space-y-1">
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3 h-3" /> Scheduled Publish Time: {schedule.publish_time} ({schedule.timezone})
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-xs text-slate-500">
                Click any day in the calendar to inspect video mapping.
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-900/80 flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition cursor-pointer"
          >
            Close Simulator
          </button>
        </div>
      </div>
    </div>
  );
};
