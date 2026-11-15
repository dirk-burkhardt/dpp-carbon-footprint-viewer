import { readFileSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // Im Entwicklungsbetrieb wird /api an die API weitergereicht. Frontend und API laufen so unter derselben
  // Adresse, CORS ist nicht nötig (wie später hinter nginx).
  const apiTarget = env.API_PROXY_TARGET || 'http://localhost:8080'
  // Einzige Quelle der Version ist package.json
  const { version } = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf-8'))
  return {
    define: {
      __APP_VERSION__: JSON.stringify(version)
    },
    plugins: [vue(), tailwindcss()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    oxc: {
      // CarbonSankeyTooltip.tsx nutzt klassisches JSX mit Vues h()
      jsx: { runtime: 'classic', pragma: 'h', pragmaFrag: 'Fragment' }
    },
    server: {
      proxy: {
        '/api': { target: apiTarget, changeOrigin: true }
      }
    },
    preview: {
      proxy: {
        '/api': { target: apiTarget, changeOrigin: true }
      }
    },
    build: {
      sourcemap: false,
      chunkSizeWarningLimit: 1500
    }
  }
})
