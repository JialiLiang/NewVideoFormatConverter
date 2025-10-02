import { apiClient } from './client';

export type VideoFormat = 'square' | 'square_blur' | 'landscape' | 'vertical';

export interface StartConversionResponse {
  job_id: string;
}

export const startConversion = async (files: File[], formats: VideoFormat[]) => {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  formats.forEach((format) => formData.append('formats', format));
  const { data } = await apiClient.post<StartConversionResponse>('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export type JobStatus = 'queued' | 'processing' | 'completed' | 'error' | 'cancelled';

export interface ConversionResult {
  filename: string;
  original_name: string;
  format_name: string;
  metadata?: Record<string, unknown>;
}

export interface ConversionStatus {
  status: JobStatus;
  progress: number;
  results?: ConversionResult[];
  errors?: string[];
  estimated_time_remaining_human?: string | null;
  elapsed_time_human?: string | null;
  cancel_requested?: boolean;
}

export const fetchStatus = async (jobId: string) => {
  const { data } = await apiClient.get<ConversionStatus>(`/status/${jobId}`);
  return data;
};

export const cancelJob = async (jobId: string) => {
  const { data } = await apiClient.post(`/cancel/${jobId}`);
  return data;
};
