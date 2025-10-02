import { apiClient } from './client';

export interface TranscriptionResponse {
  transcription?: string;
  video_available_for_vocal_removal?: boolean;
  error?: string;
}

export const transcribeMedia = async (file: File): Promise<TranscriptionResponse> => {
  const formData = new FormData();
  formData.append('video', file);
  const { data } = await apiClient.post<TranscriptionResponse>('/api/transcribe', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export interface TranslateRequest {
  text: string;
  languages: string[];
  translation_mode: string;
}

export interface TranslateResponse {
  translations?: Record<string, string>;
  error?: string;
}

export const translateText = async (payload: TranslateRequest) => {
  const { data } = await apiClient.post<TranslateResponse>('/api/translate', payload);
  return data;
};

export interface ElevenLabsVoice {
  id: string;
  name: string;
  preview_url?: string;
  labels?: Record<string, string>;
}

export interface VoicesResponse {
  voices: ElevenLabsVoice[];
  default_voice_id?: string | null;
  count: number;
}

export const fetchVoices = async () => {
  const { data } = await apiClient.get<VoicesResponse>('/api/voices');
  return data;
};

export interface GenerateVoiceRequest {
  translations: Record<string, string>;
  voice_id: string;
  voice_model?: string;
}

export interface GenerateVoiceResponse {
  audio_files?: Record<string, string>;
  error?: string;
  warnings?: Record<string, string>;
}

export const generateVoiceovers = async (payload: GenerateVoiceRequest) => {
  const { data } = await apiClient.post<GenerateVoiceResponse>('/api/generate-voice', payload);
  return data;
};

export interface UploadVideoResponse {
  success?: boolean;
  filename?: string;
  size_mb?: number;
  video_path?: string;
  clean_audio_path?: string;
  error?: string;
}

export const uploadVideo = async (file: File) => {
  const formData = new FormData();
  formData.append('video', file);
  const { data } = await apiClient.post<UploadVideoResponse>('/api/upload-video', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export interface UploadMusicResponse {
  success?: boolean;
  filename?: string;
  is_default?: boolean;
  music_path?: string;
  error?: string;
}

export const uploadCustomMusic = async (file: File) => {
  const formData = new FormData();
  formData.append('music', file);
  const { data } = await apiClient.post<UploadMusicResponse>('/api/upload-custom-music', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const uploadDefaultMusic = async (filename: string) => {
  const formData = new FormData();
  formData.append('use_default', 'true');
  formData.append('default_music_file', filename);
  const { data } = await apiClient.post<UploadMusicResponse>('/api/upload-custom-music', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export interface MixAudioRequest {
  original_volume: number;
  voiceover_volume: number;
  use_custom_music?: boolean;
  add_subtitles?: boolean;
  subtitle_style?: string;
}

export interface MixAudioResponse {
  mixed_videos?: Record<string, unknown>;
  subtitles_enabled?: boolean;
  subtitle_data?: Record<string, unknown>;
  subtitle_styles?: string[];
  default_subtitle_style?: string;
  error?: string;
}

export const mixAudio = async (payload: MixAudioRequest) => {
  const { data } = await apiClient.post<MixAudioResponse>('/api/mix-audio', payload);
  return data;
};
