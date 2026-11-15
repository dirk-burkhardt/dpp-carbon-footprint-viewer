<script setup lang="ts">
/**
 * Tabelle der Fehler und Warnungen am unteren Bildschirmrand, geöffnet über die Statusanzeige.
 */
import { computed, onUnmounted, ref } from 'vue'
import { storageRef } from '@/lib/storage'
import { ExclamationTriangleIcon, XCircleIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { clearProblems, problemPanelOpen, problems, removeProblem, type Problem } from '@/lib/problems'

const expanded = ref<Problem | undefined>()

function toggle(problem: Problem) {
  expanded.value = expanded.value === problem ? undefined : problem
}

// Höhe in Pixeln, am oberen Rand per Ziehen veränderbar
// Ohne eigene Einstellung etwa ein Drittel der Fensterhöhe
const height = storageRef<number | null>('problemPanelHeightPx', null)
const clampHeight = (h: number) => Math.min(Math.max(h, 160), window.innerHeight - 80)
const panelHeight = computed(() => clampHeight(height.value ?? Math.round(window.innerHeight * 0.32)))

function onResize(e: PointerEvent) {
  height.value = clampHeight(window.innerHeight - e.clientY)
}
function stopResize() {
  window.removeEventListener('pointermove', onResize)
  window.removeEventListener('pointerup', stopResize)
  document.body.style.userSelect = ''
}
function startResize(e: PointerEvent) {
  e.preventDefault()
  document.body.style.userSelect = 'none'
  window.addEventListener('pointermove', onResize)
  window.addEventListener('pointerup', stopResize)
}
onUnmounted(stopResize)

function time(date: Date) {
  return date.toLocaleTimeString()
}
</script>

<template>
  <div
    v-if="problemPanelOpen"
    class="fixed bottom-0 inset-x-0 z-[70] flex flex-col bg-base-100 border-t border-base-300 shadow-[0_-4px_12px_rgba(0,0,0,0.12)]"
    :style="{ height: `${panelHeight}px` }"
  >
    <div
      class="absolute -top-1 inset-x-0 h-2 cursor-ns-resize"
      title="Drag to change the height"
      @pointerdown="startResize"
    ></div>
    <div class="flex items-center gap-4 px-4 py-1 border-b border-base-300 shrink-0">
      <span class="font-medium">Problems</span>
      <button v-if="problems.length" type="button" class="btn btn-ghost btn-xs" @click="clearProblems">Clear all</button>
      <span class="grow"></span>
      <button type="button" class="btn btn-ghost btn-sm btn-square" title="Close" @click="problemPanelOpen = false">
        <XMarkIcon class="h-5" />
      </button>
    </div>
    <div class="overflow-auto overscroll-contain grow min-h-0">
      <p v-if="!problems.length" class="px-4 py-2 text-sm">No problems occurred.</p>
      <table v-else class="table table-sm table-pin-rows [&_td]:py-1">
        <thead>
          <tr>
            <th class="w-6"></th>
            <th class="w-10 text-right">Count</th>
            <th>Message</th>
            <th class="w-24">Time</th>
            <th class="w-6"></th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(problem, i) of problems" :key="i">
            <tr class="hover:bg-base-200 cursor-pointer" @click="toggle(problem)">
              <td>
                <XCircleIcon v-if="problem.level === 'error'" class="h-4 text-error" />
                <ExclamationTriangleIcon v-else class="h-4 text-warning" />
              </td>
              <td class="text-right">{{ problem.count }}</td>
              <td>
                <code v-if="problem.status" class="mr-1">{{ problem.status }}</code>
                {{ problem.message }}
                <span v-if="problem.details && expanded !== problem" class="opacity-60 truncate"> &ndash; {{ problem.details }}</span>
              </td>
              <td class="whitespace-nowrap">{{ time(problem.lastTimestamp) }}</td>
              <td>
                <button type="button" class="opacity-50 hover:opacity-100" title="Remove" @click.stop="removeProblem(problem)">
                  <XMarkIcon class="h-4" />
                </button>
              </td>
            </tr>
            <tr v-if="expanded === problem && (problem.details || problem.trace)">
              <td></td>
              <td></td>
              <td colspan="3">
                <p v-if="problem.details" class="whitespace-pre-wrap">{{ problem.details }}</p>
                <pre v-if="problem.trace" class="whitespace-pre-wrap text-xs opacity-70">{{ problem.trace }}</pre>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>
