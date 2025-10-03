import { apiClient } from './client';

export interface ExtractPlaylistResponse {
  success: boolean;
  playlist_url?: string;
  playlist_title?: string;
  total_videos?: number;
  video_ids?: string[];
  videos?: Array<{
    video_id: string;
    title: string;
    url: string;
    duration?: number;
    views?: number;
    author?: string;
  }>;
  video_ids_text?: string;
  error?: string;
}

export const extractPlaylist = async (playlistUrl: string, password: string) => {
  const { data } = await apiClient.post<ExtractPlaylistResponse>('/api/extract-playlist', {
    playlist_url: playlistUrl,
    password,
  });
  return data;
};
