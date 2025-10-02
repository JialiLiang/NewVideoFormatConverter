import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiBase = env.VITE_API_BASE_URL || 'http://localhost:5000';

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': {
          target: apiBase,
          changeOrigin: true,
          secure: false,
        },
        '/audio': {
          target: apiBase,
          changeOrigin: true,
          secure: false,
        },
        '/video': {
          target: apiBase,
          changeOrigin: true,
          secure: false,
        },
        '/adlocalizer': {
          target: apiBase,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
});
