import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

// Backend URL: dev is Windows ↔ Spark, default to localhost (proxy or tunnel).
// Override with VITE_API_BASE in .env.local for direct Spark IP / VPN.
const API_BASE = process.env.VITE_API_BASE || 'http://localhost:8000'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: API_BASE,
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
        ws: true,
      },
    },
  },
  test: {
    environment: 'happy-dom',
    globals: true,
    include: ['tests/**/*.spec.ts'],
  },
})
