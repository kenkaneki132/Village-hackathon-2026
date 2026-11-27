import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' makes the build work from any sub-path (e.g. GitHub Pages /Village-hackathon-2026/)
export default defineConfig({
  base: './',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/verify': 'http://localhost:8000',
      '/synthetic-test': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    }
  }
})