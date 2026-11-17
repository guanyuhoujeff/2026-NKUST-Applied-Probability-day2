import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    rollupOptions: {
      input: { main: 'index.html', teacher: 'teacher.html' },
    },
  },
  server: {
    host: true,
    port: 52008,
    allowedHosts: ['mycena.com.tw'],
    proxy: {
      '/api': 'http://localhost:52014',
      '/ws': { target: 'ws://localhost:52014', ws: true },
    },
  },
})
