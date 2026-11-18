<script setup lang="ts">
/**
 * Estimates for life cycle phases without declared footprint: assumptions, results with formula and inputs,
 * plausibility of the declared production footprint and the sources of all factors.
 */
import { computed } from 'vue'
import type { loadFullAssetInfo } from '@/lib/util'
import { grams } from '@/lib/util'
import { originLabels, showEstimates, useEstimates } from '@/lib/estimates'
import type { ApiEstimateValue } from '@/lib/api/products'

const props = defineProps<{ info: Awaited<ReturnType<typeof loadFullAssetInfo>> }>()

const assetId = computed(() => props.info.asset.id)
const { estimates, assumptions } = useEstimates(assetId)

function update(key: keyof typeof assumptions.value, value: string) {
  assumptions.value = { ...assumptions.value, [key]: value }
}

const sourceTitles = computed(() => Object.fromEntries((estimates.value?.sources ?? []).map((s) => [s.key, s])))

// Defaults of the product class, shown as placeholder of the assumption fields
const classDefault = (unit: string) =>
  estimates.value?.phases.flatMap((p) => p.inputs).find((i) => i.unit === unit && i.origin !== 'user')

function formatNumber(value: number) {
  return Math.abs(value) >= 100 ? Math.round(value).toLocaleString() : Number(value.toPrecision(3)).toLocaleString()
}

function describe(value: ApiEstimateValue) {
  const source = value.source ? sourceTitles.value[value.source] : undefined
  return [originLabels[value.origin], value.reference, source ? `${source.publisher}, ${source.edition ?? ''}`.trim() : '']
    .filter(Boolean)
    .join('; ')
}

const statusLabels = { estimated: 'estimated', declared: 'declared', missing: 'not possible' } as const
</script>

