/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    manifest: true,
    rolldownOptions: {
      output: {
        codeSplitting: { groups: [{ name: 'katex', test: /node_modules[\\/]katex[\\/]/ }] },
      },
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    // The FastAPI server (AGENTS.md §6). Same origin, so no CORS and audio lip sync works.
    proxy: {
      '/lessons': 'http://localhost:8000',
      '/audio': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
