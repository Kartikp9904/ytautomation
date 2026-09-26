import { apiClient } from './client';

export interface SourceChannelSync {
  id: string;
  source_channel_url: string;
  source_channel_name?: string;
  source_channel_id?: string;
  target_channel_id: string;
  target_channel_name?: string;
  sync_mode: string; // ALL, SHORTS_ONLY, FULL_VIDEOS_ONLY
  auto_publish: boolean;
  publish_privacy_status: string; // public, unlisted, private
  publish_mode: string; // SCHEDULED, IMMEDIATE, MANUAL
  daily_publish_count: number;
  publish_time_slots: string[];
  timezone: string;
  max_video_size_mb: number;
  last_scheduled_slot_published?: string;
  title_prefix?: string;
  title_suffix?: string;
  description_footer?: string;
  custom_tags?: string[];
  enabled: boolean;
  last_synced_at?: string;
  last_error?: string;
  videos_synced_count?: number;
  videos_uploaded_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface SourceChannelSyncInput {
  source_channel_url: string;
  target_channel_id: string;
  sync_mode?: string;
  auto_publish?: boolean;
  publish_privacy_status?: string;
  publish_mode?: string;
  daily_publish_count?: number;
  publish_time_slots?: string[];
  timezone?: string;
  max_video_size_mb?: number;
  title_prefix?: string;
  title_suffix?: string;
  description_footer?: string;
  custom_tags?: string[];
  enabled?: boolean;
}

export interface SyncedSourceVideo {
  id: string;
  sync_id: string;
  source_video_id: string;
  source_url: string;
  title: string;
  description?: string;
  tags?: string[];
  category_id?: string;
  thumbnail_url?: string;
  duration_seconds?: number;
  is_short: boolean;
  download_status: string; // PENDING, DOWNLOADING, DOWNLOADED, FAILED
  upload_status: string; // PENDING, UPLOADING, UPLOADED, SKIPPED, FAILED
  uploaded_youtube_video_id?: string;
  uploaded_youtube_url?: string;
  error_message?: string;
  published_at_source?: string;
  created_at?: string;
}

export interface SyncTriggerResult {
  success: boolean;
  message: string;
  videos_found: number;
  videos_downloaded: number;
  videos_uploaded: number;
}

export const getSyncConfigs = async (): Promise<SourceChannelSync[]> => {
  const response = await apiClient.get<SourceChannelSync[]>('/channel-sync');
  return response.data;
};

export const createSyncConfig = async (data: SourceChannelSyncInput): Promise<SourceChannelSync> => {
  const response = await apiClient.post<SourceChannelSync>('/channel-sync', data);
  return response.data;
};

export const updateSyncConfig = async (id: string, data: Partial<SourceChannelSyncInput>): Promise<SourceChannelSync> => {
  const response = await apiClient.put<SourceChannelSync>(`/channel-sync/${id}`, data);
  return response.data;
};

export const deleteSyncConfig = async (id: string): Promise<void> => {
  await apiClient.delete(`/channel-sync/${id}`);
};

export const triggerChannelSync = async (id: string, maxVideos: number = 5): Promise<SyncTriggerResult> => {
  const response = await apiClient.post<SyncTriggerResult>(`/channel-sync/${id}/trigger?max_videos=${maxVideos}`);
  return response.data;
};

export const getSyncedVideos = async (syncId?: string): Promise<SyncedSourceVideo[]> => {
  const url = syncId ? `/channel-sync/videos?sync_id=${syncId}` : '/channel-sync/videos';
  const response = await apiClient.get<SyncedSourceVideo[]>(url);
  return response.data;
};

export const uploadSingleSyncedVideo = async (videoId: string): Promise<SyncedSourceVideo> => {
  const response = await apiClient.post<SyncedSourceVideo>(`/channel-sync/videos/${videoId}/upload`);
  return response.data;
};

export interface CookieStatusResponse {
  has_cookies: boolean;
  source?: string;
  file_path?: string;
  updated_at?: string;
  size_bytes?: number;
}

export const getCookiesStatus = async (): Promise<CookieStatusResponse> => {
  const response = await apiClient.get<CookieStatusResponse>('/channel-sync/cookies/status');
  return response.data;
};

export const saveCookies = async (cookies: string): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.post<{ success: boolean; message: string }>('/channel-sync/cookies', { cookies });
  return response.data;
};

export const deleteCookies = async (): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.delete<{ success: boolean; message: string }>('/channel-sync/cookies');
  return response.data;
};

