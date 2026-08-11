import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// The API base is injected at build time via VITE_API_BASE (see .env.example). In dev we
// also proxy /chat, /ingest, /health to the backend so the app works with no env at all.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/chat': 'http://localhost:8000',
      '/ingest': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
});
