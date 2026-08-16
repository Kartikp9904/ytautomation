import axios from 'axios';

export const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('yt_auth_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('yt_auth_token');
    }
    return Promise.reject(error);
  }
);

export interface SystemHealth {
  status: string;
  environment: string;
  database: string;
  scheduler: string;
  storage: {
    provider: string;
    connected: boolean;
    free_space_gb: number | null;
    total_space_gb: number | null;
  };
  timestamp: string;
  version: string;
}

export const fetchHealth = async (): Promise<SystemHealth> => {
  const response = await apiClient.get<SystemHealth>('/health');
  return response.data;
};
