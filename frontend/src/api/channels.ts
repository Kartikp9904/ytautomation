import { apiClient } from './client';

export interface Channel {
  id: string;
  name: string;
  youtube_channel_id: string | null;
  timezone: string;
  enabled: boolean;
  default_title_template: string | null;
  default_description_template: string | null;
  default_tags: string[];
  default_category_id: string;
  default_privacy_status: string;
  default_thumbnail_storage_id: string | null;
  created_at: string;
  updated_at: string;
  schedules_count: number;
  videos_count: number;
  is_connected: boolean;
}

export interface ChannelInput {
  name: string;
  timezone: string;
  enabled?: boolean;
  default_title_template?: string | null;
  default_description_template?: string | null;
  default_tags?: string[];
  default_category_id?: string;
  default_privacy_status?: string;
}

export interface TimezoneOption {
  name: string;
  label: string;
  offset: string;
}

export interface ChannelListResponse {
  total: number;
  items: Channel[];
}

export const getChannels = async (): Promise<ChannelListResponse> => {
  const response = await apiClient.get<ChannelListResponse>('/channels');
  return response.data;
};

export const getTimezones = async (): Promise<TimezoneOption[]> => {
  const response = await apiClient.get<TimezoneOption[]>('/channels/timezones');
  return response.data;
};

export const createChannel = async (data: ChannelInput): Promise<Channel> => {
  const response = await apiClient.post<Channel>('/channels', data);
  return response.data;
};

export const updateChannel = async (id: string, data: Partial<ChannelInput>): Promise<Channel> => {
  const response = await apiClient.put<Channel>(`/channels/${id}`, data);
  return response.data;
};

export const toggleChannel = async (id: string): Promise<Channel> => {
  const response = await apiClient.patch<Channel>(`/channels/${id}/toggle`);
  return response.data;
};

export const deleteChannel = async (id: string): Promise<void> => {
  await apiClient.delete(`/channels/${id}`);
};
