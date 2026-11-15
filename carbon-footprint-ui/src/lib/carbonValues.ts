/**
 * Kennzahlen des CO2-Fußabdrucks eines Assets für Datasheet und Compare.
 */
import CarbonFootprint from '@/lib/model/CarbonFootprint'
import CarbonTree from '@/lib/model/CarbonTree'
import { lifeCyclePhaseSequence } from '@/lib/lifeCycleUtil'

export type Carbon = CarbonTree | CarbonFootprint

function addPhases(target: Record<string, number>, source: Record<string, number>) {
  for (const [phase, value] of Object.entries(source)) {
    target[phase] = (target[phase] || 0) + value
  }
}

function phasesOfFootprint(footprint: CarbonFootprint, count: number) {
  const result: Record<string, number> = {}
  for (const p of footprint.product) {
    addPhases(result, { [p.lifeCyclePhase.toString()]: p.co2eq * count })
  }
  return result
}

/**
 * CO2eq (kg) je Lebenszyklusphase. Hat ein Asset selbst einen Fußabdruck, gilt dieser, sonst die Summe seiner
 * Komponenten, jeweils mit deren Stückzahl.
 * @param data Fußabdruck oder Produktbaum
 * @param count Anzahl der Einheiten
 */
export function co2eqByLifeCyclePhases(data: Carbon, count = 1): Record<string, number> {
  if (data instanceof CarbonFootprint) {
    return phasesOfFootprint(data, count)
  }
  if (data.asset.footprint) {
    return phasesOfFootprint(data.asset.footprint, count)
  }
  const result: Record<string, number> = {}
  for (const child of data.connectionsArray) {
    addPhases(result, co2eqByLifeCyclePhases(child, count * (child.connection?.bulkCount || 1)))
  }
  return result
}

/** Sortiert Phasenbezeichnungen (z. B. "A1", "A1-A3", "B6") nach ihrer Reihenfolge im Lebenszyklus */
export function sortPhases(phases: string[]): string[] {
  const position = (phase: string) => {
    const i = lifeCyclePhaseSequence.findIndex((p) => phase.startsWith(p))
    return i < 0 ? lifeCyclePhaseSequence.length : i
  }
  return [...phases].sort((a, b) => position(a) - position(b) || a.localeCompare(b))
}
