import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

const projectRoot = fileURLToPath(new URL('./', import.meta.url))

// https://vite.dev/config/
export default defineConfig(({ command }) => ({
  root: projectRoot,
  plugins: [
    vue(),
    // The devtools plugin is helpful locally, but it has been breaking
    // production builds on Windows with the current Vite/Rolldown stack.
    command === 'serve' ? vueDevTools() : null,
  ].filter(Boolean),
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
  },
  build: {
    target: 'esnext',
  },
  optimizeDeps: {
    entries: ['index.html'],
  },
}))
