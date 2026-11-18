/**
 * Gemeinsamer Speicher für Fehler und Warnungen.
 *
 * Statusanzeige und Fehlertabelle lesen beide hieraus. Gleiche Meldungen werden zusammengefasst (Zähler),
 * damit z. B. viele gleichartige Ladefehler nicht die Liste füllen.
 */
import { computed, reactive, ref } from 'vue'
import { ErrorClient, type ErrorDataHandler } from '@/lib/ErrorDataHandler'

/** One place where a problem occurs: an asset and optionally an element within it */
export type ProblemOccurrence = {
  source: string
  subject?: string
  details?: string
  lastTimestamp: Date
}

export type Problem = ErrorDataHandler & {
  level: 'error' | 'warning'
  /**
   * Problems with a source: number of distinct places (asset and element) where the problem occurs.
   * Problems without a source: number of times the problem was reported.
   */
  count: number
  lastTimestamp: Date
  occurrences: ProblemOccurrence[]
}

export const problems = reactive<Problem[]>([])

/** Ob die Fehlertabelle geöffnet ist */
export const problemPanelOpen = ref(false)

export const errorCount = computed(() => problems.filter((p) => p.level === 'error').reduce((n, p) => n + p.count, 0))
export const warningCount = computed(() => problems.filter((p) => p.level === 'warning').reduce((n, p) => n + p.count, 0))

/**
 * Adds a problem. Equal messages are grouped. A problem with a source is counted once per asset and element:
 * views compute values repeatedly and assets are loaded again when navigating, which must not inflate the count.
 */
function addProblem(e: ErrorDataHandler) {
  const level = e.level ?? 'error'
  const timestamp = e.timestamp ?? new Date()
  const hasSource = e.source !== undefined
  const existing = problems.find(
    (p) =>
      p.level === level &&
      p.message === e.message &&
      p.status === e.status &&
      // With a source the details describe the occurrence, otherwise they distinguish problems
      (hasSource ? p.occurrences.length > 0 : p.occurrences.length === 0 && p.details === e.details)
  )
  const problem: Problem = existing ?? {
    ...e,
    level,
    count: 0,
    timestamp,
    lastTimestamp: timestamp,
    occurrences: [],
  }
  problem.lastTimestamp = timestamp
  if (hasSource) {
    const occurrence = problem.occurrences.find(
      (o) => o.source === e.source && o.subject === e.subject && o.details === e.details
    )
    if (occurrence) {
      occurrence.lastTimestamp = timestamp
    } else {
      problem.occurrences.push({ source: e.source!, subject: e.subject, details: e.details, lastTimestamp: timestamp })
    }
    problem.count = problem.occurrences.length
  } else {
    problem.count += 1
  }
  if (!existing) {
    problems.unshift(problem)
  }
}

/** Distinct assets a problem occurs in, in order of appearance */
export function problemSources(problem: Problem): string[] {
  return [...new Set(problem.occurrences.map((o) => o.source))]
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
