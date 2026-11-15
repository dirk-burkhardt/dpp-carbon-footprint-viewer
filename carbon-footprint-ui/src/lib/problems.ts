/**
 * Gemeinsamer Speicher für Fehler und Warnungen.
 *
 * Statusanzeige und Fehlertabelle lesen beide hieraus. Gleiche Meldungen werden zusammengefasst (Zähler),
 * damit z. B. viele gleichartige Ladefehler nicht die Liste füllen.
 */
import { computed, reactive, ref } from 'vue'
import { ErrorClient, type ErrorDataHandler } from '@/lib/ErrorDataHandler'

export type Problem = ErrorDataHandler & {
  level: 'error' | 'warning'
  count: number
  lastTimestamp: Date
}

export const problems = reactive<Problem[]>([])

/** Ob die Fehlertabelle geöffnet ist */
export const problemPanelOpen = ref(false)

export const errorCount = computed(() => problems.filter((p) => p.level === 'error').reduce((n, p) => n + p.count, 0))
export const warningCount = computed(() => problems.filter((p) => p.level === 'warning').reduce((n, p) => n + p.count, 0))

function addProblem(e: ErrorDataHandler) {
  const level = e.level ?? 'error'
  const timestamp = e.timestamp ?? new Date()
  const existing = problems.find(
    (p) => p.level === level && p.message === e.message && p.details === e.details && p.status === e.status
  )
  if (existing) {
    existing.count += 1
    existing.lastTimestamp = timestamp
    return
  }
  problems.unshift({ ...e, level, count: 1, timestamp, lastTimestamp: timestamp })
}

export function removeProblem(problem: Problem) {
  const i = problems.indexOf(problem)
  if (i >= 0) {
    problems.splice(i, 1)
  }
}

export function clearProblems() {
  problems.splice(0, problems.length)
  problemPanelOpen.value = false
}

ErrorClient.errorFunction = (e: ErrorDataHandler | undefined) => {
  if (e === undefined) {
    return
  }
  if ((e.level ?? 'error') === 'error') {
    console.error(e.message, e)
  } else {
    console.warn(e.message, e)
  }
  addProblem(e)
}
