import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  resolve: {
    preserveSymlinks: true,
  },
  server: {
    port: 5173,
    fs: {
      strict: false,
    },
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/documents': 'http://127.0.0.1:8000',
      '/chat': 'http://127.0.0.1:8000',
      '/events': 'http://127.0.0.1:8000',
      '/requests': 'http://127.0.0.1:8000',
      '/forensics': 'http://127.0.0.1:8000',
    },
  },
});

