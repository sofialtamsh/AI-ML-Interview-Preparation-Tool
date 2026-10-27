import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// This file runs in Node; only this one environment variable is read from it.
declare const process: { env: Record<string, string | undefined> }

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // Same-origin API in development, so session cookies and the CSRF header need no CORS.
    // IPP_API_PROXY points a second dev server at another API instance (e.g. a test database).
    proxy: { '/api': { target: process.env.IPP_API_PROXY ?? 'http://localhost:8010' } },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})
