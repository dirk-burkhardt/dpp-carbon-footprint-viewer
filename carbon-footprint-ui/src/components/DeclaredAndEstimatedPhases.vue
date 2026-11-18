<script setup lang="ts">
/**
 * CO2eq per life cycle phase: declared values solid, estimated values hatched, so both can be told apart.
 * Phases a declared footprint covers are never estimated (see the Estimates view).
 */
import { computed } from 'vue'
import { grams } from '@/lib/util'
import { co2eqByLifeCyclePhases, sortPhases, type Carbon } from '@/lib/carbonValues'
import type { ApiEstimates } from '@/lib/api/products'

const props = defineProps<{ carbon?: Carbon, estimates?: ApiEstimates | null, showEstimates: boolean }>()

type Row = { phase: string, label?: string, co2eq: number, estimated: boolean }

const rows = computed<Row[]>(() => {
  const declared = props.carbon ? co2eqByLifeCyclePhases(props.carbon) : {}
  const result: Row[] = Object.entries(declared).map(([phase, co2eq]) => ({ phase: phase || 'unknown phase', co2eq, estimated: false }))
  if (props.showEstimates) {
    for (const p of props.estimates?.phases ?? []) {
      if (p.status === 'estimated' && p.co2eq) {
        result.push({ phase: p.phase, label: p.label, co2eq: p.co2eq, estimated: true })
      }
    }
  }
  const order = sortPhases(result.map((r) => r.phase))
  return result.sort((a, b) => order.indexOf(a.phase) - order.indexOf(b.phase) || Number(a.estimated) - Number(b.estimated))
})
const max = computed(() => Math.max(0, ...rows.value.map((r) => r.co2eq)))
const declaredTotal = computed(() => rows.value.filter((r) => !r.estimated).reduce((s, r) => s + r.co2eq, 0))
const estimatedTotal = computed(() => rows.value.filter((r) => r.estimated).reduce((s, r) => s + r.co2eq, 0))
</script>

<template>
  <div>
    <div class="flex flex-wrap gap-6 text-sm mb-3">
      <span><span class="inline-block w-4 h-3 align-middle mr-1 bg-primary"></span>declared: {{ grams(declaredTotal, 'kg') }}</span>
      <span v-if="showEstimates">
        <span class="inline-block w-4 h-3 align-middle mr-1 estimate-fill"></span>estimated: {{ grams(estimatedTotal, 'kg') }}
      </span>
      <span v-if="showEstimates && estimatedTotal > 0">together: {{ grams(declaredTotal + estimatedTotal, 'kg') }}</span>
    </div>
    <p v-if="!rows.length" class="text-sm italic">No emissions per phase known.</p>
    <div v-for="(r, i) of rows" :key="i" class="grid grid-cols-[9rem_1fr] items-center gap-3 h-8">
      <div class="text-sm text-right truncate" :title="r.label">
        {{ r.phase }}<span v-if="r.estimated" class="opacity-70"> (estimated)</span>
      </div>
      <div class="flex items-center h-full">
        <div
          class="h-5 rounded-r-sm"
          :class="r.estimated ? 'estimate-fill' : 'bg-primary'"
          :style="{ width: `calc(${max > 0 ? (r.co2eq / max) * 100 : 0}% - 7rem * ${max > 0 ? r.co2eq / max : 0})` }"
        ></div>
        <span class="text-xs ml-2 whitespace-nowrap">{{ grams(r.co2eq, 'kg') }}</span>
      </div>
    </div>
  </div>
</template>
