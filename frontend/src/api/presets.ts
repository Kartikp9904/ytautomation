import { apiClient } from './client';

export interface ContentPreset {
  id: string;
  name: string;
  category_id?: string;
  category_name?: string;
  default_language?: string;
  default_audio_language?: string;
  made_for_kids?: boolean;
  age_restricted?: boolean;
  contains_synthetic_media?: boolean;
  description?: string;
  tags?: string[];
  hooks: string[];
}

export const getPresets = async (): Promise<ContentPreset[]> => {
  const res = await apiClient.get<ContentPreset[]>('/presets');
  return res.data;
};

export const getPreset = async (presetId: string): Promise<ContentPreset> => {
  const res = await apiClient.get<ContentPreset>(`/presets/${presetId}`);
  return res.data;
};

export const savePreset = async (preset: Partial<ContentPreset>): Promise<ContentPreset> => {
  const res = await apiClient.post<ContentPreset>('/presets', preset);
  return res.data;
};

export const deletePreset = async (presetId: string): Promise<{ message: string; id: string }> => {
  const res = await apiClient.delete<{ message: string; id: string }>(`/presets/${presetId}`);
  return res.data;
};

export const importPresetsJson = async (data: any, overwriteAll = false): Promise<any> => {
  const res = await apiClient.post(`/presets/import?overwrite_all=${overwriteAll}`, data);
  return res.data;
};

export const uploadPresetsJsonFile = async (file: File, overwriteAll = false): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await apiClient.post(`/presets/upload-json?overwrite_all=${overwriteAll}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return res.data;
};

export const exportPresetsJson = async (): Promise<Blob> => {
  const res = await apiClient.get('/presets/export', {
    responseType: 'blob',
  });
  return res.data;
};
