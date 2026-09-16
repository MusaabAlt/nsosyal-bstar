import { fileURLToPath, URL } from 'node:url'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => ({
  plugins: [
    vue(),
    // Auto-imports only the Vuetify components we use, with their CSS.
    vuetify({ autoImport: true }),
    tailwindcss(),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    // The Go backend serves /api on :8080 (and the built UI in production).
    // A machine where 8080 is taken sets API_PROXY_TARGET in .env.local
    // (git-ignored), e.g. API_PROXY_TARGET=http://127.0.0.1:8090.
    proxy: { '/api': loadEnv(mode, process.cwd(), '').API_PROXY_TARGET || 'http://127.0.0.1:8080' },
  },
  build: {
    // Everything (fonts included) ships inside dist/: the demo room is offline.
    assetsInlineLimit: 0,
    sourcemap: false,
  },
  test: {
    environment: 'jsdom',
    css: false,
    server: { deps: { inline: ['vuetify'] } },
  },
}))
