import axios from 'axios';

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '';

export const apiClient = axios.create({
  baseURL: configuredBaseUrl || undefined,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const resolveApiUrl = (path: string) => {
  const trimmed = path.startsWith('/') ? path : `/${path}`;
  if (configuredBaseUrl && /^https?:/i.test(configuredBaseUrl)) {
    return new URL(trimmed, configuredBaseUrl).toString();
  }
  return trimmed;
};
