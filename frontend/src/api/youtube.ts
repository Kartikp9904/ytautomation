import { apiClient } from './client';

export interface YouTubeConnectionStatus {
  channel_id: string;
  channel_name: string;
  is_connected: boolean;
  youtube_channel_id: string | null;
  account_email: string | null;
  token_expiry: string | null;
  daily_quota_used: number;
  daily_quota_limit: number;
  last_error: string | null;
}

export const getYouTubeAuthUrl = async (channelId: string): Promise<{ auth_url: string }> => {
  const response = await apiClient.get<{ auth_url: string }>('/youtube/auth-url', {
    params: { channel_id: channelId },
  });
  return response.data;
};

export const getYouTubeConnectionStatus = async (channelId: string): Promise<YouTubeConnectionStatus> => {
  const response = await apiClient.get<YouTubeConnectionStatus>(`/youtube/${channelId}/status`);
  return response.data;
};

export const disconnectYouTubeChannel = async (channelId: string): Promise<{ message: string }> => {
  const response = await apiClient.post<{ message: string }>(`/youtube/${channelId}/disconnect`);
  return response.data;
};

export interface CopyrightAuditSummary {
  total_audited: number;
  flagged_and_replaced: number;
  clean_count: number;
  results: Array<{
    status: string;
    occurrence_id?: string;
    youtube_video_id?: string;
    reason?: string;
    action_result?: any;
    inspection?: any;
  }>;
}

export const auditCopyright = async (channelId?: string, limit = 20): Promise<CopyrightAuditSummary> => {
  const response = await apiClient.post<CopyrightAuditSummary>('/youtube/audit-copyright', null, {
    params: { channel_id: channelId || undefined, limit },
  });
  return response.data;
};

export const auditSingleOccurrence = async (occurrenceId: string): Promise<any> => {
  const response = await apiClient.post(`/youtube/occurrences/${occurrenceId}/audit`);
  return response.data;
};

export const deleteAndReplaceOccurrence = async (
  occurrenceId: string,
  reason = 'Manual Deletion',
  autoReplace = true
): Promise<any> => {
  const response = await apiClient.post(
    `/youtube/occurrences/${occurrenceId}/delete-and-replace`,
    null,
    {
      params: { reason, auto_replace: autoReplace },
    }
  );
  return response.data;
};
