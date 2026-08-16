import { apiClient } from './client';

export interface VideoItem {
  id: string;
  channel_id: string | null;
  folder_id: string | null;
  storage_provider: string;
  storage_file_id: string;
  filename: string;
  path: string;
  mime_type: string;
  size_bytes: number;
  day_of_month_index: number | null;
  enabled: boolean;
  custom_metadata: Record<string, any> | null;
  custom_thumbnail_file_id: string | null;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
  channel_name: string | null;
  folder_name: string | null;
}

export interface VideoListResponse {
  total: number;
  items: VideoItem[];
}

export interface ContentFolderItem {
  id: string;
  storage_folder_id: string;
  name: string;
  path: string;
  channel_id: string | null;
  default_title_template: string | null;
  default_description_template: string | null;
  default_tags: string[];
  default_category_id: string | null;
  default_thumbnail_storage_id: string | null;
  created_at: string;
  updated_at: string;
  videos_count: number;
  channel_name: string | null;
}

export interface MetadataPreview {
  video_id: string;
  video_filename: string;
  title: string;
  description: string;
  tags: string[];
  category_id: string;
  privacy_status: string;
  thumbnail_storage_id: string | null;
  source_hierarchy: Record<string, string>;
}

export interface VideoFilterParams {
  channel_id?: string;
  folder_id?: string;
  day_of_month?: number;
  enabled?: boolean;
  search?: string;
  skip?: number;
  limit?: number;
}

export const getVideos = async (params: VideoFilterParams = {}): Promise<VideoListResponse> => {
  const response = await apiClient.get<VideoListResponse>('/videos', { params });
  return response.data;
};

export const getVideo = async (id: string): Promise<VideoItem> => {
  const response = await apiClient.get<VideoItem>(`/videos/${id}`);
  return response.data;
};

export const toggleVideo = async (id: string): Promise<VideoItem> => {
  const response = await apiClient.patch<VideoItem>(`/videos/${id}/toggle`);
  return response.data;
};

export const updateVideo = async (id: string, data: Partial<VideoItem>): Promise<VideoItem> => {
  const response = await apiClient.put<VideoItem>(`/videos/${id}`, data);
  return response.data;
};

export const previewVideoMetadata = async (
  videoId: string,
  params: { channel_id?: string; schedule_id?: string; target_date?: string } = {}
): Promise<MetadataPreview> => {
  const response = await apiClient.post<MetadataPreview>(`/videos/${videoId}/preview-metadata`, params);
  return response.data;
};

export const getContentFolders = async (channelId?: string): Promise<ContentFolderItem[]> => {
  const response = await apiClient.get<{ total: number; items: ContentFolderItem[] }>('/folders', {
    params: { channel_id: channelId },
  });
  return response.data.items;
};

export const updateContentFolder = async (
  folderId: string,
  data: Partial<ContentFolderItem>
): Promise<ContentFolderItem> => {
  const response = await apiClient.put<ContentFolderItem>(`/folders/${folderId}`, data);
  return response.data;
};