<template>
  <div class="col-span-6 m-4 space-y-4">
    <div class="flex flex-wrap items-start gap-4">
      <p class="grow basis-96 text-sm">
        Phases of the life cycle that no declared carbon footprint covers are estimated here from the data of the
        asset (mass, power consumption, materials, product class) and published emission factors. Estimates are
        shown hatched in Overview and Life Cycles and never change the declared values.
      </p>
      <label class="flex items-center gap-2 text-sm cursor-pointer">
        <input v-model="showEstimates" type="checkbox" class="toggle toggle-sm" />
        Show estimates in Overview and Life Cycles
      </label>
    </div>

    <div v-if="estimates === undefined" class="skeleton h-64 w-full"></div>
    <p v-else-if="estimates === null" class="alert">Estimates are not available from this API.</p>
    <template v-else>
      <!-- Assumptions -->
      <div class="rounded-lg border border-base-300 p-4">
        <h2 class="text-lg mb-1">Assumptions</h2>
        <p class="text-sm opacity-70 mb-3">
          Product class: <strong>{{ estimates.productClass.label }}</strong>
          <span v-if="estimates.productClass.classId"> ({{ estimates.productClass.system }} {{ estimates.productClass.classId }})</span>.
          Empty fields use the default shown in grey.
        </p>
        <div class="grid grid-cols-[repeat(auto-fit,minmax(12rem,1fr))] gap-4">
          <label class="text-sm">
            Country of use (electricity)
            <select class="select select-sm w-full mt-1" :value="assumptions.country" @change="update('country', ($event.target as HTMLSelectElement).value)">
              <option v-for="c of estimates.countries" :key="c" :value="c">{{ c === 'EU' ? 'EU-27 average' : c }}</option>
            </select>
          </label>
          <label class="text-sm">
            Service life in years
            <input
              class="input input-sm w-full mt-1" type="number" min="0" step="1"
              :value="assumptions.lifetimeYears ?? ''" :placeholder="classDefault('a')?.value?.toString() ?? ''"
              @change="update('lifetimeYears', ($event.target as HTMLInputElement).value)"
            />
          </label>
          <label class="text-sm">
            Operating hours per year
            <input
              class="input input-sm w-full mt-1" type="number" min="0" step="100"
              :value="assumptions.hoursPerYear ?? ''" :placeholder="classDefault('h/a')?.value?.toString() ?? ''"
              @change="update('hoursPerYear', ($event.target as HTMLInputElement).value)"
            />
          </label>
          <label class="text-sm">
            Transport to the customer in km
            <input
              class="input input-sm w-full mt-1" type="number" min="0" step="10" placeholder="not set"
              :value="assumptions.transportKm ?? ''"
              @change="update('transportKm', ($event.target as HTMLInputElement).value)"
            />
          </label>
          <label class="text-sm">
            Means of transport
            <select class="select select-sm w-full mt-1" :value="assumptions.transportMode" @change="update('transportMode', ($event.target as HTMLSelectElement).value)">
              <option v-for="(label, mode) of estimates.transportModes" :key="mode" :value="mode">{{ label }}</option>
            </select>
          </label>
        </div>
      </div>

      <!-- Results per phase -->
      <div class="rounded-lg border border-base-300 p-4">
        <div class="flex flex-wrap items-baseline gap-4 mb-2">
          <h2 class="text-lg grow">Estimated phases</h2>
          <span class="text-sm">
            Sum of estimates: <strong>{{ grams(estimates.estimatedCo2eq, 'kg') }}</strong>
            <span class="inline-block w-4 h-3 align-middle ml-1 estimate-fill"></span>
          </span>
        </div>
        <p v-for="(w, i) of estimates.warnings" :key="i" class="text-sm text-warning mb-2">{{ w }}</p>
        <table class="table table-sm">
          <thead>
            <tr><th>Phase</th><th>Status</th><th class="text-right">CO2eq</th><th class="w-1/2">Calculation</th></tr>
          </thead>
          <tbody>
            <tr v-for="p of estimates.phases" :key="p.phase" class="align-top">
              <td><strong>{{ p.phase }}</strong><br /><span class="text-xs opacity-70">{{ p.label }}</span></td>
              <td>
                <span v-if="p.status === 'estimated'" class="inline-block w-4 h-3 align-middle mr-1 estimate-fill"></span>
                <span v-else-if="p.status === 'declared'" class="inline-block w-4 h-3 align-middle mr-1 bg-primary"></span>
                {{ statusLabels[p.status] }}
              </td>
              <td class="text-right whitespace-nowrap">{{ p.co2eq != null ? grams(p.co2eq, 'kg') : '' }}</td>
              <td class="text-sm">
                <template v-if="p.status === 'estimated'">
                  <div class="mb-1">{{ p.formula }}</div>
                  <ul class="space-y-0.5">
                    <li v-for="(i, n) of p.inputs" :key="n">
                      {{ i.name }}: <strong>{{ formatNumber(i.value) }} {{ i.unit }}</strong>
                      <span class="opacity-70">({{ describe(i) }})</span>
                    </li>
                  </ul>
                </template>
                <span v-else class="opacity-70">{{ p.reason }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Plausibility -->
      <div v-if="estimates.plausibility" class="rounded-lg border border-base-300 p-4">
        <h2 class="text-lg mb-1">Plausibility of the declared production footprint</h2>
        <p class="text-sm">
          Declared A1-A3: <strong>{{ grams(estimates.plausibility.declaredCo2eq, 'kg') }}</strong>,
          rough estimate from mass and material: <strong>{{ grams(estimates.plausibility.estimatedCo2eq, 'kg') }}</strong>
          (factor {{ formatNumber(estimates.plausibility.ratio) }}).
        </p>
        <p class="text-sm mt-1" :class="{ 'text-warning': estimates.plausibility.assessment !== 'plausible' }">
          {{ estimates.plausibility.note }}
        </p>
      </div>

      <!-- Sources -->
      <div class="rounded-lg border border-base-300 p-4">
        <h2 class="text-lg mb-2">Sources</h2>
        <ul class="text-sm space-y-2">
          <li v-for="s of estimates.sources" :key="s.key">
            <a v-if="s.url" :href="s.url" target="_blank" rel="noopener noreferrer" class="link">{{ s.title }}</a>
            <span v-else>{{ s.title }}</span>
            <span class="opacity-70">, {{ s.publisher }}<template v-if="s.edition">, {{ s.edition }}</template><template v-if="s.updated">; updated: {{ s.updated }}</template><template v-if="s.license">; license: {{ s.license }}</template></span>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>
