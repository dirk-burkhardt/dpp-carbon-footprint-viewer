/**
 * Estimates for life cycle phases without declared footprint: whether they are shown and the assumptions the user
 * set. Both are kept in the browser. Country and transport apply to all assets, service life and operating hours
 * per asset (they depend on the product).
 */
import { computed, type Ref } from 'vue'
import { computedAsync } from '@vueuse/core'
import { storageRef } from '@/lib/storage'
import { fetchEstimates, type ApiEstimates, type ApiEstimateValue, type EstimateQuery } from '@/lib/api/products'

/** Estimates are shown by default and can be hidden */
export const showEstimates = storageRef<boolean>('showEstimates', true)

const country = storageRef<string>('estimateCountry', 'EU')
const transport = storageRef<{ km?: number, mode: string }>('estimateTransport', { mode: 'road' })
const perAsset = storageRef<Record<string, { lifetimeYears?: number, hoursPerYear?: number }>>('estimateAssumptions', {})

export type Assumptions = {
  country: string
  transportKm?: number
  transportMode: string
  lifetimeYears?: number
  hoursPerYear?: number
}

function positive(value: unknown): number | undefined {
  const number = Number(value)
  return value === '' || value === null || value === undefined || !Number.isFinite(number) || number <= 0 ? undefined : number
}

/** Assumptions for an asset, readable and writable */
export function useAssumptions(assetId: Ref<string>) {
  return computed<Assumptions>({
    get: () => ({
      country: country.value,
      transportKm: transport.value.km,
      transportMode: transport.value.mode,
      lifetimeYears: perAsset.value[assetId.value]?.lifetimeYears,
      hoursPerYear: perAsset.value[assetId.value]?.hoursPerYear,
    }),
    set: (value) => {
      country.value = value.country || 'EU'
      transport.value = { km: positive(value.transportKm), mode: value.transportMode || 'road' }
      perAsset.value = {
        ...perAsset.value,
        [assetId.value]: { lifetimeYears: positive(value.lifetimeYears), hoursPerYear: positive(value.hoursPerYear) },
      }
    },
  })
}

/** Estimates of an asset with the current assumptions (undefined while loading, null if not available) */
export function useEstimates(assetId: Ref<string>) {
  const assumptions = useAssumptions(assetId)
  const estimates = computedAsync<ApiEstimates | null | undefined>(async () => {
    const a = assumptions.value
    const query: EstimateQuery = {
      country: a.country,
      lifetimeYears: positive(a.lifetimeYears),
      hoursPerYear: positive(a.hoursPerYear),
      transportKm: positive(a.transportKm),
      transportMode: a.transportMode,
    }
    return fetchEstimates(assetId.value, query)
  }, undefined)
  return { estimates, assumptions }
}

export const originLabels: Record<ApiEstimateValue['origin'], string> = {
  file: 'from the asset administration shell',
  class: 'default of the product class',
  assumption: 'general assumption',
  user: 'set by you',
  factor: 'emission factor',
}
