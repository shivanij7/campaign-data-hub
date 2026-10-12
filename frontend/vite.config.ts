import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In dev the browser calls /api/... on this server, which forwards to FastAPI (so there is no CORS to configure).
// Default is 127.0.0.1, not "localhost": Node may resolve localhost to IPv6 (::1) where uvicorn isn't listening.
// If port 8000 is taken, start the API on another port and run:  VITE_API_PROXY=http://127.0.0.1:8001 npm run dev
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': process.env.VITE_API_PROXY ?? 'http://127.0.0.1:8000' } },
})
