import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In development, /api is proxied to FastAPI so the session cookie is same-origin.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
