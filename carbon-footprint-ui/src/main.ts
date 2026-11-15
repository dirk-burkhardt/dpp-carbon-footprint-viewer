import './assets/main.css'

import { createApp } from 'vue'
import { ErrorClient } from '@/lib/ErrorDataHandler'
import { update as updateApiConfig } from '@/lib/apiConfig'
import { updateClients } from '@/lib/api/clients'
import App from './App.vue'
import router from './router'

/** Lädt die Laufzeitkonfiguration (/config.json). Fehlt sie, gelten die Werte aus dem Build. */
async function loadRuntimeConfig() {
  try {
    const response = await fetch('/config.json', { cache: 'no-cache' })
    if (!response.ok) {
      return
    }
    const content: unknown = await response.json()
    if (content && typeof content === 'object' && !Array.isArray(content)) {
      updateApiConfig(content as Record<string, unknown>)
      updateClients()
    } else {
      console.error('config.json enthält kein JSON-Objekt und wird ignoriert')
    }
  } catch (error) {
    console.error('Could not load config.json', error)
  }
}

// Abgelehnte Promises nicht unbemerkt lassen
window.onunhandledrejection = ErrorClient.unhandledRejection

loadRuntimeConfig().finally(() => {
  createApp(App).use(router).mount('#app')
})
