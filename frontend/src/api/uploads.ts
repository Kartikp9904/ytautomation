import { apiClient } from './client';

export interface ManualUploadRequest {
  video_id: string;
  channel_id: string;
  title?: string;
  description?: string;
  tags?: string[];
  category_id?: string;
  privacy_status?: string;
}

export interface ManualUploadResponse {
  message: string;
  occurrence_id: string;
  job_id: string;
  status: string;
}

export interface UploadJobItem {
  id: string;
  occurrence_id: string;
  status: string; // QUEUED, DOWNLOADING, IN_PROGRESS, SUCCESS, FAILED, RETRYING
  bytes_downloaded: number;
  bytes_uploaded: number;
  total_bytes: number;
  progress_percentage: number;
  youtube_video_id: string | null;
  youtube_url: string | null;
  error_type: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkerPoolStatus {
  max_concurrent_uploads: number;
  per_channel_max_concurrent: number;
  channel_cooldown_seconds: number;
  active_uploads_count: number;
  is_paused: boolean;
  running_jobs: Array<{
    channel_id: string;
    started_at: string;
    dry_run: boolean;
  }>;
  active_channels: string[];
}

export interface ReconciliationSummary {
  total_stuck_found: number;
  reconciled_to_queue: number;
  permanently_failed: number;
  cleaned_temp_files: number;
}

export const triggerManualUpload = async (data: ManualUploadRequest): Promise<ManualUploadResponse> => {
  const response = await apiClient.post<ManualUploadResponse>('/uploads/manual', data);
  return response.data;
};

export const getUploadJob = async (jobId: string): Promise<UploadJobItem> => {
  const response = await apiClient.get<UploadJobItem>(`/uploads/${jobId}`);
  return response.data;
};

export const listUploadJobs = async (statusFilter?: string): Promise<UploadJobItem[]> => {
  const response = await apiClient.get<{ total: number; items: UploadJobItem[] }>('/uploads', {
    params: { status_filter: statusFilter },
  });
  return response.data.items;
};

export const retryUploadJob = async (jobId: string): Promise<void> => {
  await apiClient.post(`/uploads/${jobId}/retry`);
};

export const triggerReconciliation = async (): Promise<ReconciliationSummary> => {
  const response = await apiClient.post<ReconciliationSummary>('/uploads/reconcile');
  return response.data;
};

export const getWorkerPoolStatus = async (): Promise<WorkerPoolStatus> => {
  const response = await apiClient.get<WorkerPoolStatus>('/uploads/queue/status');
  return response.data;
};

export const pauseWorkerQueue = async (): Promise<void> => {
  await apiClient.post('/uploads/queue/pause');
};

export const resumeWorkerQueue = async (): Promise<void> => {
  await apiClient.post('/uploads/queue/resume');
};
