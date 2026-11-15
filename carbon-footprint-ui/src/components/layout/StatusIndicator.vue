<script setup lang="ts">
/**
 * Symbol für den Zustand der Verarbeitung: OK (blau), Warnungen (gelb) oder Fehler (rot).
 * Links unten die Anzahl der Warnungen, rechts unten die Anzahl der Fehler. Ein Klick öffnet die Tabelle.
 */
import { computed } from 'vue'
import { CheckCircleIcon, ExclamationTriangleIcon, XCircleIcon } from '@heroicons/vue/24/outline'
import { errorCount, problemPanelOpen, warningCount } from '@/lib/problems'

const props = defineProps<{ small?: boolean }>()

const state = computed(() => (errorCount.value > 0 ? 'error' : warningCount.value > 0 ? 'warning' : 'ok'))
const title = computed(() => {
  if (state.value === 'ok') {
    return 'No problems'
  }
  return `${warningCount.value} warning(s), ${errorCount.value} error(s). Click to show details`
})
</script>

<template>
  <button
    type="button"
    class="relative inline-flex items-center justify-center"
    :class="props.small ? 'w-10 h-10' : 'w-14 h-14'"
    :title="title"
    :disabled="state === 'ok' && !problemPanelOpen ? true : undefined"
    @click="problemPanelOpen = !problemPanelOpen"
  >
    <CheckCircleIcon v-if="state === 'ok'" class="h-full text-info" />
    <ExclamationTriangleIcon v-else-if="state === 'warning'" class="h-full text-warning" />
    <XCircleIcon v-else class="h-full text-error" />
    <span
      v-if="warningCount > 0"
      class="absolute -bottom-1 -left-1 min-w-5 px-1 rounded-sm bg-warning text-warning-content text-xs leading-5 text-center"
    >{{ warningCount }}</span>
    <span
      v-if="errorCount > 0"
      class="absolute -bottom-1 -right-1 min-w-5 px-1 rounded-sm bg-error text-error-content text-xs leading-5 text-center"
    >{{ errorCount }}</span>
  </button>
</template>
