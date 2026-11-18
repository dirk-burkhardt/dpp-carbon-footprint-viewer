<script setup lang="ts">
/**
 * Tabelle der Fehler und Warnungen am unteren Bildschirmrand, geöffnet über die Statusanzeige.
 */
import { computed, onUnmounted, ref } from 'vue'
import { storageRef } from '@/lib/storage'
import { ExclamationTriangleIcon, XCircleIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { clearProblems, problemPanelOpen, problemSources, problems, removeProblem, type Problem } from '@/lib/problems'

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

// Affected assets in the table row; the expanded row lists every occurrence
const MAX_SOURCES = 3
function sourcesLabel(problem: Problem) {
  const sources = problemSources(problem)
  const shown = sources.slice(0, MAX_SOURCES).join(', ')
  return sources.length > MAX_SOURCES ? `${shown} and ${sources.length - MAX_SOURCES} more` : shown
}

function hasDetails(problem: Problem) {
  return Boolean(problem.details || problem.trace || problem.occurrences.length)
}

// Details shared by all occurrences are shown once above the list
function commonDetails(problem: Problem) {
  if (!problem.occurrences.length) {
    return problem.details
  }
  const details = new Set(problem.occurrences.map((o) => o.details))
  return details.size === 1 ? [...details][0] : undefined
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
            <th class="w-1/4">Asset</th>
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
              <td class="text-right" :title="problem.occurrences.length ? 'Number of affected elements' : 'Number of times the problem occurred'">{{ problem.count }}</td>
              <td>
                <code v-if="problem.status" class="mr-1">{{ problem.status }}</code>
                {{ problem.message }}
                <span v-if="commonDetails(problem) && expanded !== problem" class="opacity-60 truncate"> &ndash; {{ commonDetails(problem) }}</span>
              </td>
              <td class="truncate max-w-0" :title="problemSources(problem).join('\n')">{{ sourcesLabel(problem) }}</td>
              <td class="whitespace-nowrap">{{ time(problem.lastTimestamp) }}</td>
              <td>
                <button type="button" class="opacity-50 hover:opacity-100" title="Remove" @click.stop="removeProblem(problem)">
                  <XMarkIcon class="h-4" />
                </button>
              </td>
            </tr>
            <tr v-if="expanded === problem && hasDetails(problem)">
              <td></td>
              <td></td>
              <td colspan="4">
                <p v-if="commonDetails(problem)" class="whitespace-pre-wrap">{{ commonDetails(problem) }}</p>
                <table v-if="problem.occurrences.length" class="mt-1 text-sm">
                  <tbody>
                    <tr v-for="(o, j) of problem.occurrences" :key="j">
                      <td class="pr-4 py-0.5 align-top whitespace-nowrap">{{ o.source }}</td>
                      <td class="pr-4 py-0.5 align-top opacity-70">{{ o.subject ?? '' }}</td>
                      <td v-if="!commonDetails(problem)" class="py-0.5 align-top">{{ o.details }}</td>
                    </tr>
                  </tbody>
                </table>
                <pre v-if="problem.trace" class="whitespace-pre-wrap text-xs opacity-70">{{ problem.trace }}</pre>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>
