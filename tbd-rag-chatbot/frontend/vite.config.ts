import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Cau hinh Vite cho frontend TBD RAG Chatbot
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy API requests den backend FastAPI de tranh CORS trong dev mode
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
})
