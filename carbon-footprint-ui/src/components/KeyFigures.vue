<script setup lang="ts">
/**
 * Key figures of an asset: CO2eq per kg and per watt (reference quantities from Technical Data) and, for assets
 * with components, own manufacturing versus purchased components and the data coverage of the components.
 */
import { computed } from 'vue'
import { grams, percent } from '@/lib/util'
import { describeSource, type ApiIndicators } from '@/lib/api/products'
import { analyzeStructure, intensity } from '@/lib/keyFigures'
import type CarbonTree from '@/lib/model/CarbonTree'
import { showEstimates, useEstimates } from '@/lib/estimates'

const props = defineProps<{
  assetId: string
  totalCo2eq: number | undefined
  indicators: ApiIndicators | null
  carbonTree?: CarbonTree
}>()

const { estimates } = useEstimates(computed(() => props.assetId))
const estimatedPhases = computed(() => estimates.value?.phases.filter((p) => p.status === 'estimated') ?? [])

const mass = computed(() => props.indicators?.mass ?? undefined)
const power = computed(() => props.indicators?.power ?? undefined)
const perKg = computed(() => intensity(props.totalCo2eq, mass.value))
const perWatt = computed(() => intensity(props.totalCo2eq, power.value))

const structure = computed(() => (props.carbonTree?.connectionsArray.length ? analyzeStructure(props.carbonTree) : undefined))
const ownShare = computed(() => {
  const s = structure.value
  const total = s ? s.ownProductCo2eq + s.componentsProductCo2eq : 0
  return s && total > 0 ? s.ownProductCo2eq / total : undefined
})

// Why a reference quantity is missing: no Technical Data submodel at all, or the property is not stated in it
function missingNote(quantity: string) {
  if (props.indicators === null) {
    return 'not offered by this API'
  }
  return props.indicators.technicalDataFound === false
    ? 'the shell has no Technical Data submodel'
    : `no ${quantity} stated in Technical Data`
}

function formatMass(kg: number) {
  return kg < 1 ? `${Math.round(kg * 1000 * 10) / 10} g` : `${Math.round(kg * 100) / 100} kg`
}
</script>

<template>
  <div class="grid grid-cols-[repeat(auto-fit,minmax(14rem,1fr))] gap-4">
    <div class="key-figure" :title="mass ? describeSource(mass) : missingNote('mass')">
      <div class="key-figure-label">CO2eq per kg of product</div>
      <template v-if="perKg !== undefined">
        <div class="key-figure-value">{{ grams(perKg, 'kg') }}</div>
        <div class="key-figure-note">mass {{ formatMass(mass!.value) }} from Technical Data</div>
      </template>
      <template v-else>
        <div class="key-figure-value opacity-50">not available</div>
        <div class="key-figure-note">{{ mass ? 'no carbon footprint data' : missingNote('mass') }}</div>
      </template>
    </div>

    <div class="key-figure" :title="power ? describeSource(power) : missingNote('power consumption')">
      <div class="key-figure-label">CO2eq per watt of power</div>
      <template v-if="perWatt !== undefined">
        <div class="key-figure-value">{{ grams(perWatt, 'kg') }}</div>
        <div class="key-figure-note">power {{ Math.round(power!.value * 100) / 100 }} W from Technical Data</div>
      </template>
      <template v-else>
        <div class="key-figure-value opacity-50">not available</div>
        <div class="key-figure-note">{{ power ? 'no carbon footprint data' : missingNote('power consumption') }}</div>
      </template>
    </div>

    <router-link
      v-if="showEstimates && estimatedPhases.length"
      :to="{ name: 'visualization.single.estimates', params: { asset: $route.params.asset } }"
      class="key-figure hover:bg-base-200/60"
      title="Phases without declared data, estimated from the data of the asset and published emission factors"
    >
      <div class="key-figure-label flex items-center gap-2">
        <span class="inline-block w-4 h-3 estimate-fill"></span>Estimated, not declared
      </div>
      <div class="key-figure-value">{{ grams(estimates!.estimatedCo2eq, 'kg') }}</div>
      <div class="key-figure-note">{{ estimatedPhases.map((p) => p.phase).join(', ') }}, see Estimates</div>
    </router-link>

    <template v-if="structure">
      <div
        class="key-figure"
        title="Product emissions of the asset itself (its declared footprint minus the footprints of its components) compared with those of its components"
      >
        <div class="key-figure-label">Own manufacturing</div>
        <template v-if="ownShare !== undefined">
          <div class="key-figure-value">{{ percent(ownShare) }}</div>
          <div class="flex h-2 mt-2 rounded-sm overflow-hidden bg-base-300">
            <div class="bg-primary" :style="{ width: `${ownShare * 100}%` }"></div>
          </div>
          <div class="key-figure-note">
            {{ grams(structure.ownProductCo2eq, 'kg') }} own, {{ grams(structure.componentsProductCo2eq, 'kg') }} components
          </div>
        </template>
        <template v-else>
          <div class="key-figure-value opacity-50">not available</div>
          <div class="key-figure-note">no product emissions known</div>
        </template>
      </div>

      <div
        class="key-figure"
        title="Share of the components at the lowest level of the product structure (counted with their units) that provide an own carbon footprint. Components without one are missing in the totals."
      >
        <div class="key-figure-label">Data coverage of components</div>
        <div class="key-figure-value">{{ structure.coverage !== undefined ? percent(structure.coverage) : 'none' }}</div>
        <div class="key-figure-note">
          {{ structure.leafComponentsWithFootprint }} of {{ structure.leafComponents }} components with own footprint,
          {{ structure.depth }} {{ structure.depth === 1 ? 'level' : 'levels' }}
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
@reference "@/assets/main.css";

.key-figure {
  @apply rounded-lg border border-base-300 px-4 py-3;
}
.key-figure-label {
  @apply text-sm opacity-70;
}
.key-figure-value {
  @apply text-2xl mt-1;
}
.key-figure-note {
  @apply text-xs opacity-70 mt-1;
}
</style>
