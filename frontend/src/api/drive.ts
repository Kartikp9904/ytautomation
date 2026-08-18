import { apiClient } from './client';

export interface DriveStatus {
  connected: boolean;
  account_email: string | null;
  has_credentials: boolean;
  token_expiry: string | null;
  last_error: string | null;
  storage_provider: string;
}

export interface DriveFolderItem {
  id: string;
  name: string;
  path: string;
  parent_id: string | null;
  modified_time: string | null;
}

export interface ScanSummary {
  root_id: string;
  folders_found: number;
  videos_found: number;
  sidecar_json_found: number;
  thumbnails_found: number;
  errors: string[];
}

export const getDriveStatus = async (): Promise<DriveStatus> => {
  const response = await apiClient.get<DriveStatus>('/drive/status');
  return response.data;
};

export const getDriveAuthUrl = async (): Promise<string> => {
  const response = await apiClient.get<{ auth_url: string }>('/drive/auth-url');
  return response.data.auth_url;
};

export const disconnectDrive = async (): Promise<void> => {
  await apiClient.post('/drive/disconnect');
};

export const getFolders = async (parentId?: string, providerName?: string): Promise<DriveFolderItem[]> => {
  const response = await apiClient.get<DriveFolderItem[]>('/drive/folders', {
    params: { parent_id: parentId, provider_name: providerName },
  });
  return response.data;
};

export const triggerScan = async (
  rootFolderId?: string,
  channelId?: string,
  provider?: string
): Promise<ScanSummary> => {
  const response = await apiClient.post<ScanSummary>(
    '/drive/scan',
    {
      root_folder_id: rootFolderId,
      channel_id: channelId,
      provider,
    },
    {
      timeout: 300000, // 5 minutes for large drive scans
    }
  );
  return response.data;
};

export const createSampleLocalData = async (): Promise<{
  message: string;
  base_path: string;
  total_files_created: number;
  structure: string[];
}> => {
  const response = await apiClient.post('/drive/create-sample-data');
  return response.data;
};
