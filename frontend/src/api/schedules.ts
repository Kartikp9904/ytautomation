import { apiClient } from './client';

export interface ScheduleItem {
  id: string;
  channel_id: string;
  name: string;
  schedule_type: string; // DAILY, WEEKLY, MONTHLY, ONE_TIME
  source_type: string;   // FOLDER, VIDEO
  source_id: string;
  mode: string;          // DAY_OF_MONTH, REPEAT, ROTATION, SHUFFLE, SINGLE_VIDEO
  publish_time: string;  // "09:00"
  timezone: string;
  upload_lead_minutes: number;
  use_youtube_scheduled_publish: boolean;
  dry_run: boolean;
  days_of_week: string[];
  day_of_month: number | null;
  repeat_interval_days: number | null;
  enabled: boolean;
  title_template: string | null;
  description_template: string | null;
  tags: string[];
  category_id: string | null;
  privacy_status: string;
  made_for_kids?: boolean;
  age_restricted?: boolean;
  default_language?: string | null;
  default_audio_language?: string | null;
  contains_synthetic_media?: boolean;
  preset_category?: string | null;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
  next_run_time: string | null;
  channel_name: string | null;
  source_name: string | null;
  current_rotation_index?: number | null;
  total_rotation_videos?: number | null;
  shuffle_remaining_count?: number | null;
  shuffle_used_count?: number | null;
  shuffle_cycle?: number | null;
}

export interface ScheduleOccurrenceItem {
  id: string;
  schedule_id: string;
  channel_id: string;
  video_id: string | null;
  scheduled_publish_time: string;
  target_upload_time: string;
  status: string;
  dry_run: boolean;
  youtube_video_id?: string | null;
  idempotency_key: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface CalendarDaySimulationItem {
  date: string;
  day_number: number;
  video_id: string | null;
  video_filename: string | null;
  is_matched: boolean;
  is_fallback: boolean;
  fallback_reason: string | null;
  is_leap_year: boolean;
  days_in_month: number;
}

export interface CalendarSimulationResponse {
  schedule_id: string;
  year: number;
  month: number;
  days_in_month: number;
  is_leap_year: boolean;
  days: CalendarDaySimulationItem[];
}

export interface TimelineItem {
  id: string;
  schedule_id: string | null;
  schedule_name: string | null;
  channel_name: string;
  channel_id: string;
  video_title: string;
  scheduled_publish_time: string;
  target_upload_time: string;
  status: string;
  dry_run: boolean;
  youtube_video_id: string | null;
  youtube_url: string | null;
}

export interface CalendarEventItem {
  id: string;
  date: string; // YYYY-MM-DD
  title: string;
  schedule_name: string;
  channel_name: string;
  mode: string;
  publish_time: string;
  status: string;
  dry_run: boolean;
  youtube_url: string | null;
}

export interface ScheduleCreateData {
  channel_id: string;
  name: string;
  schedule_type: string;
  source_type: string;
  source_id: string;
  mode: string;
  publish_time: string;
  timezone?: string;
  upload_lead_minutes?: number;
  use_youtube_scheduled_publish?: boolean;
  dry_run?: boolean;
  days_of_week?: string[];
  day_of_month?: number;
  repeat_interval_days?: number;
  enabled?: boolean;
  title_template?: string;
  description_template?: string;
  tags?: string[];
  category_id?: string;
  privacy_status?: string;
  made_for_kids?: boolean;
  age_restricted?: boolean;
  default_language?: string;
  default_audio_language?: string;
  contains_synthetic_media?: boolean;
  preset_category?: string;
}

export interface ScheduleFilterParams {
  channel_id?: string;
  enabled?: boolean;
  mode?: string;
  schedule_type?: string;
}

export const getSchedules = async (params: ScheduleFilterParams = {}): Promise<ScheduleItem[]> => {
  const response = await apiClient.get<{ total: number; items: ScheduleItem[] }>('/schedules', { params });
  return response.data.items;
};

export const getSchedule = async (id: string): Promise<ScheduleItem> => {
  const response = await apiClient.get<ScheduleItem>(`/schedules/${id}`);
  return response.data;
};

export const createSchedule = async (data: ScheduleCreateData): Promise<ScheduleItem> => {
  const response = await apiClient.post<ScheduleItem>('/schedules', data);
  return response.data;
};

export const updateSchedule = async (id: string, data: Partial<ScheduleCreateData>): Promise<ScheduleItem> => {
  const response = await apiClient.put<ScheduleItem>(`/schedules/${id}`, data);
  return response.data;
};

export const toggleSchedule = async (id: string): Promise<ScheduleItem> => {
  const response = await apiClient.patch<ScheduleItem>(`/schedules/${id}/toggle`);
  return response.data;
};

export const deleteSchedule = async (id: string): Promise<void> => {
  await apiClient.delete(`/schedules/${id}`);
};

export const triggerScheduleNow = async (id: string): Promise<{ message: string; occurrence_id: string; status: string }> => {
  const response = await apiClient.post(`/schedules/${id}/trigger-now`);
  return response.data;
};

export const resetRotationIndex = async (id: string, index: number = 0): Promise<{ message: string; current_index: number }> => {
  const response = await apiClient.post<{ message: string; current_index: number }>(
    `/schedules/${id}/reset-rotation`,
    null,
    { params: { index } }
  );
  return response.data;
};

export const reshufflePool = async (id: string): Promise<{ message: string; total_shuffled: number; current_cycle: number }> => {
  const response = await apiClient.post<{ message: string; total_shuffled: number; current_cycle: number }>(
    `/schedules/${id}/reshuffle`
  );
  return response.data;
};

export const getScheduleOccurrences = async (id: string): Promise<ScheduleOccurrenceItem[]> => {
  const response = await apiClient.get<ScheduleOccurrenceItem[]>(`/schedules/${id}/occurrences`);
  return response.data;
};

export const simulateScheduleCalendar = async (
  scheduleId: string,
  year: number,
  month: number
): Promise<CalendarSimulationResponse> => {
  const response = await apiClient.post<CalendarSimulationResponse>(
    `/schedules/${scheduleId}/simulate-calendar`,
    null,
    { params: { year, month } }
  );
  return response.data;
};

export const getTodayTimeline = async (): Promise<TimelineItem[]> => {
  const response = await apiClient.get<TimelineItem[]>('/schedules/timeline/today');
  return response.data;
};

export const getCalendarEvents = async (
  year: number,
  month: number,
  channelId?: string
): Promise<CalendarEventItem[]> => {
  const response = await apiClient.get<CalendarEventItem[]>('/schedules/calendar/events', {
    params: { year, month, channel_id: channelId || undefined }
  });
  return response.data;
};
